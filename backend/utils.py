import os
import time
from functools import wraps
from datetime import datetime
from flask import request, redirect, url_for, session, jsonify
from .config import FM_ROOT

_login_attempts = {}


def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()


def _is_login_locked(ip):
    entry = _login_attempts.get(ip)
    if not entry:
        return False
    if entry.get('locked_until') and time.time() < entry['locked_until']:
        return True
    if entry.get('locked_until') and time.time() >= entry['locked_until']:
        _login_attempts.pop(ip, None)
    return False


def record_failed_login(ip):
    entry = _login_attempts.setdefault(ip, {'count': 0, 'locked_until': None})
    entry['count'] += 1
    return entry


def reset_login_attempts(ip):
    _login_attempts.pop(ip, None)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def get_safe_path(rel_path):
    if not rel_path:
        return os.path.abspath(FM_ROOT)
    target = os.path.abspath(os.path.join(FM_ROOT, rel_path))
    if not target.startswith(os.path.abspath(FM_ROOT)):
        return os.path.abspath(FM_ROOT)
    return target
