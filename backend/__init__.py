import os
from flask import Flask
from .config import ensure_directories, load_or_create_secret_key, UPLOAD_FOLDER, OUTPUT_FOLDER
from .blueprints.auth import auth_bp
from .blueprints.pages import pages_bp
from .blueprints.translate import translate_bp
from .blueprints.file_manager import file_manager_bp
from .blueprints.scraper import scraper_bp
from .blueprints.wallpaper import wallpaper_bp
from .blueprints.socmed import socmed_bp
from .blueprints.qrcode import qrcode_bp
from .blueprints.portfolio import portfolio_bp
from .cron import setup_scheduler


def create_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_folder = os.path.join(base_dir, 'templates')
    static_folder = os.path.join(base_dir, 'static')

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB limit
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

    app.secret_key = os.environ.get('ULTOID_SECRET_KEY') or load_or_create_secret_key()
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    ensure_directories()

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(translate_bp)
    app.register_blueprint(file_manager_bp)
    app.register_blueprint(scraper_bp)
    app.register_blueprint(wallpaper_bp)
    app.register_blueprint(socmed_bp)
    app.register_blueprint(qrcode_bp)
    app.register_blueprint(portfolio_bp)

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://cdn.emulatorjs.org; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://cdn.emulatorjs.org; "
            "font-src 'self' https://fonts.gstatic.com https://fonts.googleapis.com; "
            "img-src 'self' data: https: http: blob:; "
            "connect-src 'self' https: wss: blob:; "
            "worker-src 'self' blob:;"
        )
        return response

    setup_scheduler(app)
    return app
