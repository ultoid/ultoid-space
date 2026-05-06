// Navigasi Pages
const page1 = document.getElementById('page1');
const page2 = document.getElementById('page2');
const page3 = document.getElementById('page3');

// Elemen Page 1
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileDetailsArea = document.getElementById('fileDetailsArea');
const pdfPreview = document.getElementById('pdfPreview');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const btnStartTranslate = document.getElementById('btnStartTranslate');

// Elemen Page 2
const terminalLog = document.getElementById('terminalLog');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');

// Elemen Page 3
const btnDownload = document.getElementById('btnDownload');
const btnReset = document.getElementById('btnReset');
const resultPreview = document.getElementById('resultPreview');

let currentFile = null;
let isTranslating = false; // <--- TAMBAHKAN INI (Penanda apakah mesin sedang jalan)

let timerInterval = null;
let processStartTime = null;
let phaseStartTime = null;

// Fungsi untuk mengubah milidetik menjadi format 00:00
function formatTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const m = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const s = String(totalSeconds % 60).padStart(2, '0');
    return `${m}:${s}`;
}

// ==========================================
// LOGIKA PAGE 1: UPLOAD & DROP
// ==========================================
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('border-blue-500', 'bg-blue-50');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('border-blue-500', 'bg-blue-50');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-blue-500', 'bg-blue-50');
    if (e.dataTransfer.files.length) {
        handleFileSelect(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFileSelect(e.target.files[0]);
    }
});

async function handleFileSelect(file) {
    if (file.type !== 'application/pdf') {
        alert('Mohon unggah file format PDF.');
        return;
    }
    
    currentFile = file;
    
    // Tampilkan Detail
    dropZone.classList.add('hidden');
    fileDetailsArea.classList.remove('hidden');
    
    // Isi Data Dasar
    fileName.textContent = file.name;
    fileSize.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
    
    // Trik Preview PDF
    const fileURL = URL.createObjectURL(file);
    pdfPreview.src = fileURL + "#toolbar=0&navpanes=0&scrollbar=0";

    // --- FITUR AUTO DETECT ---
    document.getElementById('filePages').textContent = "Mendeteksi...";
    document.getElementById('fileLang').textContent = "Mendeteksi...";
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // Kirim diam-diam ke Flask untuk dianalisis
        const response = await fetch('/analyze_pdf', { method: 'POST', body: formData });
        const data = await response.json();
        
        if (data.error) throw new Error(data.error);
        
        // Update UI dengan hasil dari Python!
        document.getElementById('filePages').textContent = data.pages + " Halaman";
        document.getElementById('fileLang').textContent = data.language;
    } catch (err) {
        document.getElementById('filePages').textContent = "? Halaman";
        document.getElementById('fileLang').textContent = "Gagal Deteksi";
        console.error("Gagal menganalisis PDF:", err);
    }
}

// ==========================================
// LOGIKA PAGE 2: TRANSISI & PROGRESS (ASLI)
// ==========================================
btnStartTranslate.addEventListener('click', () => {
    if (!currentFile) {
        alert("Pilih file PDF terlebih dahulu!");
        return;
    }
    
    // Pindah dari Page 1 ke Page 2
    page1.classList.add('hidden');
    page2.classList.remove('hidden');
    
    // Jalankan mesin asli
    runUltoidEngine(currentFile);
});

// Pastikan ini ada di bagian atas file script.js Anda (bersama variabel lainnya)
// let isTranslating = false; 

