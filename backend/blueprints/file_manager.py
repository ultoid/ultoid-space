import os
import io
import json
import uuid
import zipfile
import shutil
import re
from datetime import datetime
from flask import Blueprint, abort, jsonify, request, send_file, render_template, make_response
from ..utils import login_required, get_safe_path
from ..config import FM_ROOT

file_manager_bp = Blueprint('file_manager', __name__)
TRASH_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(FM_ROOT)),
    '..',
    'data',
    'file_manager_trash',
))
TRASH_ID_RE = re.compile(r'^[0-9a-f]{32}$')


@file_manager_bp.errorhandler(ValueError)
def handle_invalid_path(error):
    return jsonify({'success': False, 'error': str(error)}), 400


def _trash_entry_path(item_id):
    if not isinstance(item_id, str) or not TRASH_ID_RE.fullmatch(item_id):
        raise ValueError('Item Sampah tidak valid')
    return os.path.join(TRASH_ROOT, item_id)


def _trash_item(item_path):
    trash_id = uuid.uuid4().hex
    entry_path = _trash_entry_path(trash_id)
    payload_path = os.path.join(entry_path, 'payload')
    metadata = {
        'id': trash_id,
        'name': os.path.basename(item_path),
        'original_path': os.path.relpath(item_path, os.path.realpath(FM_ROOT)).replace(os.sep, '/'),
        'type': 'folder' if os.path.isdir(item_path) else 'file',
        'trashed_at': datetime.now().isoformat(timespec='seconds'),
    }
    os.makedirs(entry_path)
    try:
        shutil.move(item_path, payload_path)
        metadata_path = os.path.join(entry_path, 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as metadata_file:
            json.dump(metadata, metadata_file, ensure_ascii=False)
    except Exception:
        if os.path.exists(payload_path) and not os.path.exists(item_path):
            os.makedirs(os.path.dirname(item_path), exist_ok=True)
            shutil.move(payload_path, item_path)
        shutil.rmtree(entry_path)
        raise
    return metadata


def _get_trash_metadata(item_id):
    entry_path = _trash_entry_path(item_id)
    metadata_path = os.path.join(entry_path, 'metadata.json')
    payload_path = os.path.join(entry_path, 'payload')
    if not os.path.isfile(metadata_path) or not os.path.lexists(payload_path):
        raise FileNotFoundError('Item Sampah tidak ditemukan')
    with open(metadata_path, encoding='utf-8') as metadata_file:
        metadata = json.load(metadata_file)
    if not isinstance(metadata, dict) or metadata.get('id') != item_id:
        raise ValueError('Metadata Sampah tidak valid')
    return entry_path, payload_path, metadata


def _render_dashboard():
    response = make_response(render_template('dashboard.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@file_manager_bp.route('/dashboard')
@file_manager_bp.route('/file-manager')
@login_required
def fm_dashboard():
    return _render_dashboard()


@file_manager_bp.route('/file-manager/<path:folder_path>')
@login_required
def fm_dashboard_folder(folder_path):
    target_dir = get_safe_path(folder_path)
    if not os.path.isdir(target_dir):
        abort(404)
    return _render_dashboard()


@file_manager_bp.route('/api/fm/storage')
@login_required
def fm_storage():
    total, used, free = shutil.disk_usage('/')
    gb = 1024 ** 3
    pct = round(used / total * 100, 1)
    return jsonify({
        'total_gb': round(total / gb, 1),
        'used_gb': round(used / gb, 1),
        'free_gb': round(free / gb, 1),
        'percent_used': pct
    })


@file_manager_bp.route('/api/fm/list')
@login_required
def fm_list():
    rel_path = request.args.get('path', '')
    target_dir = get_safe_path(rel_path)
    if not os.path.exists(target_dir):
        return jsonify({'folders': [], 'files': []})
    folders, files = [], []
    for item in os.listdir(target_dir):
        item_path = os.path.join(target_dir, item)
        mtime = os.path.getmtime(item_path)
        date_str = datetime.fromtimestamp(mtime).strftime('%d %b %Y')
        if os.path.isdir(item_path):
            folders.append({'name': item, 'date': date_str})
        else:
            size_bytes = os.path.getsize(item_path)
            size_str = f"{size_bytes/1024**2:.1f} MB" if size_bytes >= 1024**2 else f"{size_bytes/1024:.0f} KB"
            rel = (rel_path + '/' + item).lstrip('/') if rel_path else item
            files.append({'name': item, 'size': size_str, 'date': date_str, 'rel_path': rel})
    folders.sort(key=lambda x: x['name'].lower())
    files.sort(key=lambda x: x['name'].lower())
    return jsonify({'folders': folders, 'files': files})


@file_manager_bp.route('/api/fm/recent')
@login_required
def fm_recent():
    all_files = []
    for root, dirs, filenames in os.walk(FM_ROOT):
        for fname in filenames:
            fp = os.path.join(root, fname)
            rel = os.path.relpath(fp, FM_ROOT)
            mtime = os.path.getmtime(fp)
            size_bytes = os.path.getsize(fp)
            size_str = f"{size_bytes/1024**2:.1f} MB" if size_bytes >= 1024**2 else f"{size_bytes/1024:.0f} KB"
            all_files.append({
                'name': fname,
                'size': size_str,
                'date': datetime.fromtimestamp(mtime).strftime('%d %b %Y'),
                'rel_path': rel,
                'mtime': mtime
            })
    all_files.sort(key=lambda x: x['mtime'], reverse=True)
    return jsonify({'files': all_files[:30]})


@file_manager_bp.route('/api/fm/trash')
@login_required
def fm_trash_list():
    entries = []
    if not os.path.isdir(TRASH_ROOT):
        return jsonify({'items': entries})
    for item_id in os.listdir(TRASH_ROOT):
        if not TRASH_ID_RE.fullmatch(item_id):
            continue
        try:
            _, _, metadata = _get_trash_metadata(item_id)
        except FileNotFoundError:
            continue
        item_path = _trash_entry_path(item_id)
        payload_path = os.path.join(item_path, 'payload')
        size = 0
        if os.path.isfile(payload_path):
            size = os.path.getsize(payload_path)
        elif os.path.isdir(payload_path):
            for root, _, files in os.walk(payload_path):
                size += sum(os.path.getsize(os.path.join(root, name)) for name in files)
        entries.append({
            **metadata,
            'size': f"{size / 1024**2:.1f} MB" if size >= 1024**2 else f"{size / 1024:.0f} KB",
        })
    entries.sort(key=lambda item: item.get('trashed_at', ''), reverse=True)
    return jsonify({'items': entries})


@file_manager_bp.route('/api/fm/trash', methods=['POST'])
@login_required
def fm_trash_items():
    data = request.get_json(silent=True) or {}
    target_dir = get_safe_path(data.get('path', ''))
    items = data.get('items', [])
    if not isinstance(items, list) or not items:
        return jsonify({'success': False, 'error': 'Pilih item yang akan dipindahkan ke Sampah.'}), 400
    moved = []
    for name in items:
        item_path = get_safe_path(target_dir, name)
        if not os.path.lexists(item_path):
            return jsonify({'success': False, 'error': f'Item tidak ditemukan: {name}'}), 404
        moved.append(_trash_item(item_path))
    return jsonify({'success': True, 'items': moved})


@file_manager_bp.route('/api/fm/trash/restore', methods=['POST'])
@login_required
def fm_trash_restore():
    data = request.get_json(silent=True) or {}
    item_ids = data.get('items', [])
    if not isinstance(item_ids, list) or not item_ids:
        return jsonify({'success': False, 'error': 'Pilih item Sampah yang akan dipulihkan.'}), 400
    restored = []
    for item_id in item_ids:
        entry_path, payload_path, metadata = _get_trash_metadata(item_id)
        original_path = metadata.get('original_path')
        target_path = get_safe_path(original_path)
        if os.path.lexists(target_path):
            return jsonify({
                'success': False,
                'error': f"Lokasi asal sudah berisi item bernama '{metadata.get('name', '')}'. Ganti namanya atau hapus item tersebut sebelum memulihkan.",
            }), 409
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.move(payload_path, target_path)
        shutil.rmtree(entry_path)
        restored.append(item_id)
    return jsonify({'success': True, 'items': restored})


@file_manager_bp.route('/api/fm/trash/delete', methods=['POST'])
@login_required
def fm_trash_delete():
    data = request.get_json(silent=True) or {}
    item_ids = data.get('items', [])
    if not isinstance(item_ids, list) or not item_ids:
        return jsonify({'success': False, 'error': 'Pilih item Sampah yang akan dihapus permanen.'}), 400
    for item_id in item_ids:
        entry_path = _trash_entry_path(item_id)
        if not os.path.isdir(entry_path):
            return jsonify({'success': False, 'error': 'Item Sampah tidak ditemukan.'}), 404
        shutil.rmtree(entry_path)
    return jsonify({'success': True})


@file_manager_bp.route('/api/fm/trash/empty', methods=['POST'])
@login_required
def fm_trash_empty():
    if os.path.isdir(TRASH_ROOT):
        for item_id in os.listdir(TRASH_ROOT):
            if TRASH_ID_RE.fullmatch(item_id):
                shutil.rmtree(_trash_entry_path(item_id))
    return jsonify({'success': True})


@file_manager_bp.route('/api/fm/create_folder', methods=['POST'])
@login_required
def fm_create_folder():
    data = request.json
    new_folder = os.path.basename(data.get('name', 'New_Folder'))
    target_path = get_safe_path(data.get('path', ''), new_folder)
    try:
        os.makedirs(target_path, exist_ok=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@file_manager_bp.route('/api/fm/upload', methods=['POST'])
@login_required
def fm_upload():
    rel_path = request.form.get('path', '')
    files = request.files.getlist('files')
    try:
        for file in files:
            if file.filename:
                filename = os.path.basename(file.filename)
                file.save(get_safe_path(rel_path, filename))
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@file_manager_bp.route('/api/fm/delete', methods=['POST'])
@login_required
def fm_delete():
    data = request.json
    item_path = get_safe_path(data.get('path', ''), data.get('item', ''))
    try:
        if not os.path.lexists(item_path):
            return jsonify({'success': False, 'error': 'Item tidak ditemukan.'}), 404
        return jsonify({'success': True, 'item': _trash_item(item_path)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@file_manager_bp.route('/api/fm/bulk_delete', methods=['POST'])
@login_required
def fm_bulk_delete():
    data = request.json
    target_dir = get_safe_path(data.get('path', ''))
    items = data.get('items', [])
    if not isinstance(items, list) or not items:
        return jsonify({'success': False, 'error': 'Pilih item yang akan dipindahkan ke Sampah.'}), 400
    moved = []
    for name in items:
        item_path = get_safe_path(target_dir, name)
        if not os.path.lexists(item_path):
            return jsonify({'success': False, 'error': f'Item tidak ditemukan: {name}'}), 404
        moved.append(_trash_item(item_path))
    return jsonify({'success': True, 'items': moved})


@file_manager_bp.route('/bulk_delete', methods=['POST'])
def bulk_delete_legacy():
    return fm_bulk_delete()


@file_manager_bp.route('/api/fm/move', methods=['POST'])
@login_required
def fm_move():
    data = request.json
    item_name = data.get('item', '')
    source_path = get_safe_path(data.get('path', ''), item_name)
    dst_path = get_safe_path(data.get('target_folder', ''), item_name)
    try:
        shutil.move(source_path, dst_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@file_manager_bp.route('/api/fm/rename', methods=['POST'])
@login_required
def fm_rename():
    data = request.json
    target_dir = get_safe_path(data.get('path', ''))
    if not data.get('old_name', ''):
        return jsonify({'success': False, 'error': 'Item tidak valid'})
    old_path = get_safe_path(target_dir, data.get('old_name', ''))
    new_path = get_safe_path(target_dir, data.get('new_name', ''))
    try:
        os.rename(old_path, new_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@file_manager_bp.route('/api/fm/duplicate', methods=['POST'])
@login_required
def fm_duplicate():
    data = request.json
    target_dir = get_safe_path(data.get('path', ''))
    item_name = data.get('item', '')
    if not item_name:
        return jsonify({'success': False, 'error': 'Item tidak valid'})
    src_path = get_safe_path(target_dir, item_name)
    name, ext = os.path.splitext(item_name)
    dst_name = f"{name}_Copy{ext}"
    dst_path = get_safe_path(target_dir, dst_name)
    counter = 2
    while os.path.exists(dst_path):
        dst_name = f"{name}_Copy{counter}{ext}"
        dst_path = get_safe_path(target_dir, dst_name)
        counter += 1
    try:
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@file_manager_bp.route('/api/fm/download')
@login_required
def fm_download():
    rel_path = request.args.get('path', '')
    item_name = request.args.get('item', '')
    item_path = get_safe_path(rel_path, item_name)
    if os.path.isdir(item_path):
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(item_path):
                dirs[:] = [directory for directory in dirs if not os.path.islink(os.path.join(root, directory))]
                for fname in files:
                    fp = os.path.join(root, fname)
                    if os.path.islink(fp):
                        continue
                    arcname = os.path.relpath(fp, item_path)
                    zf.write(fp, arcname)
        mem.seek(0)
        return send_file(mem, download_name=f"{item_name}.zip", as_attachment=True)
    return send_file(item_path, as_attachment=True)


@file_manager_bp.route('/api/fm/bulk_download')
@login_required
def fm_bulk_download():
    rel_path = request.args.get('path', '')
    items = request.args.get('items', '').split('|')
    target_dir = get_safe_path(rel_path)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            item_path = get_safe_path(target_dir, item)
            if not os.path.exists(item_path):
                continue
            if os.path.isdir(item_path):
                for root, dirs, files in os.walk(item_path):
                    dirs[:] = [directory for directory in dirs if not os.path.islink(os.path.join(root, directory))]
                    for fname in files:
                        fp = os.path.join(root, fname)
                        if os.path.islink(fp):
                            continue
                        arcname = os.path.join(item, os.path.relpath(fp, item_path))
                        zf.write(fp, arcname)
            else:
                zf.write(item_path, item)
    mem.seek(0)
    return send_file(mem, download_name='Ultoid_Export.zip', as_attachment=True)


@file_manager_bp.route('/api/fm/stream')
@login_required
def fm_stream():
    rel_path = request.args.get('path', '')
    target_path = get_safe_path(rel_path)
    if os.path.isfile(target_path):
        return send_file(target_path)
    return 'Not Found', 404
