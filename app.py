import os
import time
import fitz  # PyMuPDF
import markdown
import zipfile
import io
from docx import Document
from google import genai
from langdetect import detect
from flask import Flask, render_template, request, Response, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Konfigurasi Folder & API
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Membaca API Key otomatis dari file API_key.txt
try:
    with open('API_key.txt', 'r') as file:
        API_KEY_GEMINI = file.read().strip()
except FileNotFoundError:
    API_KEY_GEMINI = "API_KEY_TIDAK_DITEMUKAN"
    print("PERINGATAN: File API_key.txt tidak ditemukan!")

client = genai.Client(api_key=API_KEY_GEMINI)

@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# JALUR CEPAT: DETEKSI BAHASA & HALAMAN
# ==========================================
@app.route('/analyze_pdf', methods=['POST'])
def analyze_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file'}), 400
    
    file = request.files['file']
    filename = secure_filename(file.filename)
    
    # Simpan sementara untuk dianalisis
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], "temp_" + filename)
    file.save(temp_path)
    
    try:
        doc = fitz.open(temp_path)
        jml_halaman = len(doc)
        
        # Cari teks dari 20 halaman pertama
        text_sample = ""
        for i in range(min(20, jml_halaman)):
            teks_halaman = doc[i].get_text().strip()
            if teks_halaman:
                text_sample += teks_halaman + " "
            if len(text_sample) > 50:
                break
                
        # Deteksi Bahasa
        lang_code = "unknown"
        if len(text_sample) > 10:
            try:
                lang_code = detect(text_sample)
            except:
                pass
        
        lang_map = {
            'id': '🇮🇩 Indonesia', 'en': '🇬🇧 Inggris', 
            'ja': '🇯🇵 Jepang', 'ko': '🇰🇷 Korea', 
            'zh-cn': '🇨🇳 Mandarin', 'zh-tw': '🇨🇳 Mandarin'
        }
        
        if lang_code == "unknown":
            bahasa_terdeteksi = "✨ Auto Deteksi AI"
        else:
            bahasa_terdeteksi = lang_map.get(lang_code, f"✨ Auto ({lang_code})")
        
        # WAJIB: Tutup dulu dokumennya agar file tidak terkunci oleh Windows
        doc.close() 
        
        # Setelah ditutup, baru aman untuk dihapus
        os.remove(temp_path)
        
        return jsonify({
            'pages': jml_halaman,
            'language': bahasa_terdeteksi
        })
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500

# ==========================================
# JALUR UTAMA: UPLOAD PDF UNTUK DITERJEMAHKAN
# ==========================================
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'File kosong'}), 400
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    return jsonify({'filename': filename})

