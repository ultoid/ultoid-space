import os
from flask import Blueprint, current_app, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from ..config import CREDENTIALS_FILE, DATA_FOLDER
from ..utils import get_client_ip, _is_login_locked, record_failed_login, reset_login_attempts

auth_bp = Blueprint('auth', __name__)


def init_credentials():
    os.makedirs(DATA_FOLDER, exist_ok=True)
    if not os.path.exists(CREDENTIALS_FILE):
        password = os.environ.get('ULTOID_ADMIN_PASSWORD')
        if not password:
            raise RuntimeError('ULTOID_ADMIN_PASSWORD harus diatur sebelum membuat kredensial admin.')
        username = os.environ.get('ULTOID_ADMIN_USERNAME', 'admin')
        password_hash = generate_password_hash(password)
        try:
            with open(CREDENTIALS_FILE, 'x', encoding='utf-8') as f:
                f.write(f"USERNAME={username}\nHASHED_PASSWORD={password_hash}\n")
        except FileExistsError:
            pass


def load_credentials():
    init_credentials()
    creds = {}
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    creds[k] = v
    return creds.get('USERNAME', 'admin'), creds.get('HASHED_PASSWORD', '')


@auth_bp.route('/', endpoint='home')
def home():
    if session.get('logged_in'):
        return redirect(url_for('pages.space'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if session.get('logged_in'):
        return redirect(url_for('pages.space'))
    error = None
    if request.method == 'POST':
        client_ip = get_client_ip()
        if _is_login_locked(client_ip):
            error = 'Terlalu banyak percobaan login gagal. Coba lagi dalam 5 menit.'
            return render_template('login.html', error=error)

        try:
            admin_user, admin_password_hash = load_credentials()
        except (OSError, RuntimeError) as exc:
            current_app.logger.error('Kredensial admin tidak tersedia: %s', exc)
            return render_template(
                'login.html',
                error='Login belum dikonfigurasi. Atur ULTOID_ADMIN_PASSWORD atau siapkan data/credentials.txt.',
            ), 503

        if not admin_password_hash:
            current_app.logger.error('Hash password admin kosong pada file kredensial.')
            return render_template('login.html', error='Konfigurasi kredensial admin tidak valid.'), 503

        input_user = request.form.get('username')
        input_pass = request.form.get('password')

        if input_user == admin_user and input_pass is not None and check_password_hash(admin_password_hash, input_pass):
            reset_login_attempts(client_ip)
            session.pop('ruto_csrf_token', None)
            session['logged_in'] = True
            return redirect(url_for('pages.space'))
        else:
            entry = record_failed_login(client_ip)
            remaining = max(0, 5 - entry['count'])
            if remaining > 0:
                error = f'Username atau Password salah! ({remaining} percobaan tersisa)'
            else:
                error = 'Akun dikunci sementara karena terlalu banyak percobaan gagal.'
    return render_template('login.html', error=error)


@auth_bp.route('/logout', endpoint='logout')
def logout():
    session.pop('logged_in', None)
    session.pop('ruto_csrf_token', None)
    return redirect(url_for('auth.login'))
