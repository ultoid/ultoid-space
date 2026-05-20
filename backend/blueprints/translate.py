import os
import time
import io
import zipfile
import markdown
import requests
from flask import Blueprint, jsonify, request, send_file, Response, current_app
from docx import Document
import fitz
from langdetect import detect
from ..config import OUTPUT_FOLDER, client, API_KEY_GEMINI
from ..utils import login_required

translate_bp = Blueprint('translate', __name__)


@translate_bp.route('/analyze_pdf', methods=['POST'])
@login_required
def analyze_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file'}), 400
    file = request.files['file']
    filename = file.filename
    if not filename:
        return jsonify({'error': 'Tidak ada file'}), 400
    filename = os.path.basename(filename)
    temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_' + filename)
    file.save(temp_path)
    try:
        doc = fitz.open(temp_path)
        jml_halaman = len(doc)
        text_sample = ''
        for i in range(min(20, jml_halaman)):
            teks_halaman = doc[i].get_text().strip()
            if teks_halaman:
                text_sample += teks_halaman + ' '
            if len(text_sample) > 50:
                break
        doc.close()
        os.remove(temp_path)
        lang_code = 'unknown'
        if len(text_sample) > 10:
            try:
                lang_code = detect(text_sample)
            except Exception:
                pass
        lang_map = {
            'id': '🇮🇩 Indonesia',
            'en': '🇬🇧 Inggris',
            'ja': '🇯🇵 Jepang',
            'ko': '🇰🇷 Korea',
            'zh-cn': '🇨🇳 Mandarin',
            'zh-tw': '🇨🇳 Mandarin'
        }
        if lang_code == 'unknown':
            bahasa_terdeteksi = '✨ Auto Deteksi AI'
        else:
            bahasa_terdeteksi = lang_map.get(lang_code, f'✨ Auto ({lang_code})')
        return jsonify({'pages': jml_halaman, 'language': bahasa_terdeteksi})
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500


@translate_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'File kosong'}), 400
    filename = os.path.basename(file.filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    return jsonify({'filename': filename})


@translate_bp.route('/stream-translate/<filename>')
@login_required
def stream_translate(filename):
    def generate():
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        nama_proyek = filename.replace('.pdf', '')
        folder_md = os.path.join(OUTPUT_FOLDER, f"{nama_proyek}_md")
        folder_terjemahan = os.path.join(OUTPUT_FOLDER, f"{nama_proyek}_indo")
        os.makedirs(folder_md, exist_ok=True)
        os.makedirs(folder_terjemahan, exist_ok=True)

        yield f"data: 📚 Memulai ekstraksi PDF: {filename}...\n\n"

        try:
            doc = fitz.open(file_path)
            full_text = ''
            for i in range(len(doc)):
                full_text += doc[i].get_text() + '\n\n'
            doc.close()
        except Exception as e:
            yield f"data: ❌ Gagal mengekstrak PDF. Error: {str(e)}\n\n"
            return

        if not full_text.strip():
            yield 'data: ❌ Error: PDF kosong atau berbentuk scan gambar (tidak terbaca).\n\n'
            return

        baris_teks = full_text.split('\n')
        part_count = 1
        chunk_sekarang = ''
        for baris in baris_teks:
            if len(chunk_sekarang) + len(baris) < 15000:
                chunk_sekarang += baris + '\n'
            else:
                if chunk_sekarang.strip():
                    nama_file = f"{nama_proyek}_{part_count:03d}_Part.md"
                    with open(os.path.join(folder_md, nama_file), 'w', encoding='utf-8') as f:
                        f.write(chunk_sekarang.strip())
                    yield f"data: ✅ Part {part_count} tersimpan.\n\n"
                    part_count += 1
                chunk_sekarang = baris + '\n'

        if chunk_sekarang.strip():
            nama_file = f"{nama_proyek}_{part_count:03d}_Part.md"
            with open(os.path.join(folder_md, nama_file), 'w', encoding='utf-8') as f:
                f.write(chunk_sekarang.strip())
            yield f"data: ✅ Part {part_count} (Sisa akhir) tersimpan.\n\n"

        yield 'data: 🎉 Fase 1 Selesai. Memulai Fase 2...\n\n'

        files_md = sorted([f for f in os.listdir(folder_md) if f.endswith('.md')])
        total_files = len(files_md)
        system_prompt = (
            'Terjemahkan teks berikut ke dalam bahasa Indonesia dengan gaya bahasa yang natural, mengalir, dan mudah dipahami '
            '(seperti gaya penerjemah novel). Pertahankan format paragrafnya. Hanya berikan hasil terjemahannya saja tanpa penjelasan tambahan.'
        )

        for i, md_file in enumerate(files_md, 1):
            out_path = os.path.join(folder_terjemahan, f"INDO_{md_file}")
            if os.path.exists(out_path):
                yield f"data: ⏩ Skip [{i}/{total_files}]: {md_file} (Sudah diterjemahkan)\n\n"
                continue

            yield f"data: ⏳ [{i}/{total_files}] Memproses terjemahan...\n\n"
            with open(os.path.join(folder_md, md_file), 'r', encoding='utf-8') as f:
                isi_teks = f.read()

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model='gemma-4-26b-a4b-it',
                        contents=f"{system_prompt}\n\nTEKS ASLI:\n{isi_teks}"
                    )
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(response.text.strip())
                    yield f"data: ✅ Selesai [{i}/{total_files}]\n\n"
                    time.sleep(2)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        yield f"data: ⚠️ API Google sibuk/Error 500. Mencoba ulang ({attempt+1}/{max_retries})...\n\n"
                        time.sleep(4)
                    else:
                        yield f"data: ❌ Gagal total di part {i} setelah 3x percobaan: {str(e)}\n\n"
                        return

        yield 'data: 🔄 Menyatukan dokumen akhir...\n\n'

        daftar_indo = sorted([f for f in os.listdir(folder_terjemahan) if 'INDO_' in f])
        md_gabungan = ''
        for nama_file in daftar_indo:
            with open(os.path.join(folder_terjemahan, nama_file), 'r', encoding='utf-8') as f_in:
                md_gabungan += f_in.read() + '\n\n'

        file_md = f"{nama_proyek}_Ultoid.md"
        with open(os.path.join(OUTPUT_FOLDER, file_md), 'w', encoding='utf-8') as f:
            f.write(md_gabungan)

        file_txt = f"{nama_proyek}_Ultoid.txt"
        with open(os.path.join(OUTPUT_FOLDER, file_txt), 'w', encoding='utf-8') as f:
            f.write(md_gabungan.replace('#', '').replace('*', ''))

        html_body = markdown.markdown(md_gabungan)
        html_final = (
            "<!DOCTYPE html><html lang='id'><head><meta charset='utf-8'>"
            "<style>body { font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; color: black; max-width: 800px; margin: 0 auto; padding: 20px; } p { margin-bottom: 1.2em; text-indent: 0; }</style></head><body>"
            f"{html_body}</body></html>"
        )
        file_html = f"{nama_proyek}_Ultoid.html"
        with open(os.path.join(OUTPUT_FOLDER, file_html), 'w', encoding='utf-8') as f:
            f.write(html_final)

        try:
            doc_word = Document()
            for baris in md_gabungan.split('\n'):
                if baris.strip():
                    doc_word.add_paragraph(baris.replace('#', '').replace('*', ''))
            file_docx = f"{nama_proyek}_Ultoid.docx"
            doc_word.save(os.path.join(OUTPUT_FOLDER, file_docx))
        except Exception as e:
            yield f"data: ❌ Gagal membuat DOCX: {str(e)}\n\n"

        yield f"data: DONE|{nama_proyek}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@translate_bp.route('/get_preview/<proyek>')
