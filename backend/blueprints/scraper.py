import os
import re
import platform
import threading
import queue
from urllib.parse import urlparse
from flask import Blueprint, jsonify, request, Response, current_app
import yt_dlp
from ..utils import login_required
from ..config import FM_ROOT
from datetime import datetime

scraper_bp = Blueprint('scraper', __name__)

SUPPORTED_MEDIA_HOSTS = {
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'instagram.com': 'Instagram',
    'instagr.am': 'Instagram',
    'tiktok.com': 'TikTok',
    'vm.tiktok.com': 'TikTok',
    'vt.tiktok.com': 'TikTok',
}
IMAGE_EXTENSIONS = {'avif', 'gif', 'jpeg', 'jpg', 'png', 'webp'}
ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def _media_provider(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password:
            return None
        host = (parsed.hostname or '').lower().rstrip('.')
    except ValueError:
        return None

    for domain, provider in SUPPORTED_MEDIA_HOSTS.items():
        if host == domain or (domain in {'youtube.com', 'instagram.com', 'tiktok.com'} and host.endswith(f'.{domain}')):
            return provider
    return None


def _is_image(info):
    if not isinstance(info, dict):
        return False
    if str(info.get('ext', '')).lower() in IMAGE_EXTENSIONS:
        return True
    formats = info.get('formats') or []
    if not isinstance(formats, (list, tuple)):
        return False
    formats = [media_format for media_format in formats if isinstance(media_format, dict)]
    return bool(formats) and all(str(media_format.get('ext', '')).lower() in IMAGE_EXTENSIONS for media_format in formats)


def _playlist_count(info, displayed_count):
    try:
        return max(displayed_count, int(info.get('playlist_count') or displayed_count))
    except (TypeError, ValueError):
        return displayed_count


@scraper_bp.route('/preview-video', methods=['POST'])
@login_required
def preview_video():
    data = request.get_json(silent=True)
    url = data.get('url', '').strip() if isinstance(data, dict) and isinstance(data.get('url'), str) else ''
    if not url:
        return jsonify({'error': 'URL kosong'}), 400
    provider = _media_provider(url)
    if not provider:
        return jsonify({'error': 'Tautan harus berasal dari YouTube, Instagram, atau TikTok.'}), 400
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if isinstance(info, dict) and info.get('entries') is not None:
                entries = []
                raw_entries = info.get('entries')
                if not isinstance(raw_entries, (list, tuple)):
                    return jsonify({'error': 'Format daftar media dari platform tidak valid.'}), 502
                for idx, entry in enumerate(raw_entries):
                    if not entry or not isinstance(entry, dict):
                        continue
                    if idx >= 50:
                        break
                    entries.append({
                        'title': entry.get('title') or f'Media {idx + 1}',
                        'playlist_index': entry.get('playlist_index') or idx + 1,
                        'thumbnail': entry.get('thumbnail', ''),
                    })
                count = _playlist_count(info, len(entries))
                return jsonify({
                    'type': 'playlist',
                    'provider': provider,
                    'title': info.get('title') or f'{provider} media',
                    'entries': entries,
                    'count': count,
                    'truncated': count > len(entries),
                    'playlist_url': url,
                })
            if not isinstance(info, dict):
                return jsonify({'error': 'Platform tidak mengembalikan informasi media yang valid.'}), 502

            duration_sec = info.get('duration')
            duration_str = f"{int(duration_sec) // 60}:{int(duration_sec) % 60:02d}" if duration_sec else 'Durasi tidak tersedia'
            return jsonify({
                'type': 'image' if _is_image(info) else 'video',
                'provider': provider,
                'title': info.get('title') or 'Judul tidak tersedia',
                'thumbnail': info.get('thumbnail', ''),
                'duration': duration_str,
                'url': url,
            })
    except Exception as exc:
        current_app.logger.warning('Media preview failed for %s: %s', provider, exc)
        return jsonify({'error': 'Gagal mengambil informasi media. Tautan mungkin privat, tidak tersedia, atau tidak didukung.'}), 502


@scraper_bp.route('/stream-download')
@login_required
def stream_download():
    video_url = request.args.get('url')
    download_type = request.args.get('type', 'video')
    resolution = request.args.get('res', '720')
    playlist_item = request.args.get('item')
    if not video_url:
        return jsonify({'error': 'URL kosong'}), 400
    provider = _media_provider(video_url)
    if not provider:
        return jsonify({'error': 'Tautan harus berasal dari YouTube, Instagram, atau TikTok.'}), 400
    if download_type not in {'audio', 'video'}:
        return jsonify({'error': 'Tipe unduhan tidak valid'}), 400
    if resolution not in {'360', '480', '720', '1080', 'best'}:
        return jsonify({'error': 'Resolusi tidak valid'}), 400
    if playlist_item is not None and (
        not playlist_item.isdigit() or len(playlist_item) > 7 or int(playlist_item) < 1
    ):
        return jsonify({'error': 'Nomor item playlist tidak valid.'}), 400

    logger = current_app.logger

    def generate():
        q = queue.Queue()
        output_folder = os.path.join(FM_ROOT, 'Download')
        os.makedirs(output_folder, exist_ok=True)
        output_template = os.path.join(output_folder, 'Media_%(extractor)s_%(id)s_Ultoid.%(ext)s')
        lokasi_ffmpeg = './ffmpeg.exe' if platform.system() == 'Windows' else '/usr/bin/ffmpeg'
        ydl_opts = {
            'outtmpl': output_template,
            'restrictfilenames': True,
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': lokasi_ffmpeg,
            'noplaylist': False,
            'extract_flat': 'in_playlist',
        }
        if playlist_item is not None:
            ydl_opts['playlist_items'] = playlist_item

        def run_ytdlp():
            try:
                q.put('MSG|Memeriksa tautan dan jenis media...')
                with yt_dlp.YoutubeDL(ydl_opts) as metadata_ydl:
                    info = metadata_ydl.extract_info(video_url, download=False)
                is_collection = isinstance(info, dict) and info.get('entries') is not None
                if is_collection and playlist_item is None:
                    q.put(f'ERROR|Ini adalah playlist atau kumpulan media {provider}. Pilih satu item dari daftar; tidak ada item yang diunduh otomatis.')
                    return
                if is_collection:
                    selected_opts = {
                        **ydl_opts,
                        'extract_flat': False,
                        'playlist_items': playlist_item,
                    }
                    with yt_dlp.YoutubeDL(selected_opts) as metadata_ydl:
                        info = metadata_ydl.extract_info(video_url, download=False)
                    if isinstance(info, dict) and info.get('entries') is not None:
                        entries = list(info.get('entries') or [])
                        if not entries:
                            q.put('ERROR|Item playlist tidak ditemukan atau tidak dapat diakses.')
                            return
                        requested_index = int(playlist_item)
                        selected_entry = next(
                            (
                                entry for entry in entries
                                if isinstance(entry, dict)
                                and str(entry.get('playlist_index')) == str(requested_index)
                            ),
                            entries[0] if len(entries) == 1 else None,
                        )
                        if not isinstance(selected_entry, dict):
                            q.put('ERROR|Item pilihan tidak dapat dipastikan. Tidak ada item yang diunduh.')
                            return
                        info = selected_entry

                if not isinstance(info, dict):
                    q.put('ERROR|Informasi media tidak valid.')
                    return

                is_image = _is_image(info)
                if download_type == 'audio' and is_image:
                    q.put('ERROR|Tautan ini berisi foto, bukan video yang dapat dikonversi menjadi audio.')
                    return
                download_opts = {
                    **ydl_opts,
                    'noplaylist': not is_collection,
                    'extract_flat': False,
                }
                if is_collection:
                    download_opts['playlist_items'] = playlist_item
                if is_image:
                    download_opts.update({
                        'outtmpl': os.path.join(output_folder, 'Photo_%(extractor)s_%(id)s_Ultoid.%(ext)s'),
                        'format': 'best',
                    })
                    q.put('MSG|Mengunduh foto dalam format aslinya...')
                elif download_type == 'audio':
                    download_opts.update({
                        'outtmpl': os.path.join(output_folder, 'Audio_%(extractor)s_%(id)s_Ultoid.%(ext)s'),
                        'format': 'bestaudio/best',
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                    })
                    q.put('MSG|Menyiapkan ekstraksi audio...')
                else:
                    video_template = (
                        os.path.join(output_folder, 'Video_%(id)s_Ultoid.%(ext)s')
                        if provider == 'YouTube'
                        else output_template
                    )
                    download_opts.update({
                        'outtmpl': video_template,
                        'merge_output_format': 'mp4',
                        'format': (
                            'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                            if resolution == 'best'
                            else f'bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={resolution}][ext=mp4]/best'
                        ),
                    })
                    q.put(f'MSG|Menyiapkan video (maksimum {resolution}p)...')

                def my_hook(d):
                    if not isinstance(d, dict):
                        return
                    if d.get('status') == 'downloading':
                        raw_percent = d.get('_percent_str', '0%')
                        clean_percent = ANSI_ESCAPE_RE.sub('', raw_percent).replace('%', '').strip()
                        q.put(f"PROGRESS|{clean_percent}|{os.path.basename(d.get('filename', 'file'))}")
                    elif d.get('status') == 'finished':
                        q.put('MSG|⏳ Menyelesaikan file ini (merging/ekstraksi)...')

                def download_with_options(options):
                    with yt_dlp.YoutubeDL(options) as downloader:
                        downloader.add_progress_hook(my_hook)
                        result = downloader.extract_info(video_url, download=True)
                    return downloader, result

                try:
                    ydl, downloaded = download_with_options(download_opts)
                except yt_dlp.utils.DownloadError as error:
                    if provider != 'YouTube' or download_type != 'video' or '403' not in str(error):
                        raise
                    fallback_format = (
                        'best[ext=mp4]/best'
                        if resolution == 'best'
                        else f'best[height<={resolution}][ext=mp4]/best[height<={resolution}]/best'
                    )
                    fallback_opts = {**download_opts, 'format': fallback_format}
                    q.put('MSG|Format YouTube pilihan ditolak (HTTP 403). Mencoba format MP4 alternatif...')
                    logger.warning(
                        'YouTube download format was rejected with HTTP 403; retrying with a combined format'
                    )
                    ydl, downloaded = download_with_options(fallback_opts)
                if not isinstance(downloaded, dict):
                    q.put('ERROR|Platform tidak mengembalikan file hasil unduhan yang valid.')
                    return
                if downloaded.get('entries') is not None:
                    raw_downloaded_entries = downloaded.get('entries') or []
                    if not isinstance(raw_downloaded_entries, (list, tuple)):
                        q.put('ERROR|Platform mengembalikan format daftar media yang tidak valid.')
                        return
                    downloaded_entries = list(raw_downloaded_entries)
                    selected_download = next(
                        (
                            entry for entry in downloaded_entries
                            if isinstance(entry, dict)
                            and str(entry.get('playlist_index')) == str(playlist_item)
                        ),
                        None,
                    )
                    if selected_download is None and len(downloaded_entries) == 1:
                        selected_download = downloaded_entries[0]
                    if not isinstance(selected_download, dict):
                        q.put('ERROR|Platform mengembalikan lebih dari satu item. Unduhan dibatalkan untuk mencegah unduhan massal.')
                        return
                    downloaded = selected_download
                requested_downloads = downloaded.get('requested_downloads') or []
                if not isinstance(requested_downloads, (list, tuple)):
                    requested_downloads = []
                candidates = [downloaded.get('filepath'), downloaded.get('_filename')]
                candidates.extend(
                    item.get('filepath')
                    for item in requested_downloads
                    if isinstance(item, dict)
                )
                file_path = next(
                    (candidate for candidate in candidates if candidate and os.path.isfile(candidate)),
                    None,
                )
                if not file_path:
                    prepared_path = ydl.prepare_filename(downloaded)
                    expected_path = (
                        os.path.splitext(prepared_path)[0] + '.mp3'
                        if download_type == 'audio'
                        else prepared_path
                    )
                    if os.path.isfile(expected_path):
                        file_path = expected_path
                if not file_path:
                    q.put('ERROR|Unduhan selesai tetapi file hasil tidak ditemukan di folder Download.')
                    return
                q.put(f'DONE|{os.path.basename(file_path)}')
            except Exception as e:
                logger.exception('Media download failed for %s', provider)
                message = ANSI_ESCAPE_RE.sub('', str(e)).replace('\r', ' ').replace('\n', ' ').replace('|', '/')
                q.put(f'ERROR|{message or "Gagal mengunduh media."}')

        threading.Thread(target=run_ytdlp, daemon=True).start()
        while True:
            msg = q.get()
            if msg.startswith('PROGRESS|') or msg.startswith('DONE|') or msg.startswith('ERROR|'):
                yield f"data: {msg}\n\n"
                if msg.startswith('DONE|') or msg.startswith('ERROR|'):
                    break
            elif msg.startswith('MSG|'):
                yield f"data: {msg.split('|', 1)[1]}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@scraper_bp.route('/api/download-history')
@login_required
def download_history():
    download_folder = os.path.join(FM_ROOT, 'Download')
    if not os.path.exists(download_folder):
        return jsonify([])
    
    files_data = []
    for filename in os.listdir(download_folder):
        filepath = os.path.join(download_folder, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            size_mb = round(stat.st_size / (1024 * 1024), 2)
            mod_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
            
            thumbnail = ""
            if "_Ultoid" in filename and filename.startswith(('Video_', 'Media_', 'Photo_')):
                try:
                    if filename.startswith('Video_'):
                        yt_id = filename.split('Video_', 1)[1].split('_Ultoid', 1)[0]
                        thumbnail = f"https://img.youtube.com/vi/{yt_id}/mqdefault.jpg"
                except Exception:
                    pass

            files_data.append({
                'filename': filename,
                'size_mb': size_mb,
                'time': mod_time,
                'timestamp': stat.st_mtime,
                'thumbnail': thumbnail
            })
    
    # Sort by newest first
    files_data.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify(files_data)
