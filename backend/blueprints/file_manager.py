import os
import io
import zipfile
import shutil
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file, render_template, make_response
from ..utils import login_required, get_safe_path
from ..config import FM_ROOT

file_manager_bp = Blueprint('file_manager', __name__)


@file_manager_bp.route('/dashboard')
@file_manager_bp.route('/file-manager')
@login_required
def fm_dashboard():
    response = make_response(render_template('dashboard.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


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


@file_manager_bp.route('/api/fm/create_folder', methods=['POST'])
@login_required
def fm_create_folder():
    data = request.json
    target_dir = get_safe_path(data.get('path', ''))
    new_folder = os.path.basename(data.get('name', 'New_Folder'))
    try:
        os.makedirs(os.path.join(target_dir, new_folder), exist_ok=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@file_manager_bp.route('/api/fm/upload', methods=['POST'])
@login_required
def fm_upload():
    target_dir = get_safe_path(request.form.get('path', ''))
    files = request.files.getlist('files')
    try:
        for file in files:
            if file.filename:
                filename = os.path.basename(file.filename)
                file.save(os.path.join(target_dir, filename))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@file_manager_bp.route('/api/fm/delete', methods=['POST'])
@login_required
def fm_delete():
    data = request.json
    item_path = os.path.join(get_safe_path(data.get('path', '')), data.get('item', ''))
    try:
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@file_manager_bp.route('/api/fm/bulk_delete', methods=['POST'])
@login_required
def fm_bulk_delete():
    data = request.json
    target_dir = get_safe_path(data.get('path', ''))
    for item in data.get('items', []):
        item_path = os.path.join(target_dir, item)
        if os.path.exists(item_path):
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    return jsonify({'success': True})


@file_manager_bp.route('/bulk_delete', methods=['POST'])
def bulk_delete_legacy():
    return fm_bulk_delete()


@file_manager_bp.route('/api/fm/move', methods=['POST'])
@login_required
def fm_move():
    data = request.json
    source_dir = get_safe_path(data.get('path', ''))
    item_name = data.get('item', '')
    dst_path = os.path.join(get_safe_path(data.get('target_folder', '')), item_name)
    try:
        shutil.move(os.path.join(source_dir, item_name), dst_path)
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
    old_path = os.path.join(target_dir, os.path.basename(data.get('old_name', '')))
    new_path = os.path.join(target_dir, os.path.basename(data.get('new_name', '')))
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
    src_path = os.path.join(target_dir, item_name)
    name, ext = os.path.splitext(item_name)
    dst_path = os.path.join(target_dir, f"{name}_Copy{ext}")
    counter = 2
    while os.path.exists(dst_path):
        dst_path = os.path.join(target_dir, f"{name}_Copy{counter}{ext}")
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
    item_path = os.path.join(get_safe_path(rel_path), item_name)
    if os.path.isdir(item_path):
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(item_path):
                for fname in files:
                    fp = os.path.join(root, fname)
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
            item_path = os.path.join(target_dir, item)
            if not os.path.exists(item_path):
                continue
            if os.path.isdir(item_path):
                for root, _, files in os.walk(item_path):
                    for fname in files:
                        fp = os.path.join(root, fname)
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
