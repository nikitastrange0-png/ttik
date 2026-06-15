import os
import re
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import yt_dlp
from curl_cffi import requests as curl_requests

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8798378718:AAGRxt_IwUR0m8a2M97l-5TPn8PhWpcNL9s"
RAILWAY_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")

flask_app = Flask(__name__)
telegram_app = Application.builder().token(BOT_TOKEN).build()

# ===== ФУНКЦИИ ПОИСКА В TIKTOK =====
async def get_video_date(video_url: str) -> datetime:
    try:
        response = curl_requests.get(video_url, impersonate="chrome", timeout=10)
        match = re.search(r'"createTime":\s*"(\d{4}-\d{2}-\d{2})"', response.text)
        if match:
            return datetime.strptime(match.group(1), '%Y-%m-%d')
        return datetime.now() - timedelta(days=999)
    except Exception:
        return datetime.now() - timedelta(days=999)

async def is_video_fresh(video_url: str, max_days_old: int = 3) -> bool:
    video_date = await get_video_date(video_url)
    return (datetime.now() - video_date).days <= max_days_old

async def check_video_hashtags(video_url: str, required_tags: list) -> bool:
    try:
        response = curl_requests.get(video_url, impersonate="chrome", timeout=10)
        found_tags = re.findall(r'#([\wа-яё]+)', response.text, re.IGNORECASE)
        found_tags = [tag.lower() for tag in found_tags]
        return all(tag.lower() in found_tags for tag in required_tags)
    except Exception:
        return False

async def search_tiktok_by_hashtags(hashtags: list, limit: int = 2, max_days_old: int = 3):
    primary_tag = hashtags[0].strip('#')
    other_tags = [tag.strip('#') for tag in hashtags[1:]]
    
    videos_found = []
    checked_urls = set()
    page = 0
    
    while len(videos_found) < limit and page < 6:
        try:
            url = f"https://www.tiktok.com/tag/{primary_tag}"
            if page > 0:
                url += f"?page={page}"
            
            response = curl_requests.get(url, impersonate="chrome", timeout=15)
            raw_urls = re.findall(r'https://www\.tiktok\.com/@[\w\.]+/video/\d+', response.text)
            raw_urls = list(dict.fromkeys(raw_urls))
            
            for video_url in raw_urls:
                if len(videos_found) >= limit:
                    break
                if video_url in checked_urls:
                    continue
                checked_urls.add(video_url)
                
                if not await is_video_fresh(video_url, max_days_old):
                    continue
                
                if other_tags and not await check_video_hashtags(video_url, other_tags):
                    continue
                
                videos_found.append({"url": video_url})
            
            page += 1
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            break
    
    return videos_found[:limit]

async def download_video(url: str) -> str:
    output_path = "temp_video.mp4"
    ydl_opts = {
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        return None

# ===== КОМАНДЫ БОТА =====
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 Привет! Я ищу видео в TikTok по хештегам.\n\n"
        "📌 Отправь хештег, например: #коты\n"
        "🔍 Можно комбинировать: #коты #смешные\n"
        "📅 Указать период: #коты days=7"
    )

async def handle_message(update: Update, context):
    text = update.message.text.strip()
    
    days_match = re.search(r'days[=\s]+(\d+)', text, re.IGNORECASE)
    max_days = int(days_match.group(1)) if days_match else 3
    
    clean_text = re.sub(r'\s*days[=\s]+\d+', '', text, flags=re.IGNORECASE)
    hashtags = re.findall(r'#\w+', clean_text)
    
    if not hashtags:
        await update.message.reply_text("❌ Напиши хештег, например: #коты")
        return
    
    tags_str = ' '.join(hashtags)
    msg = await update.message.reply_text(f"🔍 Ищу видео по {tags_str} (до {max_days} дней)...")
    
    videos = await search_tiktok_by_hashtags(hashtags, limit=2, max_days_old=max_days)
    
    if not videos:
        await msg.edit_text(f"❌ Не нашёл свежих видео по {tags_str}")
        return
    
    await msg.edit_text(f"📹 Нашёл {len(videos)} видео, скачиваю...")
    
    for video in videos:
        video_path = await download_video(video['url'])
        if video_path and os.path.exists(video_path):
            with open(video_path, 'rb') as f:
                await update.message.reply_video(video=f, caption=f"📌 {tags_str}")
            os.remove(video_path)
    
    await update.message.reply_text("✅ Готово!")

# Регистрируем обработчики
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ===== WEBHOOK =====
@flask_app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, telegram_app.bot)
        asyncio.run(telegram_app.process_update(update))
        return 'ok', 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return 'error', 500

@flask_app.route('/')
def health():
    return 'ok', 200

# ===== ЗАПУСК =====
if __name__ == '__main__':
    if RAILWAY_DOMAIN:
        webhook_url = f"https://{RAILWAY_DOMAIN}/webhook/{BOT_TOKEN}"
        asyncio.run(telegram_app.bot.set_webhook(url=webhook_url))
        print(f"✅ Вебхук: {webhook_url}")
    else:
        print("⚠️ RAILWAY_PUBLIC_DOMAIN не задан")
    
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)