async function runUltoidEngine(file) {
    isTranslating = true; 

    // --- SETUP LIVE TIMER ---
    processStartTime = Date.now();
    phaseStartTime = Date.now(); // Mulai catat waktu fase 0 (Upload)
    const timerText = document.getElementById('timerText');
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        timerText.textContent = `⏱️ ` + formatTime(Date.now() - processStartTime);
    }, 1000);
    // ------------------------

    terminalLog.innerHTML = "> Mengunggah file ke server...\n";
    progressBar.style.width = '5%';
    progressText.textContent = '5%';

    const formData = new FormData();
    formData.append('file', file);
    
    const targetLang = document.getElementById('targetLang').value;
    formData.append('target_lang', targetLang);

    try {
        const uploadRes = await fetch('/upload', { method: 'POST', body: formData });
        const uploadData = await uploadRes.json();
        
        if (uploadData.error) throw new Error(uploadData.error);
        
        // Cetak waktu fase Upload
        const uploadTime = formatTime(Date.now() - phaseStartTime);
        terminalLog.innerHTML += `> Upload sukses! (⏱️ Waktu: ${uploadTime})\n`;
        
        // Reset timer fase untuk mulai Fase 1 (Ekstraksi)
        phaseStartTime = Date.now(); 
        
        progressBar.style.width = '15%';
        progressText.textContent = '15%';

        const eventSource = new EventSource(`/stream-translate/${uploadData.filename}`);
        
        eventSource.onmessage = function(event) {
            // JIKA SELESAI
            if (event.data.startsWith("DONE|")) {
                isTranslating = false; 
                clearInterval(timerInterval); // Matikan jam
                
                const finalFilename = event.data.split("|")[1];
                eventSource.close();
                
                // Cetak waktu Fase 3 (Gabung) dan Total Waktu
                const phase3Time = formatTime(Date.now() - phaseStartTime);
                const totalTime = formatTime(Date.now() - processStartTime);
                
                terminalLog.innerHTML += `> ⏱️ Waktu Penggabungan HTML: ${phase3Time}\n`;
                terminalLog.innerHTML += `> ✨ SELESAI SEMPURNA! (Total Waktu: ${totalTime}) ✨\n`;
                
                progressBar.style.width = '100%';
                progressText.textContent = '100%';
                
                setupDownloadPage(finalFilename);
                setTimeout(showPage3, 1000); 
            } 
            // JIKA SEDANG PROSES
            else {
                terminalLog.innerHTML += `> ${event.data}\n`;
                terminalLog.scrollTop = terminalLog.scrollHeight; 
                
                // --- LOGIKA PROGRESS BAR & TIMER FASE ---
                if (event.data.includes("Fase 1 Selesai")) {
                    // Cetak waktu Fase 1
                    const phase1Time = formatTime(Date.now() - phaseStartTime);
                    terminalLog.innerHTML += `> ⏱️ Total Waktu Ekstraksi PDF: ${phase1Time}\n`;
                    
                    // Reset timer fase untuk mulai Fase 2 (Terjemahan)
                    phaseStartTime = Date.now();
                    
                    progressBar.style.width = '40%';
                    progressText.textContent = '40%';
                } 
                else if (event.data.match(/\[(\d+)\/(\d+)\]/)) {
                    const match = event.data.match(/\[(\d+)\/(\d+)\]/);
                    const currentPart = parseInt(match[1]);
                    const totalParts = parseInt(match[2]);
                    
                    const persentaseFase2 = (currentPart / totalParts) * 50;
                    const totalProgress = Math.floor(40 + persentaseFase2); 
                    
                    progressBar.style.width = totalProgress + '%';
                    progressText.textContent = totalProgress + '%';
                } 
                else if (event.data.includes("Menggabungkan naskah")) {
                    // Cetak waktu Fase 2
                    const phase2Time = formatTime(Date.now() - phaseStartTime);
                    terminalLog.innerHTML += `> ⏱️ Total Waktu AI Menerjemahkan: ${phase2Time}\n`;
                    
                    // Reset timer fase untuk mulai Fase 3 (Gabung)
                    phaseStartTime = Date.now();
                    
                    progressBar.style.width = '95%';
                    progressText.textContent = '95%';
                }
            }
        };

        eventSource.onerror = function() {
            isTranslating = false; 
            clearInterval(timerInterval);
            terminalLog.innerHTML += `> ❌ Koneksi terputus dari server.\n`;
            eventSource.close();
            progressBar.classList.replace('bg-blue-600', 'bg-red-500');
        };

    } catch (error) {
        isTranslating = false; 
        clearInterval(timerInterval);
        terminalLog.innerHTML += `> ❌ Gagal: ${error.message}\n`;
        progressBar.classList.replace('bg-blue-600', 'bg-red-500');
    }
}

// Fungsi untuk menyiapkan file di Page 3
// Fungsi untuk menyiapkan file di Page 3
async function setupDownloadPage(projectName) {
    // Beri teks loading sementara
    document.getElementById('resultPreview').innerHTML = '<div class="text-center text-gray-500 mt-10">⏳ Memuat preview hasil terjemahan...</div>';

    // 1. Ambil Preview dari Server
    try {
        const res = await fetch(`/get_preview/${projectName}`);
        const data = await res.json();
        if(data.html) {
            document.getElementById('resultPreview').innerHTML = data.html;
        }
    } catch(e) {
        document.getElementById('resultPreview').innerHTML = "❌ Preview tidak tersedia. Namun file tetap bisa di-download.";
    }

    // 2. Logika Tombol Download ZIP / Single
    btnDownload.onclick = () => {
        const checkboxes = document.querySelectorAll('.format-cb:checked');
        const selectedFormats = Array.from(checkboxes).map(cb => cb.value);
        
        if (selectedFormats.length === 0) {
            alert("Silakan pilih minimal 1 format download!");
            return;
        }

        // Gabungkan format dengan koma (contoh: html,docx)
        const formatsStr = selectedFormats.join(',');
        
        // Arahkan browser ke rute download dinamis kita
        window.location.href = `/download_pack/${projectName}?formats=${formatsStr}`;
    };
}

// ==========================================
// LOGIKA PAGE 3: DOWNLOAD & RESET
// ==========================================
function showPage3() {
    page2.classList.add('hidden');
    page3.classList.remove('hidden');
}

btnReset.addEventListener('click', () => {
    // Kembali ke Page 1 dan reset state
    currentFile = null;
    fileInput.value = '';
    
    page3.classList.add('hidden');
    fileDetailsArea.classList.add('hidden');
    dropZone.classList.remove('hidden');
    page1.classList.remove('hidden');
    
    // Reset Progress
    progressBar.style.width = '0%';
    progressText.textContent = '0%';
});

// ==========================================
// LOGIKA PENCEGAH REFRESH / TUTUP TAB
// ==========================================
window.addEventListener('beforeunload', function (e) {
    // Jika mesin sedang tidak jalan, biarkan user keluar dengan aman
    if (!isTranslating) {
        return undefined;
    }

    // Jika mesin SEDANG jalan, cegah user keluar dan munculkan popup bawaan browser
    // Teks ini disiapkan, meskipun browser modern biasanya akan mengabaikan teksnya 
    // dan menampilkan peringatan standar mereka.
    const confirmationMessage = "Jika menutup halaman, progress akan berakhir dan harus mengulang dari awal.";
    e.preventDefault();
    e.returnValue = confirmationMessage; 
    return confirmationMessage;
});