import os
import json
from flask import Blueprint, jsonify, request
from ..utils import login_required
from ..config import SETTINGS_FILE, ALLOWED_IMAGE_EXT

wallpaper_bp = Blueprint('wallpaper', __name__)


def get_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'wallpaper': 'mac-default'}


def save_settings(data):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)


@wallpaper_bp.route('/api/wallpaper', methods=['GET', 'POST'])
@login_required
def manage_wallpaper():
    settings = get_settings()
    if request.method == 'POST':
        data = request.json
        settings['wallpaper'] = data.get('wallpaper', 'mac-default')
        save_settings(settings)
        return jsonify({'status': 'success'})
    return jsonify({'wallpaper': settings['wallpaper']})


@wallpaper_bp.route('/api/wallpaper/upload', methods=['POST'])
@login_required
def upload_wallpaper():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'File kosong'}), 400
    filename = os.path.basename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_IMAGE_EXT:
        return jsonify({'error': f"Tipe file '.{ext}' tidak diizinkan. Gunakan: {', '.join(ALLOWED_IMAGE_EXT)}"}), 400
    save_dir = 'static/file_manager/Wallpaper'
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, filename)
    file.save(filepath)
    url = f"/{save_dir}/{filename}"
    return jsonify({'url': url})


@wallpaper_bp.route('/api/wallpaper/list', methods=['GET'])
@login_required
def list_wallpapers():
    save_dir = 'static/file_manager/Wallpaper'
    os.makedirs(save_dir, exist_ok=True)
    files = os.listdir(save_dir)
    images = [f"/{save_dir}/{f}" for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))]
    images.reverse()
    return jsonify(images)