# ==========================================
# JALUR STREAMING: PROSES MESIN ULTOID
# ==========================================
@app.route('/stream-translate/<filename>')
def stream_translate(filename):
    def generate():
        import pymupdf4llm # Import di sini agar aman dari bentrok saat analisa
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        nama_proyek = filename.replace('.pdf', '')
        
        folder_md = os.path.join(OUTPUT_FOLDER, f"{nama_proyek}_md")
        folder_terjemahan = os.path.join(OUTPUT_FOLDER, f"{nama_proyek}_indo")
        os.makedirs(folder_md, exist_ok=True)
        os.makedirs(folder_terjemahan, exist_ok=True)
        
        yield f"data: 📚 Memulai ekstraksi PDF: {filename}...\n\n"
        
        # FASE 1: Ekstrak
        try:
            md_text = pymupdf4llm.to_markdown(file_path)
        except Exception as e:
            yield f"data: ❌ Gagal mengekstrak PDF. Error: {str(e)}\n\n"
            return

        baris_teks = md_text.split('\n')
        part_count = 1
        chunk_sekarang = ""
        
        for baris in baris_teks:
            if len(chunk_sekarang) + len(baris) < 15000:
                chunk_sekarang += baris + "\n"
            else:
                if chunk_sekarang.strip():
                    nama_file = f"{nama_proyek}_{part_count:03d}_Part.md"
                    with open(os.path.join(folder_md, nama_file), "w", encoding="utf-8") as f:
                        f.write(chunk_sekarang.strip())
                    yield f"data: ✅ Part {part_count} tersimpan.\n\n"
                    part_count += 1
                chunk_sekarang = baris + "\n"
                
        if chunk_sekarang.strip():
            nama_file = f"{nama_proyek}_{part_count:03d}_Part.md"
            with open(os.path.join(folder_md, nama_file), "w", encoding="utf-8") as f:
                f.write(chunk_sekarang.strip())
            yield f"data: ✅ Part {part_count} (Sisa akhir) tersimpan.\n\n"
            
        yield f"data: 🎉 Fase 1 Selesai. Memulai Fase 2 (Gemma 4 API)...\n\n"
        
        # FASE 2: Translasi
        files_md = sorted([f for f in os.listdir(folder_md) if f.endswith(".md")])
        total_files = len(files_md)
        system_prompt = "Terjemahkan dalam bahasa indonesia dengan style terjemahan novel yang mudah dimengerti, tulis hasil terjemahannya saja."
        
        for i, md_file in enumerate(files_md, 1):
            out_path = os.path.join(folder_terjemahan, f"INDO_{md_file}")
            
            # Fitur Skip jika sudah ada (Sangat berguna jika internet putus di tengah jalan)
            if os.path.exists(out_path):
                yield f"data: ⏩ Skip [{i}/{total_files}]: {md_file} (Sudah diterjemahkan)\n\n"
                continue

            yield f"data: ⏳ [{i}/{total_files}] Memproses {md_file}...\n\n"
            
            with open(os.path.join(folder_md, md_file), "r", encoding="utf-8") as f:
                isi_teks = f.read()
                
            try:
                response = client.models.generate_content(
                    model='gemma-4-26b-a4b-it',
                    contents=f"{system_prompt}\n\nTEKS ASLI:\n{isi_teks}"
                )
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(response.text.strip())
                yield f"data: ✅ Selesai [{i}/{total_files}]\n\n"
                time.sleep(3)
            except Exception as e:
                yield f"data: ❌ Error pada part {i}: {str(e)}\n\n"

        # FASE 3: Gabung & Buat Multi-Format
        yield f"data: 🔄 Menyimpan dalam format HTML, MD, TXT, dan DOCX...\n\n"
        daftar_indo = sorted([f for f in os.listdir(folder_terjemahan) if "INDO_" in f])
        
        md_gabungan = ""
        for nama_file in daftar_indo:
            with open(os.path.join(folder_terjemahan, nama_file), "r", encoding="utf-8") as f_in:
                md_gabungan += f_in.read() + "\n\n"

        # 1. Simpan Markdown (.md)
        file_md = f"{nama_proyek}_Ultoid.md"
        with open(os.path.join(OUTPUT_FOLDER, file_md), "w", encoding="utf-8") as f:
            f.write(md_gabungan)

        # 2. Simpan Text murni (.txt)
        file_txt = f"{nama_proyek}_Ultoid.txt"
        with open(os.path.join(OUTPUT_FOLDER, file_txt), "w", encoding="utf-8") as f:
            f.write(md_gabungan.replace('#', '').replace('*', '')) # Hapus simbol MD dasar

        # 3. Simpan HTML (.html)
        html_body = markdown.markdown(md_gabungan)
        html_final = f"<!DOCTYPE html><html lang='id'><head><meta charset='utf-8'><style>body {{ font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; color: black; }} p {{ margin-bottom: 1.2em; text-indent: 0; }}</style></head><body>{html_body}</body></html>"
        file_html = f"{nama_proyek}_Ultoid.html"
        with open(os.path.join(OUTPUT_FOLDER, file_html), "w", encoding="utf-8") as f:
            f.write(html_final)

        # 4. Simpan Word (.docx)
        try:
            doc_word = Document()
            for baris in md_gabungan.split('\n'):
                if baris.strip():
                    doc_word.add_paragraph(baris.replace('#', '').replace('*', ''))
            file_docx = f"{nama_proyek}_Ultoid.docx"
            doc_word.save(os.path.join(OUTPUT_FOLDER, file_docx))
        except Exception as e:
            yield f"data: ❌ Gagal membuat DOCX: {str(e)}\n\n"

        # Kirim nama proyek ke UI
        yield f"data: DONE|{nama_proyek}\n\n"

    return Response(generate(), mimetype='text/event-stream')


# ==========================================
# JALUR PREVIEW TAMPILAN
# ==========================================
@app.route('/get_preview/<proyek>')
def get_preview(proyek):
    html_path = os.path.join(app.config['UPLOAD_FOLDER'].replace('uploads', 'outputs'), f"{proyek}_Ultoid.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            konten = f.read()
        # Ambil 3000 karakter pertama saja untuk preview agar ringan
        return jsonify({'html': konten[:3000] + "...<br><br><b>(Preview Dibatasi)</b>"})
    except:
        return jsonify({'html': '<p>Gagal memuat preview.</p>'})


# ==========================================
# JALUR DOWNLOAD & ZIP DINAMIS
# ==========================================
@app.route('/download_pack/<proyek>')
def download_pack(proyek):
    formats = request.args.get('formats', '').split(',')
    output_dir = app.config['UPLOAD_FOLDER'].replace('uploads', 'outputs')
    
    # Cari file yang diminta
    files_to_send = []
    for fmt in formats:
        if fmt in ['html', 'md', 'txt', 'docx']:
            filename = f"{proyek}_Ultoid.{fmt}"
            path = os.path.join(output_dir, filename)
            if os.path.exists(path):
                files_to_send.append((filename, path))
    
    # Jika cuma 1 format, langsung download filenya
    if len(files_to_send) == 1:
        return send_file(files_to_send[0][1], as_attachment=True)
    
    # Jika lebih dari 1, gabungkan jadi ZIP
    elif len(files_to_send) > 1:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename, path in files_to_send:
                zf.write(path, filename)
        memory_file.seek(0)
        return send_file(memory_file, download_name=f"{proyek}_Ultoid_Pack.zip", as_attachment=True)
    
    return "File tidak ditemukan", 404

if __name__ == '__main__':
    app.run(debug=True, threaded=True)