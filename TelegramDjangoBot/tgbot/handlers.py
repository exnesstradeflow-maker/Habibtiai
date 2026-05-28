import io
import random
import asyncio
from aiogram import types, F
from PIL import Image, ImageDraw, ImageFont
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from tgbot.config import dp, bot, userbot, MAIN_CHAT_ID, SUPPORT_CHAT_ID, LOG_CHAT_ID, logger
from tgbot.database_utils import check_bad_words_in_db, get_user_link, set_user_link, delete_user_link, get_invite_link, set_invite_link
from tgbot.filters import handle_user_penalty, get_image_bytes, analyze_image_with_openai, send_private

captcha_pending = {}
user_to_support = {}
support_to_user = {}
waiting_support = set()

def create_image_captcha() -> tuple[bytes, str]:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    captcha_text = "".join(random.choice(chars) for _ in range(5))
    width, height = 250, 90
    image = Image.new("RGB", (width, height), color=(235, 235, 235))
    draw = ImageDraw.Draw(image)
    for _ in range(8):
        draw.line((random.randint(0, width), random.randint(0, height), random.randint(0, width), random.randint(0, height)), fill=(random.randint(100, 180), random.randint(100, 180), random.randint(100, 180)), width=2)
    for _ in range(300):
        draw.point((random.randint(0, width), random.randint(0, height)), fill=(random.randint(50, 150), random.randint(50, 150), random.randint(50, 150)))
    try: font = ImageFont.load_default()
    except Exception: font = None
    for i, char in enumerate(captcha_text):
        draw.text((25 + (i * 40) + random.randint(-5, 5), 25 + random.randint(-8, 8)), char, fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)), font=font, scale=3)
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
        await userbot.send_file(user_id, captcha_file, caption=f"Salom, {user_name}! 👋\n🤖 Rasm ichidagi 5 xonali kodni yozib yuboring!\n⏳ Vaqt: 60 soniya.", parse_mode="html")
    except Exception as e: logger.error(f"Captcha yuborishda xatolik: {e}")

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    if message.chat.type == "private":
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔗 Havola olish", callback_data="get_link")], [InlineKeyboardButton(text="👨‍💼 Admin bilan bog'lanish", callback_data="contact_admin")]])
        await message.answer("👋 Salom! Quyidagi tugmalardan birini tanlang:", reply_markup=markup)

@dp.callback_query(F.data == "contact_admin")
async def contact_admin_callback(callback: CallbackQuery):
    waiting_support.add(callback.from_user.id)
    await callback.message.answer("💬 Savolingizni yozing, admin tez orada javob beradi!")
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
        await callback.answer("⚠️ Havola berilgan!", show_alert=True)
        return
    try:
        invite = await bot.create_chat_invite_link(chat_id=MAIN_CHAT_ID, member_limit=1)
        log_msg = await bot.send_message(LOG_CHAT_ID, f"🔗 <b>Havola olindi</b>\n👤 Ism: {callback.from_user.first_name}\n🆔 ID: <code>{user_id}</code>\n🌐 Havola: {invite.invite_link}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_link_{user_id}")]]), parse_mode="HTML")
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
        await delete_user_link(user_id)
        await callback.answer("✅ Havola o'chirildi.")
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

@dp.message(F.chat.id == MAIN_CHAT_ID, F.text)
async def check_text(message: types.Message):
    if await check_bad_words_in_db(message.text):
        await handle_user_penalty(message, reason=f"So'kinish")

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
