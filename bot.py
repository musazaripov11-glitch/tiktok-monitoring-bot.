#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok Video Downloader Telegram Bot
Бот для скачивания видео из TikTok без водяных знаков
"""

import os
import re
import asyncio
import logging
from pathlib import Path
import aiohttp
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, FSInputFile
from aiogram.enums import ParseMode
from database import Database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "8457618300:AAERJ48vxZxYyi2yOCOEjhJjHCAUkArGPsw"
ADMIN_USERNAME = "themzv"  # Юзернейм админа без @
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ в байтах
CAPTION = "🚀 Скачано в @tiktoksaveooffbot\nПользуйтесь и делитесь с друзьями"

# Создаем папку для временных файлов
TEMP_DIR = Path("/tmp/tiktok_downloads")
TEMP_DIR.mkdir(exist_ok=True)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
db = Database()


def is_tiktok_url(url: str) -> bool:
    """Проверка, является ли URL ссылкой на TikTok"""
    tiktok_patterns = [
        r'https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+',
        r'https?://(?:vm|vt)\.tiktok\.com/[A-Za-z0-9]+',
        r'https?://(?:www\.)?tiktok\.com/t/[A-Za-z0-9]+'
    ]
    return any(re.match(pattern, url) for pattern in tiktok_patterns)


async def download_with_ytdlp(url: str) -> tuple[str, bool]:
    """Скачивание видео через yt-dlp"""
    try:
        output_path = str(TEMP_DIR / '%(id)s.%(ext)s')
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 30,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            if info:
                video_id = info.get('id', 'video')
                ext = info.get('ext', 'mp4')
                video_path = TEMP_DIR / f"{video_id}.{ext}"
                
                if video_path.exists() and video_path.stat().st_size <= MAX_FILE_SIZE:
                    return str(video_path), True
                elif video_path.exists():
                    video_path.unlink()  # Удаляем файл, если он слишком большой
                    return "", False
        
        return "", False
    except Exception as e:
        logger.error(f"Ошибка yt-dlp: {e}")
        return "", False


async def download_with_api(url: str) -> tuple[str, bool]:
    """Fallback метод: скачивание через API"""
    try:
        # Используем бесплатный API для скачивания TikTok
        api_url = "https://api.tiklydown.eu.org/api/download"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json={"url": url}, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Пробуем получить видео без watermark
                    video_url = data.get('video', {}).get('noWatermark')
                    
                    if not video_url:
                        return "", False
                    
                    # Скачиваем видео
                    async with session.get(video_url, timeout=60) as video_response:
                        if video_response.status == 200:
                            content = await video_response.read()
                            
                            if len(content) > MAX_FILE_SIZE:
                                return "", False
                            
                            # Сохраняем во временный файл
                            video_path = TEMP_DIR / f"tiktok_{hash(url)}.mp4"
                            video_path.write_bytes(content)
                            return str(video_path), True
        
        return "", False
    except Exception as e:
        logger.error(f"Ошибка API: {e}")
        return "", False


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    # Добавляем пользователя в БД
    db.add_user(user_id, username)
    
    welcome_text = (
        "👋 Привет! Я помогу тебе скачать видео из TikTok без водяных знаков.\n\n"
        "📹 Просто отправь мне ссылку на видео из TikTok, и я пришлю его тебе!\n\n"
        "❓ Используй /help для получения подробной инструкции."
    )
    
    await message.answer(welcome_text)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = (
        "📖 Как пользоваться ботом:\n\n"
        "1️⃣ Найди интересное видео в TikTok\n"
        "2️⃣ Нажми 'Поделиться' и скопируй ссылку\n"
        "3️⃣ Отправь ссылку мне в чат\n"
        "4️⃣ Получи видео без водяного знака!\n\n"
        "⚠️ Ограничения:\n"
        "• Максимальный размер видео: 50 МБ\n"
        "• Поддерживаются только ссылки TikTok\n\n"
        "💬 Если возникли проблемы, попробуйте другую ссылку."
    )
    
    await message.answer(help_text)


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Обработчик команды /stats (только для админа)"""
    username = message.from_user.username
    
    # Проверяем, является ли пользователь админом
    if username != ADMIN_USERNAME:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Получаем статистику
    total_users = db.get_total_users()
    
    stats_text = (
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {total_users}"
    )
    
    await message.answer(stats_text)


@dp.message(F.text)
async def handle_message(message: types.Message):
    """Обработчик текстовых сообщений (ссылок на TikTok)"""
    url = message.text.strip()
    
    # Проверяем, является ли сообщение ссылкой на TikTok
    if not is_tiktok_url(url):
        await message.answer(
            "❌ Пожалуйста, отправьте правильную ссылку на TikTok видео.\n\n"
            "Пример: https://www.tiktok.com/@username/video/1234567890"
        )
        return
    
    # Отправляем сообщение о начале загрузки
    status_msg = await message.answer("⏳ Загружаю видео, подождите...")
    
    try:
        # Пробуем скачать через yt-dlp
        logger.info(f"Попытка скачать через yt-dlp: {url}")
        video_path, success = await download_with_ytdlp(url)
        
        # Если не получилось, пробуем через API
        if not success:
            logger.info(f"yt-dlp не сработал, пробуем API: {url}")
            await status_msg.edit_text("⏳ Пробую альтернативный метод...")
            video_path, success = await download_with_api(url)
        
        if not success or not video_path:
            await status_msg.edit_text(
                "❌ К сожалению, не удалось загрузить это видео. Попробуйте другую ссылку."
            )
            return
        
        # Отправляем видео пользователю
        video_file = FSInputFile(video_path)
        await message.answer_video(
            video=video_file,
            caption=CAPTION
        )
        
        # Удаляем сообщение о загрузке
        await status_msg.delete()
        
        # Удаляем временный файл
        try:
            Path(video_path).unlink()
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка при обработке видео: {e}")
        await status_msg.edit_text(
            "❌ К сожалению, не удалось загрузить это видео. Попробуйте другую ссылку."
        )


async def set_bot_commands():
    """Установка команд бота в меню"""
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Как пользоваться ботом?")
    ]
    await bot.set_my_commands(commands)


async def main():
    """Главная функция запуска бота"""
    try:
        # Инициализируем базу данных
        db.init_db()
        
        # Устанавливаем команды бота
        await set_bot_commands()
        
        logger.info("Бот запущен и готов к работе!")
        
        # Запускаем polling
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
