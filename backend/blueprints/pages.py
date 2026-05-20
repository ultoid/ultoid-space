from flask import Blueprint, render_template, redirect, url_for, jsonify, request, send_from_directory, current_app
from ..utils import login_required
from ..config import NOTES_FILE, TASKS_FILE, OUTPUT_FOLDER, GAMES_FILE
import os
import json

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


@pages_bp.route('/ig-scraper', endpoint='ig_scraper_page')
@login_required
def ig_scraper_page():
    return render_template('ig_scraper.html')


@pages_bp.route('/tt-scraper', endpoint='tt_scraper_page')
@login_required
def tt_scraper_page():
    return render_template('tt_scraper.html')


@pages_bp.route('/fb-scraper', endpoint='fb_scraper_page')
@login_required
def fb_scraper_page():
    return render_template('fb_scraper.html')


@pages_bp.route('/fb-input', endpoint='fb_input_page')
@login_required
def fb_input_page():
    return render_template('fb_input.html')


@pages_bp.route('/socmed-dashboard', endpoint='socmed_dashboard')
@login_required
def socmed_dashboard():
    return render_template('socmed_dashboard.html')


@pages_bp.route('/download_admin/<path:filename>', endpoint='download_admin')
@login_required
def download_admin(filename):
    return send_from_directory(os.path.abspath(OUTPUT_FOLDER), filename, as_attachment=True)


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
