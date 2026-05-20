# 🤖 Ultoid Translate: AI-Powered PDF Translator

**Ultoid Translate** adalah aplikasi web portabel berbasis Python (Flask) yang dirancang untuk menerjemahkan dokumen PDF (terutama novel/buku) secara otomatis menggunakan mesin AI **Google Gemini (Gemma 4)**. Aplikasi ini fokus pada kemudahan penggunaan, kecepatan, dan hasil terjemahan bergaya narasi novel.

---

## ✨ Fitur Unggulan

*   **🔍 Auto-Language Detection**: Mendeteksi bahasa asal dokumen secara otomatis (Inggris, Jepang, Korea, dll.) meskipun halaman awal berisi gambar/sampul.
*   **⚡ Real-Time Streaming Progress**: Pantau proses ekstraksi dan translasi baris demi baris melalui terminal log interaktif.
*   **⏱️ Smart Timer & Progress Bar**: Dilengkapi dengan *live timer* dan bar progres dinamis yang bergerak berdasarkan jumlah *part* yang diproses.
*   **📄 Multi-Format Export**: Unduh hasil terjemahan dalam format `.html`, `.docx`, `.md`, atau `.txt`.
*   **📦 Auto-Zip Downloader**: Jika memilih lebih dari satu format, aplikasi akan membungkusnya secara otomatis ke dalam satu file `.zip`.
*   **🖼️ PDF Preview**: Lihat langsung file PDF yang diunggah di dalam browser sebelum mulai menerjemahkan.
*   **⚠️ Safety Navigation**: Peringatan konfirmasi jika pengguna tidak sengaja mencoba menutup tab atau me-refresh halaman saat proses sedang berjalan.

---

## 🛠️ Persyaratan Sistem

Aplikasi ini menggunakan **Python 3.13+ (system or virtualenv)** sehingga tidak memerlukan instalasi Python secara global di komputer. Library utama yang digunakan:

*   **Flask**: Untuk server web lokal.
*   **PyMuPDF (fitz) & pymupdf4llm**: Untuk ekstraksi teks dari PDF ke Markdown.
*   **Google GenAI**: Untuk akses API Gemma 4.
*   **Langdetect**: Untuk deteksi bahasa otomatis.
*   **Python-Docx**: Untuk pembuatan file Word.

---

## 🚀 Cara Penggunaan

1.  **Clone / Download** repository ini.
2.  **API Key**: Masukkan API Key Google Gemini kamu ke dalam file `API_key.txt` di folder utama.
3.  **Jalankan Aplikasi**: Klik dua kali pada file `run.bat`.
4.  **Akses Web**: Browser akan otomatis terbuka ke alamat `http://127.0.0.1:5000`.
5.  **Mulai**: Drag & drop file PDF, tunggu deteksi selesai, lalu klik **Mulai Terjemahkan**.

---

## 📂 Struktur Proyek
```text
ultoid_translate/
├── static/              # File CSS dan JavaScript (script.js)
├── templates/           # File HTML (index.html)
├── uploads/             # Folder penyimpanan file PDF yang diunggah
├── outputs/             # Folder hasil terjemahan (MD, HTML, DOCX, TXT)
├── app.py               # Backend utama Flask
├── run.bat              # Script eksekusi satu klik
├── API_key.txt          # File rahasia API Key (Jangan di-upload ke GitHub!)
├── .gitignore           # Daftar file/folder yang diabaikan oleh Git
└── README.md            # Dokumentasi proyek

\nMinimal setup:
1. python -m venv venv
2. venv\\Scripts\\activate (Windows) atau source venv/bin/activate (Linux/mac)
3. pip install -r requirements.txt
