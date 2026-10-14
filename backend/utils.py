import os
import time
from functools import wraps
from flask import request, redirect, url_for, session, jsonify
from .config import FM_ROOT, LOGIN_LOCKOUT_SECONDS, LOGIN_MAX_ATTEMPTS

_login_attempts = {}


def get_client_ip():
    return request.remote_addr or 'unknown'


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
    if entry['count'] >= LOGIN_MAX_ATTEMPTS:
        entry['locked_until'] = time.time() + LOGIN_LOCKOUT_SECONDS
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


def get_safe_path(rel_path='', item=None):
    root = os.path.realpath(FM_ROOT)
    base = os.path.realpath(os.path.join(root, rel_path or ''))
    target = os.path.realpath(os.path.join(base, item or ''))
    try:
        normalized_root = os.path.normcase(root)
        base_common = os.path.commonpath((normalized_root, os.path.normcase(base)))
        target_common = os.path.commonpath((normalized_root, os.path.normcase(target)))
    except ValueError as exc:
        raise ValueError('Path berada di luar direktori File Manager') from exc
    if base_common != normalized_root or target_common != normalized_root:
        raise ValueError('Path berada di luar direktori File Manager')
    if item is not None:
        if (
            not item
            or item in ('.', '..')
            or os.path.basename(item) != item
            or '/' in item
            or '\\' in item
        ):
            raise ValueError('Nama item tidak valid')
        if os.path.normcase(os.path.dirname(target)) != os.path.normcase(base):
            raise ValueError('Path item tidak valid')
    return target
