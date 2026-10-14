from flask import Blueprint, render_template, redirect, url_for, jsonify, request, send_from_directory, current_app, send_file
from ..utils import get_safe_path, login_required
from ..config import NOTES_FILE, TASKS_FILE, OUTPUT_FOLDER, GAMES_FILE, NOTES_IMAGES_FOLDER, SAVES_FOLDER, GAME_IMAGES_FOLDER, MOVIES_FILE, FM_ROOT
import os
from werkzeug.utils import secure_filename
import uuid
import json
import subprocess
import math
import mimetypes

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/space', endpoint='space')
@login_required
def space():
    return render_template('space.html')


@pages_bp.route('/translate', endpoint='translate_app')
@login_required
def translate_app():
    return render_template('index.html')


@pages_bp.route('/downloader', endpoint='downloader_page')
@login_required
def downloader_page():
    return render_template('downloader.html')


@pages_bp.route('/task', endpoint='task_manager')
@login_required
def task_manager():
    return render_template('task.html')


@pages_bp.route('/notes', endpoint='notes_app')
@login_required
def notes_app():
    return render_template('notes.html')


@pages_bp.route('/emulator', endpoint='emulator')
@login_required
def emulator():
    return render_template('emulator.html')


@pages_bp.route('/game-admin', endpoint='game_admin')
@login_required
def game_admin():
    return render_template('game_admin.html')


@pages_bp.route('/download_admin/<path:filename>', endpoint='download_admin')
@login_required
def download_admin(filename):
    download_folder = os.path.join(FM_ROOT, 'Download')
    return send_from_directory(os.path.abspath(download_folder), filename, as_attachment=True)


@pages_bp.route('/api/notes', methods=['GET', 'POST'])
@login_required
def api_notes():
    if request.method == 'POST':
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(request.json, f, ensure_ascii=False, indent=4)
        return jsonify({'success': True})
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify([])


@pages_bp.route('/api/tasks', methods=['GET', 'POST'])
@login_required
def api_tasks():
    if request.method == 'POST':
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(request.json, f, ensure_ascii=False, indent=4)
        return jsonify({'success': True})
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({})


@pages_bp.route('/api/custom_games', methods=['GET', 'POST'])
@login_required
def api_custom_games():
    if request.method == 'POST':
        data = request.json
        with open(GAMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return jsonify({'success': True})
    if os.path.exists(GAMES_FILE):
        with open(GAMES_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify([])

@pages_bp.route('/api/notes/upload_image', methods=['POST'])
@login_required
def upload_note_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    if file:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(NOTES_IMAGES_FOLDER, filename)
        file.save(filepath)
        # return the absolute path starting with /static for frontend rendering
        return jsonify({'success': True, 'url': f'/{NOTES_IMAGES_FOLDER}/{filename}'})
    return jsonify({'success': False, 'error': 'Failed to upload'}), 500


@pages_bp.route('/api/emulator/upload_rom', methods=['POST'])
@login_required
def upload_rom():
    if 'rom_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    file = request.files['rom_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        roms_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'roms'))
        os.makedirs(roms_dir, exist_ok=True)
        filepath = os.path.join(roms_dir, filename)
        file.save(filepath)
        return jsonify({'success': True, 'filename': filename})
    return jsonify({'success': False, 'error': 'Failed to upload'}), 500

@pages_bp.route('/api/emulator/upload_image', methods=['POST'])
@login_required
def upload_game_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    if file:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(GAME_IMAGES_FOLDER, filename)
        file.save(filepath)
        return jsonify({'success': True, 'url': f'/{GAME_IMAGES_FOLDER}/{filename}'})
    return jsonify({'success': False, 'error': 'Failed to upload'}), 500


@pages_bp.route('/play/<int:game_id>', endpoint='play_game')
@login_required
def play_game(game_id):
    if os.path.exists(GAMES_FILE):
        with open(GAMES_FILE, 'r', encoding='utf-8') as f:
            games = json.load(f)
            game = next((g for g in games if g.get('id') == game_id), None)
            if game:
                state_file = os.path.join(SAVES_FOLDER, f"{game_id}.state")
                has_save = os.path.exists(state_file)
                return render_template('player.html', game=game, has_save=has_save)
    return "Game not found", 404


@pages_bp.route('/roms/<path:filename>', endpoint='serve_rom')
@login_required
def serve_rom(filename):
    roms_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'roms'))
    return send_from_directory(roms_dir, filename)


@pages_bp.route('/api/emulator/save/<int:game_id>', methods=['POST'])
@login_required
def save_emulator_state(game_id):
    state_file = os.path.join(SAVES_FOLDER, f"{game_id}.state")
    data = request.get_data()
    with open(state_file, 'wb') as f:
        f.write(data)
    return jsonify({'success': True})


@pages_bp.route('/api/emulator/load/<int:game_id>')
@login_required
def load_emulator_state(game_id):
    state_file = os.path.join(SAVES_FOLDER, f"{game_id}.state")
    if os.path.exists(state_file):
        return send_from_directory(os.path.abspath(SAVES_FOLDER), f"{game_id}.state")
    return '', 404


