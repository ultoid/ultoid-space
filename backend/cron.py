import os
import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from .config import IG_ACCOUNTS_FILE, TT_ACCOUNTS_FILE


def process_delta_for_file(filepath, is_fb=False):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        accounts = json.load(f)
    now = datetime.now()
    target_month_index = now.month - 1 if now.day < 15 else now.month
    target_year = now.year if target_month_index > 0 else now.year - 1
    if target_month_index == 0:
        target_month_index = 12
    months_arr = ['jan', 'feb', 'mar', 'apr', 'mei', 'jun', 'jul', 'agu', 'sep', 'okt', 'nov', 'des']
    target_month_str = months_arr[target_month_index - 1]
    for user, acc in accounts.items():
        prof = acc['profile']
        cum_posts = prof.get('posts_base', 0)
        for y in range(2026, target_year):
            cum_posts += sum(prof.get(f'posts_{y}', {}).values())
        for m in months_arr[:target_month_index-1]:
            cum_posts += prof.get(f'posts_{target_year}', {}).get(m, 0)
        live_posts = prof.get('total_posts', 0)
        delta_posts = live_posts - cum_posts
        if delta_posts < 0:
            delta_posts = 0
        prof.setdefault(f'posts_{target_year}', {})
        prof[f'posts_{target_year}'][target_month_str] = delta_posts
        if not is_fb:
            cum_foll = prof.get('followers_base', 0)
            for y in range(2026, target_year):
                cum_foll += sum(prof.get(f'followers_{y}', {}).values())
            for m in months_arr[:target_month_index-1]:
                cum_foll += prof.get(f'followers_{target_year}', {}).get(m, 0)
            live_foll = prof.get('followers', 0)
            if isinstance(live_foll, str):
                live_foll = 0
            delta_foll = live_foll - cum_foll
            if delta_foll < 0:
                delta_foll = 0
            prof.setdefault(f'followers_{target_year}', {})
            prof[f'followers_{target_year}'][target_month_str] = delta_foll
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=4)
    print(f"[{filepath}] Selesai dikalkulasi.")


def calculate_monthly_delta():
    print(f"[{datetime.now()}] MEMULAI KALKULASI DELTA BULANAN UNTUK IG & TT...")
    process_delta_for_file(IG_ACCOUNTS_FILE, is_fb=False)
    process_delta_for_file(TT_ACCOUNTS_FILE, is_fb=False)


def setup_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=calculate_monthly_delta, trigger='cron', day=1, hour=1, minute=0)
    scheduler.start()
    import atexit
    atexit.register(lambda: scheduler.shutdown())
    app.scheduler = scheduler
