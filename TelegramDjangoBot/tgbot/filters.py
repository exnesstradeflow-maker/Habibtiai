import io
import base64
import requests
from PIL import Image
from aiogram import types
from tgbot.config import openai_client, bot, TELEGRAM_TOKEN, logger, MAIN_CHAT_ID, LOG_CHAT_ID
from tgbot.database_utils import get_admin_violation, set_admin_violation, get_warning, set_warning, get_invite_link, set_invite_link
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception: return False

async def send_private(user_id: int, text: str, reply_markup=None):
    from tgbot.config import userbot
    try: await bot.send_message(user_id, text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        try: await userbot.send_message(user_id, text)
        except Exception as e: logger.error(f"Shaxsiy xabar yuborib bo'lmadi: {e}")

async def send_log(text: str, user_id: int = None, unblock_button: bool = False):
    markup = None
    if unblock_button and user_id:
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data=f"unblock_{user_id}")]])
    try: await bot.send_message(LOG_CHAT_ID, text, reply_markup=markup, parse_mode="HTML")
    except Exception as e: logger.error(f"Log xatolik: {e}")

def analyze_image_with_openai(file_bytes: bytes) -> bool:
    try:
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": [{"type": "text", "text": "Ushbu rasmda odobsiz kontent bormi? Faqat HA yoki YOQ deb javob ber."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            max_tokens=5, temperature=0.0
        )
        return "HA" in response.choices[0].message.content.strip().upper()
    except Exception as e: logger.error(f"OpenAI xatolik: {e}"); return False

async def get_image_bytes(file_id: str) -> bytes | None:
    try:
        file = await bot.get_file(file_id)
        response = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file.file_path}", timeout=30)
        if response.status_code != 200: return None
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        buf = io.BytesIO(); image.save(buf, format="JPEG"); return buf.getvalue()
    except Exception as e: logger.error(f"Rasm yuklashda xatolik: {e}"); return None

async def handle_admin_violation(message: types.Message, reason: str):
    user_id = message.from_user.id
    try: await message.delete()
    except Exception: pass
    count = await get_admin_violation(user_id) + 1
    await set_admin_violation(user_id, count)
    await send_private(user_id, f"⚠️ Admin qoida buzdi! {reason} ({count}/15)")
    if count >= 15:
        await send_log(f"🚨 Adminni o'chiring! ID: {user_id} 15 marta qoida buzdi.")
        await set_admin_violation(user_id, 0)

async def handle_user_penalty(message: types.Message, reason: str):
    user_id = message.from_user.id; chat_id = message.chat.id
    if await is_admin(chat_id, user_id): await handle_admin_violation(message, reason); return
    try: await message.delete()
    except Exception: pass
    count = await get_warning(user_id) + 1; await set_warning(user_id, count)
    if count >= 3:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await send_log(f"🚫 <b>BAN:</b> {message.from_user.first_name} ({reason})", user_id=user_id, unblock_button=True)
            await set_warning(user_id, 0)
        except Exception as e: logger.error(f"Ban xatolik: {e}")
    else:
        await send_private(user_id, f"⚠️ Ogohlantirish: {count}/3. Sabab: {reason}")
