import os
import re
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import yt_dlp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BOT_TOKEN = "8798378718:AAGRxt_IwUR0m8a2M97l-5TPn8PhWpcNL9s"

# Настройки для Chrome (безголовый режим)
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Без графического интерфейса
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# ===== ФУНКЦИЯ ПОИСКА ЧЕРЕЗ SELENIUM =====
async def search_tiktok_by_hashtags(hashtags: list, limit: int = 2):
    primary_tag = hashtags[0].strip('#')
    videos_found = []
    
    driver = None
    try:
        driver = get_driver()
        url = f"https://www.tiktok.com/tag/{primary_tag}"
        driver.get(url)
        
        # Ждём загрузки видео
        time.sleep(5)
        
        # Ищем ссылки на видео
        video_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/video/']")
        
        for elem in video_elements[:limit]:
            href = elem.get_attribute('href')
            if href and 'video' in href:
                videos_found.append({"url": href})
                if len(videos_found) >= limit:
                    break
                    
    except Exception as e:
        print(f"Ошибка поиска через Selenium: {e}")
    finally:
        if driver:
            driver.quit()
    
    # Если Selenium не нашёл — пробуем запасной вариант через requests
    if not videos_found:
        try:
            import requests
            from bs4 import BeautifulSoup
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(f"https://www.tiktok.com/tag/{primary_tag}", headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            raw_urls = re.findall(r'https://www\.tiktok\.com/@[\w\.]+/video/\d+', str(soup))
            raw_urls = list(dict.fromkeys(raw_urls))[:limit]
            for url in raw_urls:
                videos_found.append({"url": url})
        except Exception as e2:
            print(f"Ошибка fallback поиска: {e2}")
    
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
