import os
import sys
import io
import re
import base64
import random
import asyncio
import logging
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from openai import OpenAI
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from asgiref.sync import sync_to_async

# =====================================================================
# 1. ATROF-MUHIT VA SOZLAMALARNI YUKLASH
# =====================================================================
load_dotenv()

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

# =====================================================================
# 2. DJANGO BAZASINI KOD ICHIDA SOZLASH (PAPKA SHART EMAS)
# =====================================================================
import django
from django.conf import settings
from django.db import models

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db.sqlite3'),
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            '__main__',  # Modellar shu faylning o'zida ekanligini bildiradi
        ],
        TIME_ZONE='UTC',
        USE_TZ=True,
    )
    django.setup()

# =====================================================================
# 3. MA'LUMOTLAR BAZASI MODELLARI (JADVALLARI)
# =====================================================================
class BadWord(models.Model):
    word = models.CharField(max_length=100, unique=True)
    class Meta: app_label = '__main__'

class UserWarning(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    count = models.IntegerField(default=0)
    class Meta: app_label = '__main__'

class AdminViolation(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    count = models.IntegerField(default=0)
    class Meta: app_label = '__main__'

class UserLink(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    link = models.TextField()
    log_msg_id = models.BigIntegerField()
    class Meta: app_label = '__main__'

class InviteLink(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    link = models.TextField()
    class Meta: app_label = '__main__'

# Jadvallarni avtomatik yaratish (Migratsiyasiz ishlaydi!)
from django.core.management import call_command
django.setup()
with django.db.connection.schema_editor() as schema_editor:
    for model in [BadWord, UserWarning, AdminViolation, UserLink, InviteLink]:
        if not model._meta.db_table in django.db.connection.introspection.table_names():
            schema_editor.create_model(model)

# =====================================================================
# 4. DJANGO ORM ASYNC FUNKSIYALARI
# =====================================================================
@sync_to_async
def check_bad_words_in_db(text: str) -> bool:
    text_lower = text.lower()
    words = BadWord.objects.values_list('word', flat=True)
    for bad_word in words:
        pattern = r'\b' + re.escape(bad_word.lower()) + r'\b'
        if re.search(pattern, text_lower): return True
    return False

@sync_to_async
def get_warning(user_id: int) -> int:
    obj, created = UserWarning.objects.get_or_create(user_id=user_id)
    return obj.count

@sync_to_async
def set_warning(user_id: int, count: int):
    if count <= 0: UserWarning.objects.filter(user_id=user_id).delete()
    else: UserWarning.objects.update_or_create(user_id=user_id, defaults={'count': count})

@sync_to_async
def get_admin_violation(user_id: int) -> int:
    obj, created = AdminViolation.objects.get_or_create(user_id=user_id)
    return obj.count

@sync_to_async
def set_admin_violation(user_id: int, count: int):
    if count <= 0: AdminViolation.objects.filter(user_id=user_id).delete()
    else: AdminViolation.objects.update_or_create(user_id=user_id, defaults={'count': count})

@sync_to_async
def get_user_link(user_id: int):
    try:
        obj = UserLink.objects.get(user_id=user_id)
        return {"link": obj.link, "log_msg_id": obj.log_msg_id}
    except UserLink.DoesNotExist: return None

@sync_to_async
def set_user_link(user_id: int, link: str, log_msg_id: int):
    UserLink.objects.update_or_create(user_id=user_id, defaults={'link': link, 'log_msg_id': log_msg_id})

@sync_to_async
def delete_user_link(user_id: int):
    UserLink.objects.filter(user_id=user_id).delete()

@sync_to_async
def get_invite_link(user_id: int):
    try: return InviteLink.objects.get(user_id=user_id).link
    except InviteLink.DoesNotExist: return None

@sync_to_async
def set_invite_link(user_id: int, link: str):
    InviteLink.objects.update_or_create(user_id=user_id, defaults={'link': link})

# =====================================================================
# 5. BOT IKKILAMCHI SOZLAMALARI VA LOGGING
# =====================================================================
openai_client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
log_bot = Bot(token=LOG_BOT_TOKEN)
dp = Dispatcher()
userbot = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)

captcha_pending = {}
user_to_support = {}
support_to_user = {}
waiting_support = set()

class TelegramLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        if any(k in log_entry.lower() for k in ["retryafter", "badrequest", "flood control"]): return
        safe_log = log_entry.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        async def safe_send():
            try:
                await asyncio.sleep(1)
                await log_bot.send_message(PYCHARM_LOG_CHANNEL_ID, f"🖥 <b>Terminal Log:</b>\n<pre>{safe_log}</pre>", parse_mode="HTML")
            except Exception: pass
        try: asyncio.create_task(safe_send())
        except Exception: pass

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(TelegramLogHandler())

# =====================================================================
# 6. YORDAMCHI FUNKSIYALAR VA FILTRLAR (OPENAI)
# =====================================================================
async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception: return False

async def send_private(user_id: int, text: str, reply_markup=None):
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

# =====================================================================
# 7. CAPTCHA GENERATOR
# =====================================================================
def create_image_captcha() -> tuple[bytes, str]:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    captcha_text = "".join(random.choice(chars) for _ in range(5))
    width, height = 250, 90
    image = Image.new("RGB", (width, height), color=(235, 235, 235))
    draw = ImageDraw.Draw(image)
    for _ in range(8):
        draw.line((random.randint(0, width), random.randint(0, height), random.randint(0, width), random.randint(0, height)), fill=(150, 150, 150), width=2)
    try: font = ImageFont.load_default()
    except Exception: font = None
    for i, char in enumerate(captcha_text):
        draw.text((25 + (i * 40), 25), char, fill=(0, 0, 0), font=font, scale=3)
    img_byte_arr = io.BytesIO(); image.save(img_byte_arr, format='PNG'); return img_byte_arr.getvalue(), captcha_text

async def captcha_timeout(user_id: int):
    await asyncio.sleep(60)
    if user_id in captcha_pending:
        del captcha_pending[user_id]
        await send_private(user_id, "⏰ Captcha vaqti tugadi! Qayta urinib ko'ring.")

async def send_captcha(user_id: int, user_name: str):
    img_bytes, captcha_code = create_image_captcha()
    if user_id in captcha_pending: captcha_pending[user_id]["task"].cancel()
    task = asyncio.create_task(captcha_timeout(user_id))
    captcha_pending[user_id] = {"code": captcha_code, "task": task}
    try:
        captcha_file = io.BytesIO(img_bytes); captcha_file.name = "captcha.png"
        await userbot.send_file(user_id, captcha_file, caption=f"Salom, {user_name}! 👋\n🤖 Rasm ichidagi kodni yozib yuboring!\n⏳ Vaqt: 60 soniya.")
    except Exception as e: logger.error(f"Captcha yuborishda xatolik: {e}")

# =====================================================================
# 8. JAZOLASH STRATEGIYASI
# =====================================================================
async def handle_admin_violation(message: types.Message, reason: str):
    user_id = message.from_user.id
    try: await message.delete()
    except Exception: pass
    count = await get_admin_violation(user_id) + 1; await set_admin_violation(user_id, count)
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

# =====================================================================
# 9. AIOGRAM HANDLERS (BOT MANTIQI)
# =====================================================================
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    if message.chat.type == "private":
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔗 Havola olish", callback_data="get_link")], [InlineKeyboardButton(text="👨‍💼 Admin bilan bog'lanish", callback_data="contact_admin")]])
        await message.answer("👋 Salom! Quyidagi tugmalardan birini tanlang:", reply_markup=markup)

@dp.callback_query(F.data == "contact_admin")
async def contact_admin_callback(callback: CallbackQuery):
    waiting_support.add(callback.from_user.id)
    await callback.message.answer("💬 Savolingizni yozing, admin javob beradi!")
    try: await callback.answer()
    except Exception: pass

@dp.message(F.chat.type == "private")
async def handle_private_message(message: types.Message):
    user_id = message.from_user.id
    if (message.text and message.text.startswith("/")) or user_id in captcha_pending: return
    if user_id in waiting_support or user_id in user_to_support:
        waiting_support.discard(user_id)
        header = f"💬 <b>Foydalanuvchi xabari</b>\n👤 Ism: {message.from_user.first_name}\n🆔 ID: <code>{user_id}</code>\n{'—' * 20}\n"
        try:
            sent = await bot.send_message(SUPPORT_CHAT_ID, header + (message.text or "[Media]"), parse_mode="HTML")
            user_to_support[user_id] = sent.message_id; support_to_user[sent.message_id] = user_id
            await message.answer("✅ Xabaringiz adminga yuborildi!")
        except Exception as e: logger.error(f"Support xatolik: {e}")

@dp.message(F.chat.id == SUPPORT_CHAT_ID)
async def handle_support_reply(message: types.Message):
    if not message.reply_to_message: return
    replied_id = message.reply_to_message.message_id
    if replied_id not in support_to_user: return
    target_user_id = support_to_user[replied_id]
    try:
        await bot.send_message(target_user_id, f"👮 <b>Admin</b> javob berdi:\n\n{message.text or '[Media]'}", parse_mode="HTML")
        user_to_support[target_user_id] = message.message_id; support_to_user[message.message_id] = target_user_id
    except Exception as e: await message.reply(f"❌ Xabar yuborilmadi: {e}")

@dp.callback_query(F.data == "get_link")
async def get_link_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    existing_data = await get_user_link(user_id)
    if existing_data:
        await callback.answer("⚠️ Havola berilgan!", show_alert=True); return
    try:
        invite = await bot.create_chat_invite_link(chat_id=MAIN_CHAT_ID, member_limit=1)
        log_msg = await bot.send_message(LOG_CHAT_ID, f"🔗 <b>Havola olindi</b>\n👤 {callback.from_user.first_name}\n🌐 {invite.invite_link}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_link_{user_id}")]]), parse_mode="HTML")
        await set_user_link(user_id, invite.invite_link, log_msg.message_id)
        await callback.message.answer(f"🔗 Havolangiz:\n\n{invite.invite_link}")
        await callback.answer()
    except Exception as e: logger.error(f"Link xatolik: {e}")

