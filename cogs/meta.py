import discord
from discord.ext import commands

import datetime
import asyncio
import psutil
import os
import numpy as np


class Stats:
    """Stats :)"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.stats_updater())

    async def stats_updater(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.bot.dbc['owner']['stats'].update_one({'_id': 'command_counter'},
                                                            {'%set': {'count': self.bot._counter_commands}})
            await self.bot.dbc['owner']['stats'].update_one({'_id': 'message_counter'},
                                                            {'%set': {'count': self.bot._counter_messages}})
            await self.bot.dbc['owner']['stats'].update_one({'_id': 'songs_counter'},
                                                            {'%set': {'count': self.bot._counter_songs}})

            await asyncio.sleep(60)

    async def on_command_completion(self, ctx):
        self.bot._counter_commands += 1

    async def on_message(self, message):
        self.bot._counter_messages += 1

    def get_bot_uptime(self, *, brief=False):
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            if days:
                fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
            else:
                fmt = '{h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h}h {m}m {s}s'
            if days:
                fmt = '{d}d ' + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    @commands.command(name='about', aliases=['stats'])
    async def self_about(self, ctx):
        """Botto Stats"""
        uptime = self.get_bot_uptime(brief=True)

        cmd = r'git show -s HEAD~3..HEAD --format="[{}](https://github.com/MysterialPy/MystBot/commit/%H) %s (%cr)"'
        if os.name == 'posix':
            cmd = cmd.format(r'\`%h\`')
        else:
            cmd = cmd.format(r'`%h`')
        revision = os.popen(cmd).read().strip()

        total_members = sum(1 for _ in self.bot.get_all_members())
        total_online = len({m.id for m in self.bot.get_all_members() if m.status is discord.Status.online})

        avg_ping = np.average(list(self.bot._pings))

        voice_channels = []
        text_channels = []
        for guild in self.bot.guilds:
            voice_channels.extend(guild.voice_channels)
            text_channels.extend(guild.text_channels)

        text = len(text_channels)
        voice = len(voice_channels)

        cpu_usage = self.bot.process.cpu_percent() / psutil.cpu_count()

        embed = discord.Embed(title='MysterialBot', description='Latest Updates:\n' + revision, colour=0x886aff)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_footer(icon_url=
                         'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Python.svg/200px-Python.svg.png',
                         text='Made in Python with discord.py@rewrite')
        embed.add_field(name='Useful Links',
                        value='[Official Server](http://discord.gg/Hw7RTtr)\n'
                              '[GitHub](https://github.com/MysterialPy/MystBot)\n'
                              '[Mysterial Web](http://www.mysterialbot.com)', inline=False)

        embed.add_field(name='Creator', value=self.bot.appinfo.owner.mention)
        embed.add_field(name='Uptime', value=uptime)

        embed.add_field(name='Servers', value=str(len(self.bot.guilds)))
        embed.add_field(name='Channels', value=f'{text + voice}')
        embed.add_field(name='Members', value=f'Total: {total_members}\nOnline: {total_online}')

        embed.add_field(name='Commands Run', value=f'{self.bot._counter_commands}')
        embed.add_field(name='Messages Read', value=f'{self.bot._counter_messages}')
        embed.add_field(name='Songs Played', value=f'{self.bot._counter_songs}')

        embed.add_field(name='Status', value=f'**Memory Usage**: {self.bot._ram[-1]:.2f} MiB\n'
                                             f'**CPU Usage      **: {cpu_usage:.2f} %\n'
                                             f'**Latest Ping**      : {self.bot.latency * 1000:.2f}ms\n'
                                             f'**Avg Ping          **: {avg_ping:.2f}ms', inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Stats(bot))
