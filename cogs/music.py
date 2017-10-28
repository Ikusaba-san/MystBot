"""Copyright (c) 2017 MysterialPy. mysterialpy@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

import discord
from discord.ext import commands

import asyncio
import async_timeout
import datetime
import humanize
import math
import random
import logging
from .utils.downloader import Downloader


from cogs.utils.paginators import SimplePaginator

log = logging.getLogger('myst')


class Player:

    def __init__(self, ctx):
        self.ctx = ctx
        self._task_playerloop = ctx.bot.loop.create_task(self.player_loop())

        self.song_queue = asyncio.Queue()

        self._next = asyncio.Event()

        self.held_entry = []
        self.channel = None
        self._volume = 0.5
        self.playing = None
        self.playing_info = None
        self.requester = None
        self.paused = None
        self.downloading = None
        self.shuffling = None
        self.controls = {'▶': 'resume',
                         '⏸': 'pause',
                         '⏹': 'stop',
                         '⏭': 'skip',
                         '🔀': 'shuffle',
                         '🔂': 'repeat',
                         '➕': 'vol_up',
                         '➖': 'vol_down',
                         'ℹ': 'queue'}
        self.controller = None
        self.skips = set()
        self.pauses = set()
        self.resumes = set()
        self.shuffles = set()

        self.threadex = None

    @property
    def volume(self):
        return self._volume

    async def player_loop(self):
        await self.ctx.bot.wait_until_ready()

        while not self.ctx.bot.is_closed():
            self._next.clear()

            try:
                with async_timeout.timeout(300):
                    entry = await self.song_queue.get()
                    del self.held_entry[:]
                    self.held_entry.append(entry)
            except asyncio.TimeoutError:
                if self.downloading:
                    continue
                await self.channel.send('I have been inactive for **5** minutes. Goodbye.', delete_after=30)
                return await self.ctx.bot.music_cleanup(self.ctx, self)

            self.playing_info = entry['info']
            self.requester = entry['info']['requester']
            self.channel = entry['channel']
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(entry['source']), volume=self._volume)

            self.ctx.guild.voice_client.play(source,
                                             after=lambda s: self.ctx.bot.loop.call_soon_threadsafe(self._next.set()))

            await self.now_playing(entry['info'], entry['channel'])
            await self._next.wait()
            source.cleanup()

            self.playing_info = None
            self.requester = None
            self.skips.clear()
            self.pauses.clear()
            self.resumes.clear()
            self.shuffles.clear()

    async def now_playing(self, info, channel):

        try:
            info['title']
        except:
            return

        embed = discord.Embed(title='Now Playing:', description=info['title'], colour=0xDB7093)
        embed.set_thumbnail(url=info['thumb'] if info['thumb'] is not None else 'http://i.imgur.com/EILyJR6.png')
        embed.add_field(name='Requested by', value=info['requester'].mention)
        embed.add_field(name='Video URL', value=f"[Click Here!]({info['weburl']})")
        embed.add_field(name='Duration', value=str(datetime.timedelta(seconds=int(info['duration']))))
        embed.add_field(name='Queue Length', value=f'{self.song_queue.qsize()}')
        if self.song_queue.qsize() > 0:
            upnext = self.song_queue._queue[0]['info']
            embed.add_field(name='Up Next', value=upnext['title'], inline=False)
        embed.set_footer(text=f'🎶 | Views: {humanize.intcomma(info["views"])} |'
                              f' {info["upload_date"] if not None else ""}')

        async for message in channel.history(limit=1):
            if self.playing is None or message.id != self.playing.id and message.author.id != self.ctx.bot.user.id:

                try:
                    await self.playing.delete()
                except:
                    pass
                finally:
                    self.playing = None

                self.playing = await self.channel.send(content=None, embed=embed)

                for r in self.controls:
                    try:
                        await self.playing.add_reaction(r)
                    except:
                        return

                if self.controller is not None:
                    garbage = self.controller
                    try:
                        garbage.cancel()
                    except Exception as e:
                        await channel.send(
                            f'**Error in Player Garbage Collection:: Please terminate and restart the player.**'
                            f'```css\n[{type(e)}] - [{e}]\n```')
                        return await self.ctx.bot.music_cleanup(self.ctx, self)

                self.controller = self.ctx.bot.loop.create_task(self.react_controller())
            else:
                try:
                    await self.playing.edit(content=None, embed=embed)
                except:
                    pass

    async def react_controller(self):
        vc = self.ctx.guild.voice_client

        def check(r, u):

            if not self.playing:
                return False

            if str(r) not in self.controls.keys():
                return False

            if u.id == self.ctx.bot.user.id or r.message.id != self.playing.id:
                return False

            if u not in vc.channel.members:
                return False

            return True

        while self.playing:

            if vc is None:
                self.controller.cancel()
                return

            react, user = await self.ctx.bot.wait_for('reaction_add', check=check)
            control = self.controls.get(str(react))

            try:
                await self.playing.remove_reaction(react, user)
            except:
                pass

            try:
                cmd = self.ctx.bot.get_command(control)
                ctx = await self.ctx.bot.get_context(react.message)
                ctx.author = user
            except Exception as e:
                log.warning(f'PLAYER:: React Controller: {e} - [{self.ctx.guild.id}]')
            else:
                try:
                    if cmd.is_on_cooldown(ctx):
                        continue
                    if not await self.invoke_react(cmd, ctx):
                        continue
                    else:
                        self.ctx.bot.loop.create_task(ctx.invoke(cmd))
                except Exception as e:
                    ctx.command = self.ctx.bot.get_command('reactcontrol')
                    await cmd.dispatch_error(ctx=ctx, error=e)
                    continue

    async def invoke_react(self, cmd, ctx):

        if not cmd._buckets.valid:
            return True

        if not (await cmd.can_run(ctx)):
            return False

        bucket = cmd._buckets.get_bucket(ctx)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return False
        return True


class Music:
    """Music related commands for Mysterial.

    For music to work properly, the bot must be able to Embed.
    It is advisable to allow the bot remove reactions and manage messages."""

    def __init__(self, bot):
        self.bot = bot

    def get_player(self, ctx):

        player = self.bot._players.get(ctx.guild.id, None)

        if player is None:
            player = Player(ctx)
            self.bot._players[ctx.guild.id] = player
        return player

    @commands.command(name='reactcontrol', hidden=True)
    @commands.guild_only()
    async def falsy_controller(self, ctx):
        pass

    @commands.command(name='nowplaying', aliases=['playing', 'current', 'currentsong', 'np'])
    @commands.cooldown(2, 30, commands.BucketType.guild)
    @commands.guild_only()
    async def now_playing(self, ctx):
        """Display the current song, and the reaction controller."""

        player = self.get_player(ctx)
        await player.now_playing(player.playing_info, ctx.channel)

    @commands.command(name='play', aliases=['sing'])
    @commands.guild_only()
    async def search_song(self, ctx, *, search: str):
        """Play a song. If no link is provided, Myst will search YouTube for the song."""

        vc = ctx.guild.voice_client

        if vc is not None:
            if ctx.author not in vc.channel.members:
                return await ctx.send(f'You must be in **{vc.channel}** to request songs.')

        if vc is None:
            await ctx.invoke(self.voice_connect)
            vc = ctx.guild.voice_client

        player = self.get_player(ctx)

        try:
            await ctx.message.delete()
        except:
            pass

        self.bot._counter_songs += 1

        dl = Downloader()
        await dl.run(ctx=ctx, bot=self.bot, search=search, queue=player.song_queue)

    @commands.command(name='join', aliases=['summon', 'move', 'connect'])
    @commands.cooldown(2, 60, commands.BucketType.user)
    @commands.has_permissions(move_members=True)
    @commands.guild_only()
    async def voice_connect(self, ctx, *, channel: discord.VoiceChannel = None):
        """Summon Myst to a channel. If she is another channel she will be moved."""

        vc = ctx.guild.voice_client

        if vc is not None:
            if channel is None:
                try:
                    await vc.move_to(ctx.author.voice.channel)
                    return await ctx.send(f'Moved to: **{ctx.author.voice.channel}**', delete_after=10)
                except Exception as e:
                    msg = await ctx.send(f'There was an error switching channels.\n'
                                         f'{type(e)}: {e}')
                    return
            else:
                try:
                    await vc.move_to(channel)
                    return await ctx.send(f'Moved to: **{channel}**', delete_after=10)
                except Exception as e:
                    msg = await ctx.send(f'There was an error switching channels.\n'
                                         f'{type(e)}: {e}')
                    return

        if channel is None and ctx.author.voice is None:
            msg = await ctx.send('You did not specify a Voice Channel, and you are not connected to one.',
                                 delete_after=30)
            return

        if channel is None:
            try:
                vc = await ctx.author.voice.channel.connect(timeout=30, reconnect=True)
                return await ctx.send(f'Connected to: **{vc.channel}**', delete_after=30)
            except asyncio.TimeoutError:
                msg = await ctx.send('There was an error connecting to voice. Please try again later.')
                return

        else:
            try:
                vc = await channel.connect(timeout=30, reconnect=True)
                return await ctx.send(f'Connected to: **{vc.channel}**')
            except asyncio.TimeoutError:
                msg = await ctx.send(f'There was an error connecting to: {channel}\n'
                                     f'Please try again later')
                return

    @commands.command(name='resume')
    @commands.guild_only()
    async def resume_song(self, ctx):
        """Resume the paused song."""

        player = self.get_player(ctx)
        vc = ctx.guild.voice_client
        requester = player.requester

        if ctx.message.id != player.playing.id:
            try:
                await ctx.message.delete()
            except:
                pass

        if not vc.is_paused():
            return

        elif vc is None:
            return await ctx.send('**I am not currently playing anything.**', delete_after=15)

        elif requester.id == ctx.author.id and len(vc.channel.members) <= 4:
            vc.resume()
            try:
                return await player.paused.edit(content=f'**{requester.mention} has resumed the song.**',
                                                delete_after=15)
            except:
                return

        elif ctx.author.guild_permissions.manage_guild:
            vc.resume()
            try:
                return await player.paused.edit(content=f'**{ctx.author.mention} has resumed the song as an admin.**',
                                                delete_after=15)
            except:
                return

        elif len(vc.channel.members) <= 3:
            vc.resume()
            try:
                return await player.paused.edit(content=f'**{ctx.author.mention} has resumed the song.**',
                                                delete_after=15)
            except:
                return

        elif ctx.author.id in player.resumes:
            return await ctx.send(f'**{ctx.author.mention} you have already voted to resume. 1 more votes needed.**',
                                  delete_after=15)

        player.resumes.add(ctx.author.id)

        if len(player.resumes) > 1:
            vc.resume()
            await ctx.send('**Vote to resume the song passed. Resuming...**', delete_after=15)
            player.resumes.clear()
            try:
                await player.paused.delete()
            except:
                pass
            finally:
                return

        await ctx.send(f'**{ctx.author.mention} has started a resume request. 1 more votes need to pass.**',
                       delete_after=20)

    @commands.command(name='pause')
    @commands.cooldown(2, 90, commands.BucketType.user)
    @commands.guild_only()
    async def pause_song(self, ctx):
        """Pause the current song."""

        player = self.get_player(ctx)
        vc = ctx.guild.voice_client
        requester = player.requester

        if ctx.message.id != player.playing.id:

            try:
                await ctx.message.delete()
            except:
                pass

        if vc.is_paused():
            return

        elif vc is None or not vc.is_playing():
            return await ctx.send('**I am not currently playing anything.**', delete_after=10)

        elif requester.id == ctx.author.id and len(vc.channel.members) <= 4:
            vc.pause()
            player.paused = await ctx.send(f'**{requester.mention} has paused the song.**')
            return

        elif ctx.author.guild_permissions.manage_guild:
            vc.pause()
            player.paused = await ctx.send(f'**{ctx.author.mention} has paused the song as an admin.**')
            return

        elif len(vc.channel.members) <= 3:
            vc.pause()
            player.paused = await ctx.send(f'**{ctx.author.mention} has paused the song.**')
            return

        elif ctx.author.id in player.pauses:
            return await ctx.send(f'**{ctx.author.mention} you have already voted to pause. 1 more votes needed.**',
                                  delete_after=15)

        player.pauses.add(ctx.author.id)

        if len(player.pauses) > 1:
            vc.pause()
            player.paused = await ctx.send('**Pause vote passed: Pausing the song.**')
            player.pauses.clear()
            return

        await ctx.send(f'**{ctx.author.mention} has started a pause request. 1 more votes need to pass.**',
                       delete_after=15)

    @commands.command(name='stop')
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def stop_player(self, ctx):
        """Terminate the player and clear the Queue."""

        vc = ctx.guild.voice_client
        player = self.get_player(ctx)

        if vc is None:
            return await ctx.send('**I am not currently playing anything.**', delete_after=10)

        try:
            await player.playing.delete()
        except:
            pass

        while not player.song_queue.empty():
            await player.song_queue.get()

        vc.stop()
        await asyncio.sleep(1)

        self.bot.loop.create_task(self.bot.music_cleanup(ctx, player))
        await ctx.send(f'Player has been terminated by {ctx.author.mention}. **Goodbye.**', delete_after=30)

    @stop_player.error
    async def stop_error(self, ctx, error):

        if isinstance(error, commands.CheckFailure):
            await ctx.send('You need **`[Manage Server]`** permissions to stop the player.', delete_after=20)

    @commands.command(name='shuffle', aliases=['mix'])
    @commands.cooldown(1, 180, commands.BucketType.user)
    @commands.guild_only()
    async def shuffle_songs(self, ctx):
        """Shuffle all songs in your Queue."""

        vc = ctx.guild.voice_client
        player = self.get_player(ctx)

        if vc is None:
            return await ctx.send('**I am not currently playing anything.**', delete_after=20)

        elif player.downloading:
            return await ctx.send('**Please wait for your songs to finish downloading**', delete_after=15)

        elif player.song_queue.qsize() <= 2:
            return await ctx.send('**Please add more songs to the Queue before shuffling.**', delete_after=15)

        elif ctx.author.guild_permissions.manage_guild:
            await self.do_shuffle(ctx, player)
            return await ctx.send(f'**{ctx.author.mention} has shuffled the playlist as an admin.**', delete_after=20)

        elif len(vc.channel.members) <= 3:
            await self.do_shuffle(ctx, player)
            return await ctx.send(f'**{ctx.author.mention} has shuffled the playlist.**', delete_after=20)

        elif ctx.author.id in player.shuffles:
            return await ctx.send(f'**{ctx.author.mention} you have already voted to shuffle. 1 more votes needed.**',
                                  delete_after=15)

        player.shuffles.add(ctx.author.id)

        if len(player.shuffles) > 1:
            await ctx.send('**Shuffle vote passed: Shuffling the playlist.**', delete_after=20)
            await self.do_shuffle(ctx, player)
            player.shuffles.clear()
            return

        await ctx.send(f'**{ctx.author.mention} has started a shuffle request. 1 more votes need to pass.**',
                       delete_after=20)

    async def do_shuffle(self, ctx, player):

        shuf = []

        while not player.song_queue.empty():
            shuf.append(await player.song_queue.get())

        random.shuffle(shuf)

        for x in shuf:
            await player.song_queue.put(x)
        await ctx.invoke(self.now_playing)

    @commands.command(name='vol_up', hidden=True)
    @commands.cooldown(9, 60, commands.BucketType.user)
    @commands.guild_only()
    async def vol_up(self, ctx):
        """Turn the Volume Up!"""

        player = self.get_player(ctx)
        vc = ctx.guild.voice_client

        orig = int(player._volume * 100)
        vol_in = int(math.ceil((orig + 10) / 10.0)) * 10
        vol = float(vol_in) / 100

        if vol > 1.0:
            return await ctx.send('**Max volume reached.**', delete_after=5)

        try:
            vc.source.volume = vol
            player._volume = vol
        except AttributeError:
            await ctx.send('**I am not currently playing anything.**')

    @commands.command(name='vol_down', hidden=True)
    @commands.cooldown(9, 60, commands.BucketType.user)
    @commands.guild_only()
    async def vol_down(self, ctx):
        """Turn the Volume down."""

        player = self.get_player(ctx)
        vc = ctx.guild.voice_client

        orig = int(player._volume * 100)
        vol_in = int(math.ceil((orig - 10) / 10.0)) * 10
        vol = float(vol_in) / 100

        if vol < 0.1:
            return await ctx.send('**Minimum volume reached.**', delete_after=5)

        try:
            vc.source.volume = vol
            player._volume = vol
        except AttributeError:
            await ctx.send('**I am not currently playing anything.**')

    @commands.command(name='skip')
    @commands.cooldown(2, 60, commands.BucketType.user)
    @commands.guild_only()
    async def skip_song(self, ctx):
        """Skips the current song."""

        player = self.get_player(ctx)
        vc = ctx.guild.voice_client
        requester = player.requester

        if not player.playing:
            return

        if ctx.message.id != player.playing.id:

            try:
                await ctx.message.delete()
            except:
                pass

        if vc is None:
            return await ctx.send('**I am not currently playing anything.**', delete_after=10)

        elif requester.id == ctx.author.id and len(vc.channel.members) <= 4:
            vc.stop()
            return await ctx.send(f'**{requester.mention} has skipped the song.**', delete_after=10)

        elif ctx.author.guild_permissions.manage_guild:
            vc.stop()
            return await ctx.send(f'**{ctx.author.mention} has skipped the song as an admin.**', delete_after=10)

        elif len(vc.channel.members) <= 3:
            vc.stop()
            return await ctx.send(f'**{ctx.author.mention} has skipped the song.**', delete_after=10)

        req_skips = 1 if len(vc.channel.members) == 1 \
            else 2 if 2 <= len(vc.channel.members) <= 4 \
            else int(round(vc.channel.members / 5)) + 3

        need = req_skips - len(player.skips)

        if ctx.author.id in player.pauses:
            return await ctx.send(f'**{ctx.author.mention} you have already voted to skip. {need} more votes needed.**',
                                  delete_after=15)

        player.skips.add(ctx.author.id)

        if len(player.skips) >= req_skips:
            vc.stop()
            return await ctx.send('**Skip vote passed: Skipping the song.**', delete_after=10)

        await ctx.send(f'**{ctx.author.mention} has started a skip request. {need} more votes needed to pass.**',
                       delete_after=15)

    @commands.command(name='repeat', hidden=True)
    @commands.cooldown(3, 60, commands.BucketType.guild)
    @commands.guild_only()
    async def repeat_song(self, ctx):
        """Repeat the current song 1 time."""

        vc = ctx.guild.voice_client
        player = self.get_player(ctx)

        if not player.held_entry:
            return await ctx.send('**This song is already queued to repeat.**', delete_after=10)

        elif vc is None:
            return await ctx.send('**I am not currently playing anything.**', delete_after=10)

        await ctx.send(f'**{ctx.author.mention}: The current song will replay.**', delete_after=15)
        await self.do_repeat(ctx, player)

    async def do_repeat(self, ctx, player):

        player.shuffling = True

        while not player.song_queue.empty():
            player.held_entry.append(await player.song_queue.get())

        for x in player.held_entry:
            await player.song_queue.put(x)

        player.shuffling = False
        del player.held_entry[:]

        await ctx.invoke(self.now_playing)

    @commands.command(name='queue', aliases=['q', 'que', 'playlist'])
    @commands.cooldown(2, 90, commands.BucketType.user)
    @commands.guild_only()
    async def queue_info(self, ctx):
        """Display the Queue of songs."""

        player = self.get_player(ctx)
        vc = ctx.guild.voice_client

        if vc is None:
            return await ctx.send('**I am not currently playing anything.**', delete_after=10)

        elif player.song_queue.qsize() <= 0:
            return await ctx.send(f'```css\n[No other songs in the Queue.]\n```', delete_after=10)

        entries = [x["info"]["title"] for x in player.song_queue._queue]
        page = SimplePaginator(title='Playlist',
                               ctx=ctx,
                               bot=self.bot,
                               colour=0xDB7093,
                               entries=entries,
                               prepend=' - `',
                               append='`',
                               inner='**+**')
        await page.embed_creator()


def setup(bot):
    bot.add_cog(Music(bot))
