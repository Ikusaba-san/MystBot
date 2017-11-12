import discord
import twitchio
from twitchio import commands as tcommands
from discord.ext import commands

import asyncio
import random


class TwitchIOCog(tcommands.TwitchBot):
    def __init__(self, dbot):
        super().__init__(prefix=['?', '!?'],
                         nick='mysterialbot',
                         integrated=True,
                         initial_channels=['ladymisai', 'evieerushu'],
                         token='oauth:hi776xr4psxvcv6uva3kosqi4hc8h7',
                         client_id='d9ueaxgpwi5ktn3wheykya3tier0ms')
        self.dbot = dbot
        self.run()

        self._points = {}
        self.dbot.loop.create_task(self.twitch_chatters())
        self.dbot.loop.create_task(self.twitch_chatters_up())
        self.dbot.loop.create_task(self.init_points())

    async def twitch_chatters(self):
        await self.dbot.wait_until_ready()
        loops = 0

        while True:
            await asyncio.sleep(58)
            if loops == 10:
                loops = 0
            loops += 1

            if not self.channel_cache:
                await asyncio.sleep(5)
                continue

            for chan in self.channel_cache:
                try:
                    viewers = await self.get_chatters(chan)
                except:
                    continue

                chatters = viewers['chatters']
                if chatters['viewers'] and chan in chatters['moderators']:
                    for mem in chatters['viewers']:
                        if chan not in self._points:
                            self._points[chan] = {}
                        if mem not in self._points[chan]:
                            self._points[chan][mem] = 1
                        else:
                            self._points[chan][mem] += 1

                    for mod in chatters['moderators']:
                        if chan not in self._points:
                            self._points[chan] = {}
                        if mod not in self._points[chan]:
                            self._points[chan][mod] = 1
                        else:
                            self._points[chan][mod] += 1

    async def twitch_chatters_up(self):
        await self.dbot.wait_until_ready()

        while True:
            await asyncio.sleep(300)
            if not self._points:
                continue
            for k, v in self._points.items():
                for x, y in v.items():
                    await self.dbot.dbc['tbot'][k].update_one({'_id': x}, {'$set': {'points': y}}, upsert=True)

    async def init_points(self):
        await self.dbot.wait_until_ready()

        names = await self.dbot.dbc['tbot'].collection_names()

        for chan in names:
            self._points[chan] = {}
            async for mem in self.dbot.dbc['tbot'][chan].find({}):
                self._points[chan][mem['_id']] = mem['points']

    async def event_raw_data(self, data):
        pass

    async def event_message(self, message):
        pass

    @tcommands.twitch_command(aliases=['tofus'])
    async def points(self, ctx):

        try:
            points = self._points[ctx.channel.name][ctx.author.name]
        except KeyError:
            return await ctx.send(f'{ctx.author.name} currently has NO points! Kappa')
        else:
            await ctx.send(f'{ctx.author.name} has {points} points! DxCat')

    @tcommands.twitch_command(aliases=['gamble'])
    async def roullete(self, ctx, amount: int=None):

        amount = int(amount)

        try:
            points = self._points[ctx.channel.name][ctx.author.name]
        except KeyError:
            return await ctx.send(f'{ctx.author.name} currently has NO points to gamble! Kappa')

        if amount > points:
            return await ctx.send('You do not have that many points Keepo ...Nub')
        elif amount == points:
            msg = f'{ctx.author.name} went all in and'
        else:
            msg = f'{ctx.author.name} gambled {amount} and'

        num = random.randint(1, 100)
        if 1 <= num <= 60:
            self._points[ctx.channel.name][ctx.author.name] -= amount
            await ctx.send(f'{msg} lost {amount} tofus! BrokeBack')
        elif 61 <= num <= 99:
            self._points[ctx.channel.name][ctx.author.name] += amount
            await ctx.send(f'{msg} WON {amount} tofus!... BlessRNG')
        else:
            self._points[ctx.channel.name][ctx.author.name] += amount * 3
            await ctx.send(f'{msg} and hit the JACKPOT! KappaClause KappaClaus')

    @tcommands.twitch_command()
    async def tpoints(self, ctx):
        if ctx.author.name != 'evieerushu':
            return

        await ctx.send(f'{self._points}'[::500])

    @tcommands.twitch_command()
    async def hello(self, ctx):
        await ctx.send(f'Hai, {ctx.author.name} I am MysterialBot. I am a Twitch/Discord integrated bot made by'
                       f' EvieeRushu/MysterialPy.')


def setup(bot):
    bot.add_cog(TwitchIOCog(bot))
