import discord
from discord.ext import commands
from motor import motor_asyncio

import asyncio
import aiohttp
import sys, traceback
from collections import deque
import psutil
import logging
from configparser import ConfigParser
import contextlib
import datetime
import json
import pprint

try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop(uvloop)


loop = asyncio.get_event_loop()
dbc = motor_asyncio.AsyncIOMotorClient(minPoolSize=5)

token = ConfigParser()
token.read('/home/myst/mystbot/mystconfig.ini')  # !!!VPS!!!


async def get_prefix(b, msg):
    await b._cache_ready.wait()

    defaults = commands.when_mentioned_or(*['myst pls ', 'myst '])(b, msg)

    if msg is None:
        return 'myst '

    if msg.guild.id is None:
        return defaults

    dbp = dbc['prefix'][str(msg.guild.id)]

    if await dbp.find().count() <= 0:
        await dbp.insert_many([{'_id': 'myst '}, {'_id': 'myst pls '}])
        bot.prefix_cache[msg.guild.id] = ['myst ', 'myst pls ']
        return defaults
    else:
        prefixes = sorted(bot.prefix_cache[msg.guild.id], reverse=True)
        return commands.when_mentioned_or(*prefixes)(b, msg)

init_ext = ('cogs.admin',
            'cogs.utils.handler',
            'cogs.moderation',
            'cogs.music',
            'cogs.apis',
            'cogs.koth',
            'cogs.statistics',
            'cogs.meta')


class Botto(commands.AutoShardedBot):

    def __init__(self):
        self.blocks = {}
        self.prefix_cache = {}
        self._help_pages = None
        self._latest_ping = {}
        self._latest_ram = {}

        self.dbc = dbc
        self.session = None
        self.uptime = datetime.datetime.utcnow()
        self.appinfo = None
        self.process = psutil.Process()

        self._cache_ready = asyncio.Event()

        self._ram = deque(maxlen=120)  # 30 Minutes | Polled 15s [30 * 120 / 60]
        self._pings = deque(maxlen=60)  # 60 Minutes | Polled 60s [60 * 60 / 60]
        self._cpu = deque(maxlen=120)  # 30 Minutes | Polled 15s [15 * 120 / 60]
        self._stasks = {}
        self._starters = (self._task_pings, self._task_ram)
        self._players = {}
        self._player_tasks = {}

        self._counter_commands = None
        self._counter_messages = None
        self._counter_songs = None

        super().__init__(command_prefix=get_prefix, description=None)

    async def music_cleanup(self, ctx, player):
        vc = ctx.guild.voice_client
        print(1)

        try:
            await player.playing.delete()
        except Exception as e:
            print(e)
            print('1e')

        print(2)

        try:
            vc._connected.clear()
            try:
                if vc.ws:
                    await vc.ws.close()

                await vc.terminate_handshake(remove=True)
            finally:
                if vc.socket:
                    vc.socket.close()
        except Exception as e:
            print(e)
            print('2e')

        print(3)

        try:
            player.threadex.shutdown(wait=False)
        except Exception as e:
            print(e)
            print('3e')

        print(4)

        print(5)

        try:
            del bot._players[ctx.guild.id]
            del bot._player_tasks[ctx.guild.id]
        except Exception as e:
            print(e)
            print('5e')

        print(6)

        try:
            player._task_playerloop.cancel()
            player._task_downloader.cancel()
        except Exception as e:
            print(e)
            print('6e')

        print(7)

        try:
            del player
        except Exception as e:
            print(e)
            print('7e')

        print(8)

        print(bot._players)
        print(bot._player_tasks)
        print(player)
        return

    # Called in on_ready()
    async def _load_cache(self):
        self._cache_ready.clear()
        self.session = aiohttp.ClientSession(loop=loop)

        # Prefixes
        for guild in self.guilds:
            if await self.dbc['prefix'][str(guild.id)].find({}).count() <= 0:
                await self.dbc['prefix'][str(guild.id)].insert_many([{'_id': 'myst '}, {'_id': 'myst pls '}])
            self.prefix_cache[guild.id] = [p['_id'] async for p in self.dbc['prefix'][str(guild.id)].find({})]

        # Blocks
        async for mem in dbc['owner']['blocks'].find({}):
            self.blocks[mem['_id']] = mem['name']

        com_counter = await self.dbc['owner']['stats'].find_one({'_id': 'command_counter'})
        msg_counter = await self.dbc['owner']['stats'].find_one({'_id': 'message_counter'})
        sng_counter = await self.dbc['owner']['stats'].find_one({'_id': 'songs_counter'})
        self._counter_commands = com_counter['count'] if com_counter else 0
        self._counter_messages = msg_counter if msg_counter else 0
        self._counter_songs = sng_counter if sng_counter else 0
        await self._setup_tasks()

        return self._cache_ready.set()

    async def _setup_tasks(self):

        for exc in self._starters:
            task = self.loop.create_task(exc())
            self._stasks[exc.__name__] = task

    async def _task_pings(self):
        await self.wait_until_ready()

        while not self.is_closed():
            if self.latency <= 0:
                await asyncio.sleep(1)
                continue
            self._pings.append(self.latency * 1000)
            await asyncio.sleep(60)

    async def _task_ram(self):
        await self.wait_until_ready()

        while not self.is_closed():
            self._ram.append(self.process.memory_full_info().uss / 1024**2)
            await asyncio.sleep(15)

    async def _task_cpu(self):
        pass

    async def fetch(self, url: str, headers: dict = None, timeout: float = None,
                    return_type: str = None, **kwargs):

        async with self.session.get(url, headers=headers, timeout=timeout, **kwargs) as resp:
            if return_type:
                cont = getattr(resp, return_type)
                return resp, await cont()
            else:
                return resp, None

    async def poster(self, url: str, headers: dict = None, timeout: float = None,
                     return_type: str = None, **kwargs):

        async with self.session.post(url, headers=headers, timeout=timeout, **kwargs) as resp:
            if return_type:
                cont = getattr(resp, return_type)
                return resp, await cont()
            else:
                return resp, None

    async def msg_reactor(self, message, *react):

        for r in react:
            try:
                await message.add_reaction(r)
            except:
                pass

    async def create_gist(self, description, files, pretty=False):

        if pretty:
            file_dict = {f[0]: {"content": pprint.pformat(f[1])} for f in files}
        else:
            file_dict = {f[0]: {"content": f[1]} for f in files}
        payload = {"description": description, "public": True, "files": file_dict}
        resp, respj = await self.poster('https://api.github.com/gists', data=json.dumps(payload), return_type='json')
        return respj['html_url']

