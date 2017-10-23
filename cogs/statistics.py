import discord
from discord.ext import commands

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

import numpy as np
import itertools
import datetime

from concurrent.futures import ThreadPoolExecutor
import functools


class Plots:
    """Commands which make graphs and other pretties."""

    def __init__(self, bot):
        self.bot = bot
        self.threadex = ThreadPoolExecutor(max_workers=2)

    def pager(self, entries, chunk: int):
        for x in range(0, len(entries), chunk):
            yield entries[x:x + chunk]

    def hilo(self, numbers, indexm: int=1):
        highest = [index * indexm for index, val in enumerate(numbers) if val == max(numbers)]
        lowest = [index * indexm for index, val in enumerate(numbers) if val == min(numbers)]

        return highest, lowest

    def datetime_range(self, start, end, delta):
        current = start
        while current < end:
            yield current
            current += delta

    def get_times(self):
        # todo this is really bad so fix soon pls thanks kk weeeew

        fmt = '%H%M'
        current = datetime.datetime.utcnow()
        times = []
        times2 = []
        times3 = []
        tcount = 0

        rcurrent = current - datetime.timedelta(minutes=60)
        rcurrent2 = current - datetime.timedelta(minutes=30)
        for x in range(7):
            times.append(rcurrent + datetime.timedelta(minutes=tcount))
            tcount += 10

        tcount = 0
        for x in range(7):
            times2.append(rcurrent2 + datetime.timedelta(minutes=tcount))
            tcount += 5

        tcount = 0
        for t3 in range(26):
            times3.append(rcurrent + datetime.timedelta(minutes=tcount))
            tcount += 60/25

        times = [t.strftime(fmt) for t in times]
        times2 = [t.strftime(fmt) for t in times2]
        times3 = [t.strftime(fmt) for t in times3]

        return times, times2, times3, current

    def ping_plotter(self, data: (tuple, list)=None):

        # Base Data
        if data is None:
            numbers = list(self.bot._pings)
        else:
            numbers = data

        long_num = list(itertools.chain.from_iterable(itertools.repeat(num, 2) for num in numbers))
        chunks = tuple(self.pager(numbers, 4))

        avg = list(itertools.chain.from_iterable(itertools.repeat(np.average(x), 8) for x in chunks))
        mean = [np.mean(numbers)] * 60
        prange = int(max(numbers)) - int(min(numbers))
        plog = np.log(numbers)

        t = np.sin(np.array(numbers) * np.pi*2 / 180.)
        xnp = np.linspace(-np.pi, np.pi, 60)
        # tmean = [np.mean(t)] * 60

        # Spacing/Figure/Subs
        plt.style.use('ggplot')
        fig = plt.figure(figsize=(15, 7.5))
        ax = fig.add_subplot(2, 2, 2, axisbg='aliceblue', alpha=0.3)   # Right
        ax2 = fig.add_subplot(2, 2, 1, axisbg='thistle', alpha=0.2)  # Left
        ax3 = fig.add_subplot(2, 1, 2, axisbg='aliceblue', alpha=0.3)  # Bottom
        ml = MultipleLocator(5)
        ml2 = MultipleLocator(1)

        # Times
        times, times2, times3, current = self.get_times()

        # Axis's/Labels
        plt.title(f'Latency over Time (WebSocket) | {current} UTC')
        ax.set_xlabel(' ')
        ax.set_ylabel('Network Stability')
        ax2.set_xlabel(' ')
        ax2.set_ylabel('Milliseconds(ms)')
        ax3.set_xlabel('Time(HHMM)')
        ax3.set_ylabel('Latency(ms)')

        if min(numbers) > 100:
            ax3.set_yticks(np.arange(min(int(min(numbers)), 2000) - 100,
                                     max(range(0, int(max(numbers)) + 100)) + 50, max(numbers) / 12))
        else:
            ax3.set_yticks(np.arange(min(0, 1), max(range(0, int(max(numbers)) + 100)) + 50, max(numbers) / 12))

        # Labels
        ax.yaxis.set_minor_locator(ml2)
        ax2.xaxis.set_minor_locator(ml2)
        ax3.yaxis.set_minor_locator(ml)
        ax3.xaxis.set_major_locator(ml)

        ax.set_ylim([-1, 1])
        ax.set_xlim([0, np.pi])
        ax.yaxis.set_ticks_position('right')
        ax.set_xticklabels(times2)
        ax.set_xticks(np.linspace(0, np.pi, 7))
        ax2.set_ylim([min(numbers) - prange/4, max(numbers) + prange/4])
        ax2.set_xlim([0, 60])
        ax2.set_xticklabels(times)
        ax3.set_xlim([0, 120])
        ax3.set_xticklabels(times3, rotation=45)
        plt.minorticks_on()
        ax3.tick_params()

        highest, lowest = self.hilo(numbers, 2)

        mup = []
        mdw = []
        count = 0
        p10 = mean[0] * (1 + 0.5)
        m10 = mean[0] * (1 - 0.5)

        for x in numbers:
            if x > p10:
                mup.append(count)
            elif x < m10:
                mdw.append(count)
            count += 1

        # Axis 2 - Left
        ax2.plot(range(0, 60), list(itertools.repeat(p10, 60)), '--', c='indianred',
                 linewidth=1.0,
                 markevery=highest,
                 label='+10%')
        ax2.plot(range(0, 60), list(itertools.repeat(m10, 60)), '--', c='indianred',
                 linewidth=1.0,
                 markevery=highest,
                 label='+-10%')
        ax2.plot(range(0, 60), numbers, '-', c='blue',
                 linewidth=1.0,
                 label='Mark Up',
                 alpha=.8,
                 drawstyle='steps-post')
        ax2.plot(range(0, 60), numbers, ' ', c='red',
                 linewidth=1.0,
                 markevery=mup,
                 label='Mark Up',
                 marker='^')
        """ax2.plot(range(0, 60), numbers, ' ', c='green',
                 linewidth=1.0, markevery=mdw,
                 label='Mark Down',
                 marker='v')"""
        ax2.plot(range(0, 60), mean, label='Mean', c='blue',
                linestyle='--',
                linewidth=.75)
        ax2.plot(list(range(0, 60)), plog, 'darkorchid',
                 alpha=.9,
                 linewidth=1,
                 drawstyle='default',
                 label='Ping')

        # Axis 3 - Bottom
        ax3.plot(list(range(0, 120)), long_num, 'darkorchid',
                 alpha=.9,
                 linewidth=1.25,
                 drawstyle='default',
                 label='Ping')
        ax3.fill_between(list(range(0, 120)), long_num, 0, facecolors='darkorchid', alpha=0.3)
        ax3.plot(range(0, 120), long_num, ' ', c='indianred',
                 linewidth=1.0,
                 markevery=highest,
                 marker='^',
                 markersize=12)
        ax3.text(highest[0], max(long_num) - 10, f'{round(max(numbers))}ms', fontsize=12)
        ax3.plot(range(0, 120), long_num, ' ', c='lime',
                 linewidth=1.0,
                 markevery=lowest,
                 marker='v',
                 markersize=12)
        ax3.text(lowest[0], min(long_num) - 10, f'{round(min(numbers))}ms', fontsize=12)
        ax3.plot(list(range(0, 120)), long_num, 'darkorchid',
                 alpha=.5,
                 linewidth=.75,
                 drawstyle='steps-pre',
                 label='Steps')
        ax3.plot(range(0, 120), avg, c='forestgreen',
                 linewidth=1.25,
                 markevery=.5,
                 label='Average')

        # Axis - Right
        """ax.plot(list(range(0, 60)), plog1, 'darkorchid',
                 alpha=.9,
                 linewidth=1,
                 drawstyle='default',
                 label='Ping')
        ax.plot(list(range(0, 60)), plog2, 'darkorchid',
                 alpha=.9,
                 linewidth=1,
                 drawstyle='default',
                 label='Ping')
        ax.plot(list(range(0, 60)), plog10, 'darkorchid',
                 alpha=.9,
                 linewidth=1,
                 drawstyle='default',
                 label='Ping')"""

        ax.fill_between(list(range(0, 120)), .25, 1, facecolors='lime', alpha=0.2)
        ax.fill_between(list(range(0, 120)), .25, -.25, facecolors='dodgerblue', alpha=0.2)
        ax.fill_between(list(range(0, 120)), -.25, -1, facecolors='crimson', alpha=0.2)
        ax.fill_between(xnp, t, 1, facecolors='darkred')

        """ax.plot(list(range(0, 60)), t, 'darkred',
                linewidth=1.0,
                alpha=1,
                label='Stability')
        ax.plot(list(range(0, 60)), tmean, 'purple',
                linewidth=1.0,
                alpha=1,
                linestyle=' ')
        ax.plot(list(range(0, 60)), tp10, 'limegreen',
                linewidth=1.0,
                alpha=1,
                linestyle=' ')
        ax.plot(list(range(0, 60)), tm10, 'limegreen',
                linewidth=1.0,
                alpha=1,
                linestyle=' ')"""

        # Legend
        ax.legend(bbox_to_anchor=(.905, .97), bbox_transform=plt.gcf().transFigure)
        ax3.legend(loc='best', bbox_transform=plt.gcf().transFigure)

        # Grid
        ax.grid(which='minor')
        ax2.grid(which='both')
        ax3.grid(which='both')
        plt.grid(True, alpha=0.25)

        # Inverts
        ax.invert_yaxis()

        # File
        current = datetime.datetime.utcnow()
        save = current.strftime("%Y-%m-%d%H%M")

        plt.savefig(f'/home/myst/mystbot/pings/{save}', bbox_inches='tight')  # !!!VPS!!!
        self.bot._latest_ping[save] = f'/home/myst/mystbot/pings/{save}.png'  # !!!VPS!!!

        plt.clf()
        plt.close()
        return save

    def ram_plotter(self, data: (list, tuple)=None):
        current = datetime.datetime.utcnow()

        # Time Labels
        dts = [dt.strftime('%H%M') for dt in self.datetime_range(current - datetime.timedelta(minutes=30),
                                                                 current, datetime.timedelta(minutes=1))]

        test = list(self.bot._ram)
        chunks = tuple(self.pager(test, 2))

        mind = min(test)
        maxd = max(test)
        mean = [np.mean(test)] * 120
        avg = list(itertools.chain.from_iterable(itertools.repeat(np.average(x), 4) for x in chunks))
        highest, lowest = self.hilo(test, 1)

        fig = plt.figure(figsize=(15, 7.5))
        ax = fig.add_subplot(1, 1, 1, axisbg='whitesmoke', alpha=0.3)  # Main
        plt.style.use('ggplot')
        plt.title(f'Usage over Time (RAM) | {current} UTC')
        ax.set_xlabel('Time (HHMM)')
        ax.set_ylabel('Usage (MiB)')

        minylim = mind - 15 if mind - 15 > 0 else 0

        ax.set_xlim([0, 120])
        ax.set_xticks(np.linspace(0, 120, 30))
        ax.set_ylim([0, 120])
        ax.set_yticks(np.linspace(mind, maxd + 15, 12))
        ax.set_xticklabels(dts)
        ax.grid(which='both')
        plt.grid(True, alpha=0.25)

        # Plots
        ax.plot(list(range(0, 120)), test)
        ax.plot(list(range(0, 120)), test, '-', c='darkslategrey',
                linewidth=0.5,
                label='Usage')
        ax.fill_between(list(range(0, 240)), avg, facecolors='cyan', alpha=0.6)
        ax.fill_between(list(range(0, 120)), test, facecolors='teal', alpha=1)
        ax.plot(list(range(0, 120)), mean, '--', c='limegreen', label='Mean')
        ax.plot(range(0, 120), test, ' ', c='indianred',
                 linewidth=1.0,
                 markevery=highest,
                 marker='^',
                 markersize=12)
        ax.text(highest[0], max(test) - 10, f'{round(max(test))} MiB', fontsize=12)
        ax.plot(range(0, 120), test, ' ', c='lime',
                 linewidth=1.0,
                 markevery=lowest,
                 marker='v',
                 markersize=12)
        ax.plot(list(range(0, 120)), test, 'darkorchid',
                 alpha=.5,
                 linewidth=.75,
                 drawstyle='steps-pre',
                 label='Steps')
        ax.plot(range(0, 240), avg, c='cyan',
                 linewidth=1.5,
                 markevery=1,
                 label='Average',
                alpha=0.5)

        ax.legend(loc='best', bbox_transform=plt.gcf().transFigure)
        save = current.strftime("%Y-%m-%d%H%M")
        plt.savefig(f'/home/myst/mystbot/rams/{save}', bbox_inches='tight')  # !!!VPS!!!
        self.bot._latest_ram[save] = f'/home/myst/mystbot/rams/{save}.png'  # !!!VPS!!!

        plt.clf()
        plt.close()
        return save

    @commands.command(name='wsping')
    async def _ping(self, ctx):
        """Ping. Shown as a pretty graph."""

        current = datetime.datetime.utcnow().strftime('%Y-%m-%d%H%M')

        if len(self.bot._pings) < 60:
            return await ctx.send(f'Latency: **`{self.bot.latency * 1000}`**')

        await ctx.channel.trigger_typing()
        try:
            pfile = self.bot._latest_ping[current]
            return await ctx.send(file=discord.File(pfile))
        except:
            pass

        getfile = functools.partial(self.ping_plotter)
        pfile = await self.bot.loop.run_in_executor(self.threadex, getfile)
        await ctx.send(file=discord.File(f'/home/myst/mystbot/pings/{pfile}.png'))  # !!!VPS!!!

    @commands.command(name='ram')
    async def _ram(self, ctx):
        """Ram usage. Shown as a pretty graph."""

        current = datetime.datetime.utcnow().strftime('%Y-%m-%d%H%M')

        if len(self.bot._ram) < 60:
            return await ctx.send(f'Ram Usage: **`{self.bot._ram[-1]}`**')

        await ctx.channel.trigger_typing()
        try:
            pfile = self.bot._latest_ram[current]
            return await ctx.send(file=discord.File(pfile))
        except:
            pass

        getfile = functools.partial(self.ram_plotter)
        pfile = await self.bot.loop.run_in_executor(self.threadex, getfile)
        await ctx.send(file=discord.File(f'/home/myst/mystbot/rams/{pfile}.png'))  # !!!VPS!!!

    async def sick(self, ctx, name: str=None):
        pass


def setup(bot):
    bot.add_cog(Plots(bot))
