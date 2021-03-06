import asyncio
import subprocess
import uuid
import functools
from concurrent.futures import ThreadPoolExecutor as tpe

import json
import math

import youtube_dl


class Downloader:

    async def run(self, queue, ctx, bot, search):
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{ctx.guild.id}/{self.outtmpl_seed()}%(extractor)s_%(id)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'playlistend': 50,
        }

        ytdl = youtube_dl.YoutubeDL(opts)

        ytdl.params['extract_flat'] = True
        ef_info = ytdl.extract_info(download=False, url=search)
        ytdl.params['extract_flat'] = False

        if 'entries' in ef_info:
            length = len(ef_info['entries'])
        else:
            length = 1

        for v in range(1, length + 1):

            try:
                ytdl.params.update({'playlistend': v, 'playliststart': v})
                tdl = functools.partial(ytdl.extract_info, download=True, url=search)
                info = await bot.loop.run_in_executor(tpe(max_workers=4), tdl)
            except Exception as e:
                self._ytdl_error = e
                if length <= 1:
                    return await ctx.send(f'**There was an error processing your song.** ```css\n[{e}]\n```')
                else:
                    continue

            if 'entries' in info:
                info = info['entries'][0]

            duration = info.get('duration') or self.get_duration(info.get('url'))
            song_info = {'title': info.get('title'),
                         'weburl': info.get('webpage_url'),
                         'duration': duration,
                         'views': info.get('view_count'),
                         'thumb': info.get('thumbnail'),
                         'requester': ctx.author,
                         'upload_date': info.get('upload_date', '\uFEFF')}

            if length == 1:
                await ctx.send(f'```ini\n[Added {song_info["title"]} to the queue.]\n```', delete_after=15)
            try:
                await queue.put({'source': ytdl.prepare_filename(info), 'info': song_info, 'channel': ctx.channel})
            except Exception as e:
                self._ytdl_error = e

    def get_duration(self, url):

        cmd = f'ffprobe -v error -show_format -of json {url}'
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        data = json.loads(output)
        duration = data['format']['duration']

        return math.ceil(float(duration))

    def outtmpl_seed(self):
        ytid = str(uuid.uuid4()).replace('-', '')
        return str(int(ytid, 16))
