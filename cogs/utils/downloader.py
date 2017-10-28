import asyncio
import threading
import subprocess
import uuid

import json
import math

import youtube_dl


class Downloader(threading.Thread):

    def __init__(self, queue: asyncio.Queue, ctx, search: str):
        super().__init__()
        self.queue = queue
        self.ctx = ctx
        self.search = search

        self._stop = threading.Event()
        self.daemon = True
        self._threading_error = None
        self._ytdl_error = None

    def run(self):
        try:
            self._run()
        except Exception as e:
            self._threading_error = e
            # self.stop()
        finally:
            pass

    def _run(self):
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.ctx.guild.id}/{self.outtmpl_seed()}%(extractor)s_%(id)s.%(ext)s',
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
        ef_info = ytdl.extract_info(download=False, url=self.search)
        ytdl.params['extract_flat'] = False

        if 'entries' in ef_info:
            length = len(ef_info['entries'])
        else:
            length = 1

        while not self._stop.is_set():
            for v in range(1, length + 1):

                try:
                    ytdl.params.update({'playlistend': v, 'playliststart': v})
                    info = ytdl.extract_info(download=True, url=self.search)
                    self.process_info(info, ytdl)
                except Exception as e:
                    self._ytdl_error = e
                    if length <= 1:
                        return self.stop()
                    else:
                        continue
            try:
                return self.stop()
            except Exception as e:
                print(e)

    def stop(self):
        print('Stopping...')
        self._stop.set()
        return

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

    def process_info(self, info, ytdl):

        if 'entries' in info:
            info = info['entries'][0]

        duration = info.get('duration') or self.get_duration(info.get('url'))
        song_info = {'title': info.get('title'),
                     'weburl': info.get('webpage_url'),
                     'duration': duration,
                     'views': info.get('view_count'),
                     'thumb': info.get('thumbnail'),
                     'requester': self.ctx.author,
                     'upload_date': info.get('upload_date', '\uFEFF')}

        try:
            self.queue.put_nowait({'source': ytdl.prepare_filename(info),
                                   'info': song_info,
                                   'channel': self.ctx.channel})
        except Exception as e:
            self._ytdl_error = e