bot = Botto()
bot.remove_command('help')


@contextlib.contextmanager
def setup_logging():
    try:
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.INFO)
        logging.getLogger('myst').setLevel(logging.INFO)

        log = logging.getLogger()
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='myst.log', encoding='utf-8', mode='w')
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)

        yield
    finally:
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)


@bot.event
async def on_ready():

    await bot._load_cache()
    bot.appinfo = await bot.application_info()

    print(f'\n\nLogging in as: {bot.user.name} - {bot.user.id}\n')
    print(f'Version: {discord.__version__}\n')

    await bot.change_presence(game=discord.Game(name='💩', type=1, url='https://twitch.tv/evieerushu'))

    if __name__ == '__main__':
        for extension in init_ext:
            try:
                bot.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()
    print(f'Successfully logged in and booted...!')

async def shutdown():

    log = logging.getLogger('myst')
    print('\n\nAttempting to logout and shutdown...\n')

    await dbc.fsync(lock=True)

    try:
        await bot.logout()
    except Exception as e:
        await dbc.unlock()
        msg = f'Attempt to Logout failed:: {type(e)}: {e}'
        log.critical(msg)
        return print(msg)

    await dbc.unlock()

    for x in asyncio.Task.all_tasks():
        try:
            x.cancel()
        except:
            pass

    print('Logged out... Closing down.')
    log.info(f'Clean Log-Out:: {datetime.datetime.utcnow()}')

    sys.exit(0)

with setup_logging():

    try:
        loop.run_until_complete(bot.start(token.get('TOKEN', '_id'), bot=True, reconnect=True))  # !!!VPS!!!
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown())
