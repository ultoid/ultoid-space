import os
import json
import uuid
from flask import Blueprint, abort, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from ..utils import login_required
from ..config import PORTFOLIO_FILE

portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/portfolio')

DEFAULT_PORTFOLIO = {
    "first_name": "Ananto",
    "last_name": "Eko Pambudi",
    "title": "Digital Marketing + Branding",
    "about": "I am a Design Enthusiast who is passionate about Branding, Marketing, Advertising, Website Development, and SEO & Content Writing. I personally like to learn, enjoy developing skills, and enthusiastic about new challenges. My main basic skill is Design which I then develop towards Branding.",
    "email": "anantoeko48@gmail.com",
    "location": "Karanganyar, Jawa Tengah",
    "availability": "Available for work",
    "years_experience": "4",
    "phone": "+62 8993 8551 80",
    "profile_image": "",
    "github": "",
    "linkedin": "https://linkedin.com/in/ananto-e-140040131",
    "instagram": "https://instagram.com/anantoeko_",
    "twitter": "",
    "stats": [
        {"number": "4", "label": "Years Experiences"},
        {"number": "16", "label": "Customers"},
        {"number": "57", "label": "Projects"},
        {"number": "273", "label": "Design Items"}
    ],
    "services": [
        {"number": "01", "title": "Branding & Marketing", "description": "Developing strategies and brand identity to communicate effectively with target markets."},
        {"number": "02", "title": "Graphic Design", "description": "Creating visual content including Instagram feeds, packaging design, and vector art."},
        {"number": "03", "title": "Website Development", "description": "Building front-end web experiences using HTML, CSS, and JavaScript."},
        {"number": "04", "title": "SEO & Content Writing", "description": "Writing articles and optimizing content for search engines to gain engagement and awareness."}
    ],
    "experience": [
        {
            "role": "Koordinator Marketing Communication",
            "company": "PT Rosalia Indah Transport",
            "year": "2024 - Present",
            "description": ""
        },
        {
            "role": "Staff Marketing Communication",
            "company": "PT Rosalia Indah Transport",
            "year": "2023 - 2024",
            "description": ""
        },
        {
            "role": "Supervisor Digital Marketing",
            "company": "Semesta Group (Holding PT Zona Karya Mendunia)",
            "year": "2022 - 2023",
            "description": ""
        },
        {
            "role": "Staff Marketing Comm. & Content Creator",
            "company": "PT Zona Karya Mendunia",
            "year": "2021 - 2022",
            "description": ""
        }
    ],
    "education": [
        {
            "role": "D3 - Agribisnis, Fakultas Pertanian",
            "company": "Universitas Sebelas Maret",
            "year": "2017 - 2020",
            "description": ""
        },
        {
            "role": "Jurusan MIPA",
            "company": "SMA Negeri 1 Karanganyar",
            "year": "2014 - 2017",
            "description": ""
        },
        {
            "role": "SMP",
            "company": "SMP Negeri 3 Karanganyar",
            "year": "2011 - 2014",
            "description": ""
        },
        {
            "role": "SD",
            "company": "SD Negeri 1 Bangsri",
            "year": "2005 - 2011",
            "description": ""
        }
    ],
    "skills": [
        {"name": "Corel Draw", "percentage": "95", "icon": "Corel"},
        {"name": "Adobe Photoshop", "percentage": "85", "icon": "Ps"},
        {"name": "Adobe Premiere Pro", "percentage": "80", "icon": "Pr"},
        {"name": "HTML, CSS, JS", "percentage": "75", "icon": "Web"},
        {"name": "Copywriting", "percentage": "90", "icon": "Pen"},
        {"name": "Content Planning", "percentage": "88", "icon": "Plan"}
    ],
    "projects": [
        {
            "title": "Singapore Int. Invention Show 2020",
            "description": "Carakan: Digital Board Game",
            "link": "#",
            "image": "",
            "tags": ["Achievement"]
        },
        {
            "title": "World Young Inventor Exhibition (WYIE)",
            "description": "Detergen Alami dari Daun Patikan Cina dan Daun Sirsak, ITEX Malaysia 2019",
            "link": "#",
            "image": "",
            "tags": ["Achievement"]
        },
        {
            "title": "Program Hibah Bina Desa 2018",
            "description": "Pengembangan Potensi Lokal Berbasis Industri Kreatif Dengan Digital Marketing",
            "link": "#",
            "image": "",
            "tags": ["Digital Marketing"]
        }
    ],
    "achievements": [
        {
            "title": "Singapore Int. Invention Show 2020",
            "description": "Carakan: Digital Board Game",
            "link": "#",
            "image": "",
            "tags": ["Achievement"]
        },
        {
            "title": "World Young Inventor Exhibition (WYIE)",
            "description": "Detergen Alami dari Daun Patikan Cina dan Daun Sirsak, ITEX Malaysia 2019",
            "link": "#",
            "image": "",
            "tags": ["Achievement"]
        }
    ]
}

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return DEFAULT_PORTFOLIO
    return DEFAULT_PORTFOLIO

def save_portfolio(data):
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@portfolio_bp.route('/', endpoint='showcase')
def showcase():
    data = load_portfolio()
    return render_template('portfolio.html', portfolio=data)

@portfolio_bp.route('/edit', endpoint='edit')
@login_required
def edit():
    data = load_portfolio()
    return render_template('portfolio_edit.html', portfolio=data)

@portfolio_bp.route('/api/data', methods=['GET', 'POST'])
@login_required
def api_data():
    if request.method == 'POST':
        data = request.json
        save_portfolio(data)
        return jsonify({'success': True})
    return jsonify(load_portfolio())

@portfolio_bp.route('/api/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    if file:
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
        new_filename = f"media_{uuid.uuid4().hex[:8]}.{ext}"
        save_dir = os.path.join('static', 'portfolio_images')
        os.makedirs(save_dir, exist_ok=True)
        file.save(os.path.join(save_dir, new_filename))
        url = f"/static/portfolio_images/{new_filename}"
        return jsonify({'success': True, 'url': url})

@portfolio_bp.route('/<path:filename>')
def download_portfolio_file(filename):
    if filename != 'Ananto_Portfolio.pdf':
        abort(404)
    portfolio_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'portfolio')
    return send_from_directory(portfolio_dir, filename)
