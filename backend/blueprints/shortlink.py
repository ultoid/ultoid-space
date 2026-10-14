import os
import json
import random
import string
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, abort, url_for
from backend.utils import login_required
from backend.config import SHORTLINKS_FILE, RESERVED_ROUTES

shortlink_bp = Blueprint('shortlink', __name__)

def load_shortlinks():
    if not os.path.exists(SHORTLINKS_FILE):
        return {}
    with open(SHORTLINKS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError('Database shortlink harus berupa objek JSON.')
    return data

def save_shortlinks(data):
    os.makedirs(os.path.dirname(SHORTLINKS_FILE), exist_ok=True)
    with open(SHORTLINKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def generate_random_id(length=5):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@shortlink_bp.route('/shortlink', methods=['GET'])
@login_required
def dashboard():
    return render_template('shortlink.html')

@shortlink_bp.route('/api/shortlink/list', methods=['GET'])
@login_required
def api_list():
    data = load_shortlinks()
    # Sort by created_at descending
    links = sorted(data.values(), key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(links)

@shortlink_bp.route('/api/shortlink/create', methods=['POST'])
@login_required
def api_create():
    data = load_shortlinks()
    
    original_url = request.form.get('url', '').strip()
    custom_id = request.form.get('custom_id', '').strip()
    description = request.form.get('description', '').strip()

    if not original_url:
        return jsonify({'error': 'URL tujuan tidak boleh kosong'}), 400
        
    if not original_url.startswith('http://') and not original_url.startswith('https://'):
        original_url = 'https://' + original_url

    if custom_id:
        if custom_id in data:
            return jsonify({'error': 'Custom ID sudah digunakan'}), 400
        if custom_id.lower() in RESERVED_ROUTES:
            return jsonify({'error': 'Custom ID ini dilarang oleh sistem'}), 400
        if any(c not in string.ascii_letters + string.digits + '-' + '_' for c in custom_id):
            return jsonify({'error': 'Custom ID hanya boleh berisi huruf, angka, strip (-), dan underscore (_)'}), 400
        short_id = custom_id
    else:
        while True:
            short_id = generate_random_id()
            if short_id not in data and short_id.lower() not in RESERVED_ROUTES:
                break

    data[short_id] = {
        'id': short_id,
        'url': original_url,
        'description': description,
        'created_at': datetime.now().isoformat(),
        'clicks': 0
    }
    save_shortlinks(data)
    return jsonify(data[short_id])

@shortlink_bp.route('/api/shortlink/edit/<old_id>', methods=['POST'])
@login_required
def api_edit(old_id):
    data = load_shortlinks()
    if old_id not in data:
        return jsonify({'error': 'Shortlink tidak ditemukan'}), 404

    original_url = request.form.get('url', '').strip()
    new_id = request.form.get('custom_id', '').strip()
    description = request.form.get('description', '').strip()

    if not original_url:
        return jsonify({'error': 'URL tujuan tidak boleh kosong'}), 400

    if not original_url.startswith('http://') and not original_url.startswith('https://'):
        original_url = 'https://' + original_url

    # Validasi new_id
    if new_id and new_id != old_id:
        if new_id in data:
            return jsonify({'error': 'Custom ID sudah digunakan'}), 400
        if new_id.lower() in RESERVED_ROUTES:
            return jsonify({'error': 'Custom ID ini dilarang oleh sistem'}), 400
        if any(c not in string.ascii_letters + string.digits + '-' + '_' for c in new_id):
            return jsonify({'error': 'Custom ID hanya boleh berisi huruf, angka, strip (-), dan underscore (_)'}), 400

    item = data.pop(old_id)
    final_id = new_id if new_id else old_id
    
    item['id'] = final_id
    item['url'] = original_url
    item['description'] = description

    data[final_id] = item
    save_shortlinks(data)
    return jsonify(item)

@shortlink_bp.route('/api/shortlink/<short_id>', methods=['DELETE'])
@login_required
def api_delete(short_id):
    data = load_shortlinks()
    if short_id in data:
        del data[short_id]
        save_shortlinks(data)
        return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

# Route catch-all for redirection
@shortlink_bp.route('/s/<short_id>', methods=['GET'])
def redirect_shortlink(short_id):
    # This route has lowest priority due to being dynamic. 
    # Flask matches explicit routes (like /dashboard) before dynamic ones.
    data = load_shortlinks()
    if short_id in data:
        # Update click count
        data[short_id]['clicks'] = data[short_id].get('clicks', 0) + 1
        save_shortlinks(data)
        return redirect(data[short_id]['url'])
    
    # If it's not a shortlink, it might be an invalid route.
    # By returning 404, we let Flask handle standard error pages if needed,
    # or we can redirect to a fallback.
    abort(404)
