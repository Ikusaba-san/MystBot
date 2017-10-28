import asyncio
import threading
import subprocess
import uuid

import json
import math
import time

import youtube_dl


class Downloader(threading.Thread):

    def __init__(self, search: str):
        super().__init__()
        self.queue = []
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
            'outtmpl': f'{self.outtmpl_seed()}/%(extractor)s_%(id)s.%(ext)s',
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
                        return self.queue.append({'error': self._ytdl_error, 'type': 'YTDL'})
                    else:
                        continue
            self.stop()

    def stop(self):
        self._stop.set()
        time.sleep(5)
        return self.join()

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
                     'upload_date': info.get('upload_date', '\uFEFF')}
        file = ytdl.prepare_filename(info)

        try:
            self.queue.append({'source': file, 'info': song_info})
        except Exception as e:
            self._ytdl_error = e