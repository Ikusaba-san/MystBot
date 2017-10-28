import discord
from discord.ext import commands

import random


class Random:
    """Commands which are based on RNG's."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='choose', aliases=['select'])
    async def _choose(self, ctx, *args):
        """Make Myst choose between two or more things."""

        choice = random.choice(args)
        await ctx.send(f'**`{choice}`**')

    @commands.command(name='roll')
    async def roll_dice(self, ctx, first: int, second: int):
        """Returns a number between two selected numbers."""

        rolled = random.randint(first, second)
        await ctx.send(f'{ctx.author.mention} rolled: **`{rolled}`**')


def setup(bot):
    bot.add_cog(Random(bot))
