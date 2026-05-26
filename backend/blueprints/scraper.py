import os
import re
import platform
import threading
import queue
from urllib.parse import urlparse
from flask import Blueprint, jsonify, request, Response, current_app
from bs4 import BeautifulSoup
import requests
import yt_dlp
from ..utils import login_required

scraper_bp = Blueprint('scraper', __name__)




@scraper_bp.route('/preview-video', methods=['POST'])
@login_required
def preview_video():
    url = request.get_json().get('url')
    if not url:
        return jsonify({'error': 'URL kosong'}), 400
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                entries = []
                for idx, entry in enumerate(info['entries']):
                    if not entry:
                        continue
                    if idx >= 50:
                        break
                    entries.append({'title': entry.get('title', 'Video Tanpa Judul'), 'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"})
                return jsonify({'type': 'playlist', 'title': info.get('title', 'YouTube Playlist'), 'entries': entries, 'playlist_url': url})
            duration_sec = info.get('duration')
            duration_str = f"{divmod(int(duration_sec), 60)[0]}:{divmod(int(duration_sec), 60)[1]:02d}" if duration_sec else 'Live / Tidak diketahui'
            return jsonify({'type': 'video', 'title': info.get('title', 'Judul Tidak Diketahui'), 'thumbnail': info.get('thumbnail', ''), 'duration': duration_str, 'url': url})
    except Exception:
        return jsonify({'error': 'Gagal mengambil data video/playlist'}), 500


@scraper_bp.route('/stream-download')
@login_required
def stream_download():
    video_url = request.args.get('url')
    download_type = request.args.get('type', 'video')
    resolution = request.args.get('res', '720')

    def generate():
        q = queue.Queue()
        prefix = 'Audio' if download_type == 'audio' else 'Video'
        output_template = os.path.join('static/file_manager/Download', f"{prefix}_%(id)s_Ultoid.%(ext)s")
        lokasi_ffmpeg = './ffmpeg.exe' if platform.system() == 'Windows' else '/usr/bin/ffmpeg'
        ydl_opts = {'outtmpl': output_template, 'restrictfilenames': True, 'quiet': True, 'no_warnings': True, 'ffmpeg_location': lokasi_ffmpeg, 'noplaylist': False}
        if download_type == 'audio':
            q.put('MSG|🎶 Menyiapkan ekstraksi Audio...')
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
        else:
            q.put(f'MSG|🎬 Menyiapkan Video MP4 (Maks {resolution}p)...')
            ydl_opts.update({'merge_output_format': 'mp4'})
            if resolution == 'best':
                ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})
            else:
                ydl_opts.update({'format': f'bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={resolution}][ext=mp4]/best'})

        def run_ytdlp():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    def my_hook(d):
                        if d['status'] == 'downloading':
                            raw_percent = d.get('_percent_str', '0%')
                            clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', raw_percent).replace('%', '').strip()
                            q.put(f"PROGRESS|{clean_percent}|{os.path.basename(d.get('filename', 'file'))}")
                        elif d['status'] == 'finished':
                            q.put('MSG|⏳ Menyelesaikan file ini (merging/ekstraksi)...')
                    ydl.add_progress_hook(my_hook)
                    q.put('MSG|Sedang terhubung ke server...')
                    info = ydl.extract_info(video_url, download=True)
                    if 'entries' in info:
                        q.put('DONE|PLAYLIST')
                    else:
                        q.put(f"DONE|{prefix}_{info['id']}_Ultoid.{ 'mp3' if download_type == 'audio' else 'mp4'}")
            except Exception as e:
                q.put(f"ERROR|{str(e)}")

        threading.Thread(target=run_ytdlp).start()
        while True:
            msg = q.get()
            if msg.startswith('PROGRESS|') or msg.startswith('DONE|') or msg.startswith('ERROR|'):
                yield f"data: {msg}\n\n"
                if msg.startswith('DONE|') or msg.startswith('ERROR|'):
                    break
            elif msg.startswith('MSG|'):
                yield f"data: {msg.split('|', 1)[1]}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@scraper_bp.route('/api/proxy-image')
@login_required
def proxy_image():
    url = request.args.get('url', '')
    if not url.startswith('https://'):
        return 'Invalid URL', 400
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, stream=True, timeout=10)
        content_type = r.headers.get('Content-Type', 'image/jpeg')
        return Response(r.content, content_type=content_type, headers={'Cache-Control': 'public, max-age=86400'})
    except Exception as e:
        return str(e), 500
