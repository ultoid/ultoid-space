import os
import secrets
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Folder / file dasar
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'static/file_manager/Translate'
DATA_FOLDER = 'data'
SECRET_KEY_FILE = os.path.join(DATA_FOLDER, '.secret_key')
NOTES_FILE = os.path.join(DATA_FOLDER, 'notes.json')
TASKS_FILE = os.path.join(DATA_FOLDER, 'tasks.json')
PORTFOLIO_FILE = os.path.join(DATA_FOLDER, 'portfolio.json')
CREDENTIALS_FILE = os.path.join(DATA_FOLDER, 'credentials.txt')
FM_ROOT = 'static/file_manager'
NOTES_IMAGES_FOLDER = 'static/notes_images'
GAME_IMAGES_FOLDER = 'static/game_images'
QRCODES_FILE = os.path.join(DATA_FOLDER, 'qrcodes.json')
QRCODES_FOLDER = 'static/qrcodes'
QRCODES_LOGOS_FOLDER = os.path.join(QRCODES_FOLDER, 'logos')
DEFAULT_FOLDERS = [
    'Translate',
    'Download',
    'Wallpaper',
    'Movies'
]

ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

GAMES_FILE = os.path.join(DATA_FOLDER, 'games.json')
SETTINGS_FILE = 'settings.json'
SAVES_FOLDER = os.path.join(DATA_FOLDER, 'saves')
MOVIES_FILE = os.path.join(DATA_FOLDER, 'movies.json')
SHORTLINKS_FILE = os.path.join(DATA_FOLDER, 'shortlinks.json')
SHORTLINK_DOMAIN = 'https://anugerahgmb.com/s/'

RESERVED_ROUTES = {
    'login', 'logout', 'dashboard', 'space', 'api', 'static', 'templates',
    'translate', 'downloader', 'wallpaper', 'qrcode', 'portfolio', 'task', 'notes', 'streaming',
    'emulator', 'shortlink'
}

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300

API_KEY_GEMINI = os.environ.get('GEMINI_API_KEY')
if not API_KEY_GEMINI:
    API_KEY_GEMINI = 'API_KEY_TIDAK_DITEMUKAN'
    print('PERINGATAN: GEMINI_API_KEY belum diset di environment variables!')

client = genai.Client(api_key=API_KEY_GEMINI)


def load_or_create_secret_key():
    os.makedirs(DATA_FOLDER, exist_ok=True)
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, 'r', encoding='utf-8') as f:
            key = f.read().strip()
            if len(key) >= 32:
                return key
    key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, 'w', encoding='utf-8') as f:
        f.write(key)
    return key


def ensure_directories():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(DATA_FOLDER, exist_ok=True)
    os.makedirs(NOTES_IMAGES_FOLDER, exist_ok=True)
    os.makedirs(GAME_IMAGES_FOLDER, exist_ok=True)
    os.makedirs(QRCODES_FOLDER, exist_ok=True)
    os.makedirs(QRCODES_LOGOS_FOLDER, exist_ok=True)
    os.makedirs(SAVES_FOLDER, exist_ok=True)
    for folder in DEFAULT_FOLDERS:
        os.makedirs(os.path.join(FM_ROOT, folder), exist_ok=True)