@pages_bp.route('/api/emulator/update_time/<int:game_id>', methods=['POST'])
@login_required
def update_time_played(game_id):
    if not os.path.exists(GAMES_FILE):
        return jsonify({'success': False, 'error': 'No games found'}), 404
        
    try:
        data = request.json
        if not isinstance(data, dict):
            return jsonify({'success': False, 'error': 'Payload tidak valid'}), 400
        time_played_increment = data.get('timePlayed', 0)
        last_played = data.get('lastPlayed')
        if (
            isinstance(time_played_increment, bool)
            or not isinstance(time_played_increment, (int, float))
            or not math.isfinite(time_played_increment)
            or time_played_increment < 0
        ):
            return jsonify({'success': False, 'error': 'timePlayed harus berupa angka positif'}), 400
        
        with open(GAMES_FILE, 'r', encoding='utf-8') as f:
            games = json.load(f)
            
        game = next((game for game in games if game.get('id') == game_id), None)
        if game is None:
            return jsonify({'success': False, 'error': 'Game tidak ditemukan'}), 404
        game['timePlayed'] = game.get('timePlayed', 0) + time_played_increment
        game['lastPlayed'] = last_played
                
        with open(GAMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(games, f, ensure_ascii=False, indent=4)
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@pages_bp.route('/streaming', endpoint='streaming_dashboard')
@login_required
def streaming_dashboard():
    return render_template('streaming.html')


@pages_bp.route('/movies-admin', endpoint='movies_admin')
@login_required
def movies_admin():
    return render_template('movies_admin.html')


@pages_bp.route('/watch/<int:movie_id>', endpoint='watch_movie')
@login_required
def watch_movie(movie_id):
    if os.path.exists(MOVIES_FILE):
        with open(MOVIES_FILE, 'r', encoding='utf-8') as f:
            movies = json.load(f)
            movie = next((m for m in movies if m.get('id') == movie_id), None)
            if movie:
                return render_template('watch.html', movie=movie)
    return "Movie not found", 404


@pages_bp.route('/api/movies', methods=['GET', 'POST'])
@login_required
def api_movies():
    if request.method == 'POST':
        data = request.json
        with open(MOVIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return jsonify({'success': True})
    if os.path.exists(MOVIES_FILE):
        with open(MOVIES_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify([])


@pages_bp.route('/api/movies/extract_sub', methods=['POST'])
@login_required
def extract_subtitle():
    data = request.json
    try:
        video_path = get_safe_path(data.get('video_rel_path', '').lstrip('/'))
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    if not os.path.isfile(video_path):
        return jsonify({'success': False, 'error': 'Video tidak ditemukan'}), 404

    # Extract to the same directory with .vtt extension
    base, _ = os.path.splitext(video_path)
    sub_path = f"{base}.vtt"
    
    # Run ffmpeg to extract subtitle (map 0:s:0)
    ffmpeg_exe = os.path.join(current_app.root_path, '..', 'ffmpeg.exe')
    if not os.path.exists(ffmpeg_exe):
        ffmpeg_exe = 'ffmpeg' # fallback to system ffmpeg
        
    try:
        cmd = [ffmpeg_exe, '-i', video_path, '-map', '0:s:0', '-y', sub_path]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(sub_path):
            rel_sub_path = os.path.relpath(sub_path, FM_ROOT).replace('\\', '/')
            return jsonify({'success': True, 'sub_path': rel_sub_path})
        return jsonify({'success': False, 'error': 'Gagal mengekstrak subtitle (mungkin tidak ada subtitle)'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'FFmpeg error: {str(e)}'})

@pages_bp.route('/api/movies/stream')
@login_required
def stream_movie():
    rel_path = request.args.get('path', '').lstrip('/')
    try:
        abs_path = get_safe_path(rel_path)
    except ValueError:
        return "Access denied", 403
    if os.path.isfile(abs_path):
        mime_type = {
            '.vtt': 'text/vtt',
            '.srt': 'application/x-subrip',
            '.mkv': 'video/x-matroska',
        }.get(os.path.splitext(abs_path)[1].lower(), mimetypes.guess_type(abs_path)[0] or 'application/octet-stream')
        return send_file(abs_path, mimetype=mime_type, conditional=True)
    return "Not found", 404


@pages_bp.route('/api/movies/download')
@login_required
def download_movie():
    rel_path = request.args.get('path', '').lstrip('/')
    try:
        abs_path = get_safe_path(rel_path)
    except ValueError:
        return 'Access denied', 403
    if not os.path.isfile(abs_path):
        return 'Not found', 404
    extension = os.path.splitext(abs_path)[1].lower()
    mime_type = {
        '.mkv': 'video/x-matroska',
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
    }.get(extension, mimetypes.guess_type(abs_path)[0] or 'application/octet-stream')
    return send_file(
        abs_path,
        mimetype=mime_type,
        as_attachment=True,
        download_name=os.path.basename(abs_path),
        conditional=True,
    )
