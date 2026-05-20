import requests
import json
import time
import re
from bs4 import BeautifulSoup

# ==========================================
# KONFIGURASI — Sesuaikan ini!
# ==========================================
VPS_URL = "http://202.74.74.151:8080/"        # Ganti dengan IP VPS kamu
SCRAPER_SECRET = "ultoid_scraper_key_2026" # Harus sama dengan di app.py
COOKIES_FILE = "ig_cookies.txt"            # Path ke file cookies
DELAY_ANTAR_AKUN = 3                       # Detik jeda antar scraping (jangan terlalu cepat)

# ==========================================
# FUNGSI BACA COOKIES
# ==========================================
def load_cookies():
    cookies = {}
    try:
        with open(COOKIES_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    k, v = line.split('=', 1)
                    cookies[k.strip()] = v.strip()
        print(f"✅ Cookies berhasil dibaca ({len(cookies)} item)")
    except FileNotFoundError:
        print(f"❌ File {COOKIES_FILE} tidak ditemukan!")
    return cookies

# ==========================================
# FUNGSI SCRAPE SATU AKUN IG
# ==========================================
def scrape_ig(username, cookies):
    username = username.replace('@', '').strip().lower()
    print(f"  🔍 Scraping @{username}...")

    followers_num = 0
    posts_num = 0
    bio_name = username

    # Jalur 1: IG Internal API dengan cookies
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'X-IG-App-ID': '1217981644879628',
            'X-CSRFToken': cookies.get('csrftoken', ''),
            'Referer': 'https://www.instagram.com/',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        res = requests.get(api_url, headers=headers, cookies=cookies, timeout=10)

        if res.status_code == 200:
            json_data = res.json()
            user_data = json_data.get('data', {}).get('user', {})
            if user_data:
                followers_num = int(user_data.get('edge_followed_by', {}).get('count', 0))
                posts_num = int(user_data.get('edge_owner_to_timeline_media', {}).get('count', 0))
                bio_name = user_data.get('full_name', username)
                print(f"  ✅ Jalur 1 sukses: {followers_num:,} followers")
                return build_payload(username, bio_name, followers_num, posts_num)
        else:
            print(f"  ⚠️ Jalur 1 gagal: status {res.status_code}")

    except Exception as e:
        print(f"  ⚠️ Jalur 1 error: {e}")

    # Jalur 2: Picuki
    try:
        picuki_url = f"https://www.picuki.com/profile/{username}"
        res2 = requests.get(picuki_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res2.status_code == 200:
            soup = BeautifulSoup(res2.text, 'html.parser')
            name_tag = soup.find(class_='profile-name-bottom')
            if name_tag:
                bio_name = name_tag.get_text(strip=True)
            stats = soup.find_all('span', class_='profile-stat-count')
            if len(stats) >= 2:
                posts_num = int(stats[0].get_text(strip=True).replace(',', '').replace('.', ''))
                followers_num = int(stats[1].get_text(strip=True).replace(',', '').replace('.', ''))
                print(f"  ✅ Jalur 2 (Picuki) sukses: {followers_num:,} followers")
                return build_payload(username, bio_name, followers_num, posts_num)
    except Exception as e:
        print(f"  ⚠️ Jalur 2 error: {e}")

    # Jalur 3: Meta tags (fallback, angka bisa dibulatkan)
    try:
        html_url = f"https://www.instagram.com/{username}/"
        res3 = requests.get(html_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res3.text, 'html.parser')
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', property='og:description')
        if meta_desc:
            content = meta_desc.get('content', '')
            f_match = re.search(r'([\d,.KMB]+)\s+Followers', content, re.IGNORECASE)
            if f_match:
                f_str = f_match.group(1).upper().replace(',', '')
                if 'M' in f_str:
                    followers_num = int(float(f_str.replace('M', '')) * 1_000_000)
                elif 'K' in f_str:
                    followers_num = int(float(f_str.replace('K', '')) * 1_000)
                else:
                    followers_num = int(float(f_str))
            print(f"  ⚠️ Jalur 3 (meta) dipakai: {followers_num:,} followers (mungkin dibulatkan)")
            return build_payload(username, bio_name, followers_num, posts_num)
    except Exception as e:
        print(f"  ❌ Jalur 3 error: {e}")

    print(f"  ❌ Semua jalur gagal untuk @{username}")
    return None

# ==========================================
# FUNGSI BUAT PAYLOAD DATA
# ==========================================
def build_payload(username, bio_name, followers, posts):
    return {
        "profile": {
            "username": username,
            "bio": bio_name,
            "followers": followers,
            "total_posts": posts,
            "profile_pic": f"https://ui-avatars.com/api/?name={username}&background=random"
        },
        "posts": []
    }

# ==========================================
# FUNGSI KIRIM DATA KE VPS
# ==========================================
def kirim_ke_vps(data):
    try:
        res = requests.post(
            f"{VPS_URL}/api/ig/receive",
            json=data,
            headers={'X-Scraper-Key': SCRAPER_SECRET},
            timeout=10
        )
        if res.status_code == 200:
            print(f"  📤 Terkirim ke VPS!")
            return True
        else:
            print(f"  ❌ Gagal kirim ke VPS: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error koneksi ke VPS: {e}")
        return False

# ==========================================
# FUNGSI AMBIL DAFTAR AKUN DARI VPS
# ==========================================
def ambil_daftar_akun():
    try:
        res = requests.get(
            f"{VPS_URL}/api/ig/accounts",
            headers={'X-Scraper-Key': SCRAPER_SECRET},
            timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            return list(data.get('accounts', {}).keys())
        else:
            print(f"⚠️ Gagal ambil daftar akun dari VPS: {res.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error koneksi ke VPS: {e}")
        return []

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("=" * 50)
    print("  🚀 Ultoid IG Scraper Lokal")
    print("=" * 50)

    cookies = load_cookies()
    if not cookies:
        print("❌ Tidak ada cookies, scraping bisa gagal.")

    print("\n📋 Pilihan mode:")
    print("  1. Scrape semua akun yang sudah ada di VPS")
    print("  2. Scrape akun baru (input manual)")
    pilihan = input("\nPilih (1/2): ").strip()

    if pilihan == "1":
        print("\n📡 Mengambil daftar akun dari VPS...")
        usernames = ambil_daftar_akun()
        if not usernames:
            print("❌ Tidak ada akun di database VPS.")
        else:
            print(f"✅ {len(usernames)} akun ditemukan: {', '.join(['@'+u for u in usernames])}")
            print("\n🔄 Mulai scraping...\n")
            sukses = 0
            for username in usernames:
                data = scrape_ig(username, cookies)
                if data:
                    if kirim_ke_vps(data):
                        sukses += 1
                time.sleep(DELAY_ANTAR_AKUN)
            print(f"\n✅ Selesai! {sukses}/{len(usernames)} akun berhasil diupdate.")

    elif pilihan == "2":
        usernames_input = input("Masukkan username (pisah koma jika lebih dari 1): ").strip()
        usernames = [u.strip() for u in usernames_input.split(',') if u.strip()]
        print(f"\n🔄 Scraping {len(usernames)} akun...\n")
        sukses = 0
        for username in usernames:
            data = scrape_ig(username, cookies)
            if data:
                if kirim_ke_vps(data):
                    sukses += 1
            time.sleep(DELAY_ANTAR_AKUN)
        print(f"\n✅ Selesai! {sukses}/{len(usernames)} akun berhasil.")

    else:
        print("❌ Pilihan tidak valid.")

    input("\nTekan Enter untuk keluar...")
