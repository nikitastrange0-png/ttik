import os
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import yt_dlp
from tiktok_scraper import TikTokScraper

BOT_TOKEN = "8798378718:AAGRxt_IwUR0m8a2M97l-5TPn8PhWpcNL9s"



async def search_tiktok_by_hashtags(hashtags: list, limit: int = 2):
    primary_tag = hashtags[0].strip('#')
    videos_found = []
    
    scraper = TikTokScraper()
    try:
        # Используем встроенный метод поиска по хештегу
        result = scraper.hashtag(hashtag=primary_tag, count=limit)
        
        if result and 'videos' in result:
            for video in result['videos'][:limit]:
                video_url = f"https://www.tiktok.com/@{video['author']['uniqueId']}/video/{video['id']}"
                videos_found.append({"url": video_url})
                
    except Exception as e:
        print(f"Ошибка поиска: {e}")
    
    return videos_found

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
    msg = await update.message.reply_text(f"🔍 Ищу видео по {tags_str}...")
    
    videos = await search_tiktok_by_hashtags(hashtags, limit=2)
    
    if not videos:
        await msg.edit_text(f"❌ Не нашёл видео по {tags_str}\nПопробуй другой хештег")
        return
    
    await msg.edit_text(f"📹 Нашёл {len(videos)} видео, скачиваю...")
    
    for video in videos:
        video_path = await download_video(video['url'])
        if video_path and os.path.exists(video_path):
            with open(video_path, 'rb') as f:
                await update.message.reply_video(video=f, caption=f"📌 {tags_str}")
            os.remove(video_path)
    
    await update.message.reply_text("✅ Готово!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
    
