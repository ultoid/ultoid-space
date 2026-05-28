<div align="center">

# 🤖 Ultoid Space

**Halaman Khusus Milik Ultoid**  
Aplikasi web pintar berbasis **Python & Flask** untuk menerjemahkan dan mengelola dokumen PDF secara otomatis.  
Dirancang untuk membuat proses terjemahan novel, buku, atau dokumen panjang menjadi lebih mudah, cepat, dan rapi.

![Python](https://img.shields.io/badge/Python-3.13+-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20App-black?style=for-the-badge&logo=flask&logoColor=white)

</div>

---

## ✨ Fitur Unggulan

- 📂 **File Manager** — Kelola dokumen, gambar, dan hasil terjemahan dengan mudah melalui antarmuka lokal.
- 🎬 **Local Streaming Platform** — Nonton koleksi film dan TV series lokal dengan antarmuka modern ala Netflix, dukungan subtitle responsif, riwayat *Continue Watching*, dan *custom video player*.
- 🌐 **AI PDF Translator** — Terjemahkan PDF secara otomatis dengan bantuan AI (Google GenAI / Gemma 4), lalu simpan hasilnya ke Markdown atau Word.
- 🎮 **Game Emulator & Cloud Gaming** — Jalankan dan kelola game klasik langsung dari emulator lokal atau melalui integrasi Cloud Emulator Gaming (ROMM).
- 📝 **Notes with Flowchart** — Buat catatan visual dan diagram alur untuk ide, tugas, atau proyek.
- 📅 **Calendar Task** — Atur daftar tugas dan jadwal Anda dengan kalender terintegrasi.
- ⬇️ **Video Downloader** — Unduh video dari berbagai platform media sosial secara langsung.
- 📊 **Social Media Report** — Hasilkan laporan analitik media sosial untuk Instagram, TikTok, dan Facebook.

> **💡 Catatan Tambahan:**
> - **Konfigurasi Aman**: Gunakan `.env` untuk menyimpan API key secara aman dan rahasia.

---

## 🛠️ Persyaratan Sistem & Teknologi

Aplikasi ini menggunakan environment Python sehingga tidak mengotori instalasi global komputer Anda.

| Teknologi | Fungsi |
| :--- | :--- |
| **Python 3.13+** | Bahasa pemrograman utama |
| **Flask** | Framework untuk server web lokal |
| **PyMuPDF & pymupdf4llm** | Ekstraksi teks dari PDF dengan format Markdown |
| **Google GenAI** | Akses ke API Gemma 4 untuk terjemahan |
| **Langdetect** | Deteksi bahasa otomatis |
| **Python-Docx** | Konversi hasil akhir menjadi file `.docx` (Word) |

---

## 🚀 Cara Penggunaan (Quick Start)

Ikuti langkah-langkah di bawah ini untuk menjalankan Ultoid Space di perangkat lokal Anda:

### 1. Persiapan Awal
Clone atau download repository ini ke komputer Anda, lalu buka terminal/command prompt di dalam folder proyek.

### 2. Setup Environment
Buat *virtual environment* dan install semua library yang dibutuhkan:
```bash
# Buat virtual environment
python -m venv venv

# Aktifkan (Pilih salah satu sesuai OS)
venv\Scripts\activate      # Untuk Windows
source venv/bin/activate   # Untuk Mac/Linux

# Install dependensi
pip install -r requirements.txt
```

### 3. Konfigurasi API Key
Buat file bernama `.env` di direktori utama, lalu tambahkan API key Anda:
```env
GEMINI_API_KEY=api_gemini_anda_di_sini
RAPIDAPI_KEY=api_rapidapi_anda_di_sini    # Opsional untuk fitur social media
```

### 4. Jalankan Aplikasi
Jalankan server lokal dengan perintah:
```bash
python app.py
```
*(Khusus pengguna Windows, Anda juga bisa klik dua kali pada file `run.bat`)*

Aplikasi sekarang dapat diakses melalui browser di alamat: **`http://127.0.0.1:5000`**

---

## 📂 Struktur Proyek

```text
ultoid_space/
├── backend/             # Kode backend Flask dan blueprint (routing)
├── static/              # Aset statis: File CSS, JavaScript, gambar
├── templates/           # File antarmuka HTML
├── uploads/             # Direktori penyimpanan sementara file upload
├── outputs/             # Direktori penyimpanan hasil proses/terjemahan
├── app.py               # Entrypoint utama aplikasi Flask
├── run.bat              # Script eksekusi instan untuk OS Windows
├── requirements.txt     # Daftar dependensi modul Python
├── .gitignore           # File konfigurasi abaikan Git
└── README.md            # Dokumentasi proyek (file ini)
```

---

<div align="center">
  <i>Dibuat dengan ❤️ untuk Ultoid Space</i>
</div>