import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from werkzeug.utils import secure_filename
import qrcode
import barcode
from barcode.writer import ImageWriter
from PIL import Image
from ..config import QRCODES_FILE, QRCODES_FOLDER, QRCODES_LOGOS_FOLDER

qrcode_bp = Blueprint('qrcode_bp', __name__)

def load_qrcodes():
    if not os.path.exists(QRCODES_FILE):
        return []
    try:
        with open(QRCODES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_qrcodes(data):
    with open(QRCODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 3:
        hex_code = ''.join([c*2 for c in hex_code])
    try:
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    except:
        return (0, 0, 0)

@qrcode_bp.route('/qrcode')
def qrcode_page():
    return render_template('qrcode.html')

@qrcode_bp.route('/api/qrcode/list', methods=['GET'])
def list_qrcodes():
    # Sort by created_at descending
    qrcodes = load_qrcodes()
    qrcodes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(qrcodes)

@qrcode_bp.route('/api/qrcode/generate', methods=['POST'])
@qrcode_bp.route('/api/qrcode/edit/<item_id>', methods=['POST'])
def generate_qrcode(item_id=None):
    text = request.form.get('text', '').strip()
    item_type = request.form.get('type', 'qrcode')
    color = request.form.get('color', '#000000')
    bg_color = request.form.get('bg_color', '#ffffff')
    
    if not text:
        return jsonify({'error': 'Teks atau link tidak boleh kosong'}), 400

    qrcodes = load_qrcodes()
    
    if item_id:
        item = next((q for q in qrcodes if q['id'] == item_id), None)
        if not item:
            return jsonify({'error': 'Item tidak ditemukan'}), 404
    else:
        item_id = str(uuid.uuid4())
        item = {
            'id': item_id,
            'created_at': datetime.now().isoformat()
        }

    logo_path = item.get('logo_path', None)
    
    # Handle logo upload
    logo_file = request.files.get('logo')
    if logo_file and logo_file.filename != '':
        filename = secure_filename(logo_file.filename)
        unique_filename = f"{item_id}_{filename}"
        logo_save_path = os.path.join(QRCODES_LOGOS_FOLDER, unique_filename)
        logo_file.save(logo_save_path)
        logo_path = os.path.join('static', 'qrcodes', 'logos', unique_filename).replace('\\', '/')
    elif request.form.get('remove_logo') == 'true':
        if logo_path:
            old_logo_full = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), logo_path)
            if os.path.exists(old_logo_full):
                try: os.remove(old_logo_full)
                except: pass
        logo_path = None

    image_filename = f"{item_id}.png"
    image_save_path = os.path.join(QRCODES_FOLDER, image_filename)
    
    try:
        if item_type == 'qrcode':
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H if logo_path else qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(text)
            qr.make(fit=True)
            
            fill_color = hex_to_rgb(color)
            back_color = hex_to_rgb(bg_color)
            
            img = qr.make_image(fill_color=fill_color, back_color=back_color).convert('RGBA')
            
            if logo_path:
                logo_full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), logo_path)
                if os.path.exists(logo_full_path):
                    logo = Image.open(logo_full_path)
                    basewidth = int(img.size[0] / 4)
                    wpercent = (basewidth / float(logo.size[0]))
                    hsize = int((float(logo.size[1]) * float(wpercent)))
                    logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)
                    pos = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)
                    
                    if logo.mode != 'RGBA':
                        logo = logo.convert('RGBA')
                    
                    # Create a white background for logo (to ensure it is visible)
                    logo_bg = Image.new('RGBA', logo.size, back_color + (255,))
                    logo_bg.paste(logo, mask=logo.split()[3])
                    img.paste(logo_bg, pos)

            img.save(image_save_path)
            
        elif item_type == 'barcode':
            # Barcode using Code128
            writer = ImageWriter()
            options = {
                'foreground': color,
                'background': bg_color,
                'write_text': True
            }
            code128 = barcode.get('code128', text, writer=writer)
            code128.save(image_save_path.replace('.png', ''), options=options)
            # barcode.save adds .png automatically
        
        item['type'] = item_type
        item['text'] = text
        item['color'] = color
        item['bg_color'] = bg_color
        item['logo_path'] = logo_path
        item['image_path'] = os.path.join('static', 'qrcodes', image_filename).replace('\\', '/')
        
        if not any(q['id'] == item_id for q in qrcodes):
            qrcodes.append(item)
            
        save_qrcodes(qrcodes)
        return jsonify(item)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@qrcode_bp.route('/api/qrcode/<item_id>', methods=['DELETE'])
def delete_qrcode(item_id):
    qrcodes = load_qrcodes()
    item = next((q for q in qrcodes if q['id'] == item_id), None)
    if not item:
        return jsonify({'error': 'Item tidak ditemukan'}), 404
        
    try:
        # Hapus file gambar utama
        if item.get('image_path'):
            img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), item['image_path'])
            if os.path.exists(img_path):
                os.remove(img_path)
                
        # Hapus logo jika ada
        if item.get('logo_path'):
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), item['logo_path'])
            if os.path.exists(logo_path):
                os.remove(logo_path)
    except Exception as e:
        print(f"Error deleting files: {e}")
        
    qrcodes = [q for q in qrcodes if q['id'] != item_id]
    save_qrcodes(qrcodes)
    return jsonify({'success': True})