@dp.callback_query(F.data.startswith("cancel_link_"))
async def cancel_link_callback(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    link_data = await get_user_link(user_id)
    if link_data:
        try: await bot.revoke_chat_invite_link(chat_id=MAIN_CHAT_ID, invite_link=link_data["link"])
        except Exception: pass
        await delete_user_link(user_id); await callback.answer("✅ Havola o'chirildi.")
    try: await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ O'chirildi", callback_data="done")]]))
    except Exception: pass

@dp.callback_query(F.data.startswith("unblock_"))
async def unblock_user(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    try:
        await bot.unban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
        link = await get_invite_link(user_id)
        if not link:
            invite = await bot.create_chat_invite_link(chat_id=MAIN_CHAT_ID, member_limit=1)
            link = invite.invite_link; await set_invite_link(user_id, link)
        await send_private(user_id, f"✅ Blokdan chiqdingiz. Havola:\n\n{link}")
        await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Blokdan chiqarildi", callback_data="done")]]))
        await callback.answer("✅ Bajarildi")
    except Exception as e: logger.error(f"Unblock xatolik: {e}")

# Guruh ichidagi xabarlarni filtrlash
@dp.message(F.chat.id == MAIN_CHAT_ID, F.text)
async def check_text(message: types.Message):
    if await check_bad_words_in_db(message.text): await handle_user_penalty(message, reason="So'kinish")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.photo)
async def check_photo(message: types.Message):
    image_bytes = await get_image_bytes(message.photo[-1].file_id)
    if image_bytes and analyze_image_with_openai(image_bytes): await handle_user_penalty(message, reason="Odobsiz rasm")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.video | F.video_note)
