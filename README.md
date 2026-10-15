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

- 📂 **File Manager** — Kelola dokumen, gambar, dan hasil terjemahan melalui antarmuka lokal; URL folder mengikuti navigasi, dan Sampah mendukung pemulihan maupun penghapusan permanen.
- 🎬 **Local Streaming Platform** — Putar file film/series asli, termasuk MKV, dan unduh ke penyimpanan browser untuk ditonton ulang tanpa mengambil data dari server. Download dapat dibatalkan atau dihapus dari halaman; subtitle dan riwayat *Continue Watching* tetap didukung. Dukungan pemutaran MKV bergantung pada codec yang didukung browser/perangkat.
- 🌐 **AI PDF Translator** — Terjemahkan PDF secara otomatis dengan bantuan AI (Google GenAI / Gemma 4), lalu simpan hasilnya ke Markdown atau Word.
- 🎮 **Game Emulator & Cloud Gaming** — Jalankan dan kelola game klasik langsung dari emulator lokal atau melalui integrasi Cloud Emulator Gaming (ROMM).
- 📝 **Notes with Flowchart** — Buat catatan visual dan diagram alur untuk ide, tugas, atau proyek.
- 📅 **Calendar Task** — Atur daftar tugas dan jadwal Anda dengan kalender terintegrasi.
- ⬇️ **Media Downloader** — Unduh video dan foto publik dari YouTube, Instagram, dan TikTok. Playlist YouTube ditandai dengan jelas dan hanya item yang dipilih yang akan diunduh.
- 💬 **Ruto V1 AI** — Asisten chat pribadi dengan riwayat percakapan persisten serta memori dan skills Markdown yang dapat dikelola.

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
ULTOID_ADMIN_USERNAME=admin
ULTOID_ADMIN_PASSWORD=password_admin_kuat
GEMINI_API_KEY=api_gemini_anda
RUTO_PROVIDER=gemini
RUTO_MODEL=gemma-4-31b-it
```
`ULTOID_ADMIN_PASSWORD` wajib diisi saat pertama kali menjalankan aplikasi jika `data/credentials.txt` belum tersedia. Setelah kredensial dibuat, password tersimpan sebagai hash di file tersebut.

### Ruto V1 AI
Ruto V1 saat ini memakai Gemini API melalui `GEMINI_API_KEY`, dengan `gemma-4-31b-it` sebagai model awal. Pilihan Gemma dapat diganti di Pengaturan Ruto. Ketersediaan model dan limit mengikuti project serta akun Google AI Studio; statistik Ruto menghitung request yang dikirim oleh aplikasi ini, termasuk satu request tambahan untuk memperbarui chat memory. Riwayat chat dan chat memory disimpan di `data/ruto/ruto.sqlite3`; core memory disimpan di `data/ruto/core_memory.md`; setiap skill disimpan sebagai file Markdown terpisah di `data/ruto/skills/`. Saat upgrade, `data/ruto/memory.md` lama otomatis dipindahkan menjadi `core_memory.md`. Data tersebut bersifat lokal dan tidak disajikan sebagai file statis.

Core memory menyimpan konteks dasar yang tetap. Setelah setiap balasan, Ruto mengirim satu request AI tambahan untuk memperbarui ringkasan percakapan terkait. Ringkasan chat disimpan terpisah dari riwayat, dipakai sebagai konteks relevan pada percakapan berikutnya, dan tetap ada setelah chat dihapus. Ringkasan berusaha menghilangkan kredensial, tetapi hindari mengirim rahasia. Statistik penggunaan menghitung request ringkasan ini juga. Mekanisme ini adalah pencarian dan penggunaan kembali memori (retrieval-augmented context), bukan pelatihan ulang atau perubahan bobot model AI.

Pengaturan Ruto mencatat request dan token yang dipakai melalui Ruto, termasuk riwayat pemakaian meski chat terkait dihapus. Periksa limit model di halaman rate limits Google AI Studio. Batas RPD yang diisi di Ruto hanya menghitung request Ruto dan menghasilkan perkiraan lokal, bukan pengukur kuota akun provider yang otoritatif.

Riwayat chat bisa dicari berdasarkan judul maupun isi pesan dan dihapus satu per satu. Menghapus percakapan menghapus permanen pesan percakapan itu, tetapi tidak menghapus file memori, skills, atau catatan pemakaian request.

Saat pengguna menyertakan tautan repository, folder, atau file GitHub publik, Ruto mengambil README/file teks yang relevan melalui GitHub API dan menyertakan sumbernya sebagai konteks untuk jawaban tersebut. Untuk pertanyaan Nusvanir yang terdeteksi dari topik atau nama di core memory, Ruto memakai repository kanonis `https://github.com/ultoid/nusvanir`, menelusuri struktur repository, dan memprioritaskan dokumen Markdown serta cerita yang relevan selain README atau kode. Konteks tetap dibatasi; Ruto tidak mengklaim sudah membaca seluruh isi repository jika sumber relevan tidak tersedia. Ini bukan browser umum: hanya `github.com` dan `raw.githubusercontent.com` yang didukung, repository harus publik, hingga dua tautan dan 32.000 karakter konteks dapat dibaca per pesan. Sebelum dikirim ke model, Ruto hanya menyertakan hingga 12.000 karakter konteks GitHub yang diambil. File sumber diperlakukan sebagai data tidak tepercaya. Isi GitHub yang diambil ikut dikirim ke provider AI terpilih; percakapan sendiri tetap menyimpan pesan asli, bukan salinan konteks GitHub.

Untuk mengurangi ukuran request ke provider, Ruto membangun indeks pencarian teks penuh lokal (SQLite FTS5) per paragraf untuk core memory dan skill, serta indeks terpisah untuk ringkasan chat memory. Pencarian memakai kata kunci pertanyaan; hanya potongan yang cocok yang dikirim ke model. Indeks file dibangun saat pertama kali diperlukan atau saat file berubah; pada chat berikutnya, isi file yang tidak berubah tidak dibaca ulang. Ringkasan chat memory diindeks saat ditulis, dengan migrasi satu kali untuk ringkasan lama. File memori asli tidak diubah. Sumber GitHub juga diperingkat berdasarkan kata kunci lalu dipangkas menjadi cuplikan relevan. Riwayat lama dibatasi pada konteks yang dikirim ke model, sementara riwayat lengkap tetap tersimpan.

Provider lain yang mendukung format OpenAI Chat Completions dapat dipilih melalui `.env`:
```env
RUTO_PROVIDER=openai-compatible
RUTO_MODEL=nama_model_provider
RUTO_API_BASE_URL=https://api.example.com/v1
RUTO_API_KEY=api_key_provider
```
Ruto menambahkan `/chat/completions` ke `RUTO_API_BASE_URL`, mewajibkan HTTPS, dan hanya membaca kredensial di backend. Integrasi CopilotKu belum diaktifkan karena endpoint/API dan metode autentikasi resminya belum tersedia; jangan masukkan kredensial CopilotKu sebelum mendapatkan petunjuk integrasi resmi. CopilotKu menyebut kredit uji coba terbatas dan sistem saldo, sehingga jangan menganggap pemakaiannya selalu gratis.

Di halaman Ruto, gunakan **Memori & Skills** untuk mengubah core memory, melihat ringkasan chat memory, menambah/mengubah skill, atau mengimpor `.md`. Jawaban assistant juga bisa disimpan sebagai skill melalui tombol **Simpan sebagai skill**. Ringkasan chat otomatis dicatat sebagai konteks, bukan instruksi, dan tidak mengubah bobot model.

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