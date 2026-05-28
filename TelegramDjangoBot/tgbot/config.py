import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from openai import OpenAI
from telethon import TelegramClient
from telethon.sessions import StringSession

# .env faylini yuklaymiz
load_dotenv()

# Maxfiy ma'lumotlarni tizim muhitidan o'qiymiz
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("SESSION_STR")

MAIN_CHAT_ID = int(os.getenv("MAIN_CHAT_ID", 0))
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID", 0))
SUPPORT_CHAT_ID = int(os.getenv("SUPPORT_CHAT_ID", 0))
LOG_BOT_TOKEN = os.getenv("LOG_BOT_TOKEN")
PYCHARM_LOG_CHANNEL_ID = int(os.getenv("PYCHARM_LOG_CHANNEL_ID", 0))

openai_client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
log_bot = Bot(token=LOG_BOT_TOKEN)
dp = Dispatcher()
userbot = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)

logger = logging.getLogger("tgbot")