async def check_video(message: types.Message):
    thumb = message.video.thumbnail if message.video else message.video_note.thumbnail
    if thumb:
        image_bytes = await get_image_bytes(thumb.file_id)
        if image_bytes and analyze_image_with_openai(image_bytes): await handle_user_penalty(message, reason="Odobsiz video")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.sticker | F.animation)
async def check_media(message: types.Message):
    file_id = message.animation.file_id if message.animation else (message.sticker.file_id if not message.sticker.is_animated else (message.sticker.thumbnail.file_id if message.sticker.thumbnail else None))
    if file_id:
        image_bytes = await get_image_bytes(file_id)
        if image_bytes and analyze_image_with_openai(image_bytes): await handle_user_penalty(message, reason="Odobsiz media")

@dp.chat_join_request()
async def on_join_request(update: types.ChatJoinRequest):
    if update.chat.id == MAIN_CHAT_ID: await send_captcha(update.from_user.id, update.from_user.first_name)

# =====================================================================
# 10. USERBOT CAPTCHA JAVOBLARINI TEKSHIRISH
# =====================================================================
async def setup_userbot_handlers():
    @userbot.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def on_captcha_reply(event):
        user_id = event.sender_id
        if user_id not in captcha_pending: return
        if event.text.strip().upper() == captcha_pending[user_id]["code"]:
            captcha_pending[user_id]["task"].cancel(); del captcha_pending[user_id]
            try:
                await bot.approve_chat_join_request(MAIN_CHAT_ID, user_id)
                await send_private(user_id, "✅ Guruhga xush kelibsiz! 🎉")
            except Exception as e: logger.error(f"Approve xatolik: {e}")
        else:
            captcha_pending[user_id]["task"].cancel(); del captcha_pending[user_id]
            try: await bot.decline_chat_join_request(MAIN_CHAT_ID, user_id)
            except Exception: pass

# =====================================================================
# MAIN ISHGA TUSHIRISH
# =====================================================================
async def main():
    logger.info("🤖 LOYIHA ISHGA TUSHDI!")
    await userbot.start()
    await setup_userbot_handlers()
    await asyncio.gather(dp.start_polling(bot), userbot.run_until_disconnected())

if __name__ == "__main__":
    asyncio.run(main())
