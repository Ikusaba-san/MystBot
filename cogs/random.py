import discord
from discord.ext import commands

import random


class Random:

    def __init__(self):
        pass

    @commands.command(name='choose', aliases=['select'])
    async def _choose(self, ctx, *args):
        """Make Myst choose between 2 or more things."""

        choice = random.choice(args)
        await ctx.send(f'**`{choice}`**')

    @commands.command(name='roll')
    async def roll_dice(self, ctx, first: int, second: int):
        """Returns a number between your two selections."""

        rolled = random.randint(first, second)
        await ctx.send(f'{ctx.author.mention} rolled: **`{rolled}`**')