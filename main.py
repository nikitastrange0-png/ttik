import os
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import yt_dlp
from TikTokApi import TikTokApi

BOT_TOKEN = "8798378718:AAGRxt_IwUR0m8a2M97l-5TPn8PhWpcNL9s"

# ===== ФУНКЦИЯ ПОИСКА =====
async def search_tiktok_by_hashtags(hashtags: list, limit: int = 2):
    primary_tag = hashtags[0].strip('#')
    videos_found = []
    
    async with TikTokApi() as api:
        try:
            async for video in api.hashtag(name=primary_tag).videos(count=limit):
                video_url = f"https://www.tiktok.com/@{video.author.username}/video/{video.id}"
                videos_found.append({"url": video_url})
                if len(videos_found) >= limit:
                    break
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
        "📌 Отправь хештег, например: #коты"
    )

async def handle_message(update: Update, context):
    text = update.message.text.strip()
    hashtags = re.findall(r'#\w+', text)
    
    if not hashtags:
        await update.message.reply_text("❌ Напиши хештег, например: #коты")
        return
    
    tags_str = ' '.join(hashtags)
    msg = await update.message.reply_text(f"🔍 Ищу видео по {tags_str}...")
    
    videos = await search_tiktok_by_hashtags(hashtags, limit=2)
    
    if not videos:
        await msg.edit_text(f"❌ Не нашёл видео по {tags_str}")
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