@login_required
def get_preview(proyek):
    html_path = os.path.join(OUTPUT_FOLDER, f"{proyek}_Ultoid.html")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            konten = f.read()
        return jsonify({'html': konten[:3000] + '...<br><br><b>(Preview Dibatasi)</b>'})
    except Exception:
        return jsonify({'html': '<p>Gagal memuat preview.</p>'})


@translate_bp.route('/download_pack/<proyek>')
@login_required
def download_pack(proyek):
    formats = request.args.get('formats', '').split(',')
    files_to_send = []
    for fmt in formats:
        if fmt in ['html', 'md', 'txt', 'docx']:
            filename = f"{proyek}_Ultoid.{fmt}"
            path = os.path.join(OUTPUT_FOLDER, filename)
            if os.path.exists(path):
                files_to_send.append((filename, path))
    if len(files_to_send) == 1:
        return send_file(files_to_send[0][1], as_attachment=True)
    if files_to_send:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename, path in files_to_send:
                zf.write(path, filename)
        memory_file.seek(0)
        return send_file(memory_file, download_name=f"{proyek}_Ultoid_Pack.zip", as_attachment=True)
    return 'File tidak ditemukan', 404


@translate_bp.route('/api/generate-greeting')
@login_required
def generate_greeting():
    task_count = request.args.get('tasks', 0, type=int)
    try:
        prompt = (
            f"Berperanlah sebagai 'Uruto Sensei', asisten AI bergaya Anime / Medieval Fantasy. Sapa 'Master' dalam bahasa Indonesia dan beritahu dia bahwa ada {task_count} quest/tugas hari ini. Buatlah maksimal 2 kalimat pendek yang keren, epik, atau kawaii. Jangan pakai hashtag." if task_count > 0 else
            "Berperanlah sebagai 'Uruto Sensei', asisten AI bergaya Anime / Medieval Fantasy. Sapa 'Master' dalam bahasa Indonesia dan beritahu dia bahwa hari ini tidak ada quest/tugas sama sekali, ajak dia bersantai. Buatlah maksimal 2 kalimat pendek. Jangan pakai hashtag."
        )
        if API_KEY_GEMINI == 'API_KEY_TIDAK_DITEMUKAN':
            return jsonify({'greeting': 'Master belum mengatur GEMINI_API_KEY di environment variables! ⚠️'})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY_GEMINI}"
        payload = {'contents': [{'parts': [{'text': prompt}]}]}
        response = requests.post(url, json=payload, timeout=3)
        data = response.json()
        if response.status_code == 200:
            return jsonify({'greeting': data['candidates'][0]['content']['parts'][0]['text'].strip().replace('*', '')})
        return jsonify({'greeting': 'Aura sihir di markas sedang tidak stabil, Master. (Error API) ⚠️'})
    except Exception:
        return jsonify({'greeting': 'Koneksi ke markas Guild terputus sementara, Master.'})
