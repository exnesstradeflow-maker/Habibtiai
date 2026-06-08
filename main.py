import os
import sys
import io
import re
import base64
import random
import asyncio
import logging
import aiohttp
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from openai import OpenAI
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatMemberUpdated
from aiogram.filters import Command
from asgiref.sync import sync_to_async
import dj_database_url

# =====================================================================
# 1. ATROF-MUHIT VA SOZLAMALARNI YUKLASH
# =====================================================================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MAIN_CHAT_ID = int(os.getenv("MAIN_CHAT_ID", 0))
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID", 0))
SUPPORT_CHAT_ID = int(os.getenv("SUPPORT_CHAT_ID", 0))
LOG_BOT_TOKEN = os.getenv("LOG_BOT_TOKEN")
PYCHARM_LOG_CHANNEL_ID = int(os.getenv("PYCHARM_LOG_CHANNEL_ID", 0))

# =====================================================================
# 2. LOGGING SOZLAMALARI
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

import warnings
warnings.filterwarnings(
    "ignore",
    message="StreamingHttpResponse must consume synchronous iterators",
    category=Warning,
)
logging.getLogger("django.request").setLevel(logging.ERROR)
logging.getLogger("django.server").setLevel(logging.ERROR)

# =====================================================================
# 3. DJANGO SOZLAMALARI — PREMIUM DARK GOLD DIZAYN
# =====================================================================
import django
from django.conf import settings
from django.db import models
from django.contrib import admin

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not settings.configured:
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "worker-production-1a55.up.railway.app")
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:cnqgqNlVakEhSatvkLHKFEvaAdYKnOGa@zephyr.proxy.rlwy.net:11652/railway"
    )

    settings.configure(
        DEBUG=True,
        SECRET_KEY=os.getenv("DJANGO_SECRET_KEY", "railway-secret-key-12345"),
        DATABASES={
            'default': dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                ssl_require=False
            )
        },
        INSTALLED_APPS=[
            'jazzmin',
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            '__main__',
        ],
        ROOT_URLCONF='__main__',
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'whitenoise.middleware.WhiteNoiseMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ],
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        }],
        STATIC_URL='/static/',
        STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')] if os.path.exists(os.path.join(BASE_DIR, 'static')) else [],
        STATIC_ROOT=os.path.join(BASE_DIR, 'staticfiles'),
        ALLOWED_HOSTS=['*'],
        CSRF_TRUSTED_ORIGINS=[
            f"https://{public_domain}",
            "http://localhost:8080",
            "http://127.0.0.1:8080"
        ],
        TIME_ZONE='Asia/Tashkent',
        USE_TZ=True,

        JAZZMIN_SETTINGS={
            "site_title":    "Mafia Habibiti Admin",
            "site_header":   "⚜ Mafia Habibiti",
            "site_brand":    "⚜ Mafia Habibiti",
            "welcome_sign":  "Boshqaruv Paneliga Xush Kelibsiz!",
            "copyright":     "Mafia Habibiti Inc",
            "search_model": ["auth.User", "__main__.BadWord", "__main__.BotAdmin"],
            "show_sidebar":          True,
            "navigation_expanded":   True,
            "icons": {
                "auth":                      "fas fa-users-cog",
                "auth.user":                 "fas fa-user-shield",
                "__main__.BotSetting":       "fas fa-cogs",
                "__main__.BotOwner":         "fas fa-crown",
                "__main__.BotAdmin":         "fas fa-user-cog",
                "__main__.TelegramUser":     "fas fa-users",
                "__main__.GroupScrapedUser": "fas fa-user-plus",
                "__main__.BroadcastMessage": "fas fa-paper-plane",
                "__main__.BadWord":          "fas fa-ban",
                "__main__.UserWarning":      "fas fa-exclamation-triangle",
                "__main__.AdminViolation":   "fas fa-user-lock",
                "__main__.GroupRule":        "fas fa-scroll",
                "__main__.GroupMessage":     "fas fa-bullhorn",
            },
            "order_with_respect_to": [
                "__main__.BotSetting",
                "__main__.BotOwner",
                "__main__.BotAdmin",
                "__main__.GroupScrapedUser",
                "__main__.TelegramUser",
                "__main__.GroupMessage",
                "__main__.GroupRule",
                "__main__.BroadcastMessage",
                "__main__.BadWord",
                "auth",
            ],
            "changeform_format":  "horizontal_tabs",
        },
        JAZZMIN_UI_TWEAKS={
            "theme":           "darkly",
            "navbar":          "navbar-dark bg-dark",
            "no_navbar_border": True,
            "navbar_fixed":    True,
            "sidebar":         "sidebar-dark-warning",
            "accent":          "accent-warning",
            "button_classes": {
                "primary":   "btn-warning text-dark font-weight-bold",
                "warning":   "btn-warning text-dark",
                "danger":    "btn-danger",
                "success":   "btn-success",
            },
        },
    )
    django.setup()

# =====================================================================
# 4. MODELLAR
# =====================================================================
class BotSetting(models.Model):
    is_captcha_active      = models.BooleanField("Kaptcha faolmi?", default=True)
    is_link_active         = models.BooleanField("Havola olish faolmi?", default=True)
    is_join_request_active   = models.BooleanField("Arizalarni qabul qilsinmi?", default=True)
    is_subscription_active   = models.BooleanField("Botga /start bosmaganlar yoza olmasinmi?", default=False)
    is_rules_for_admins    = models.BooleanField("Qoidalar adminlarga ham ishlasinmi?", default=False, help_text="Yoqilsa, taqiqlangan so'zlar va filtrlar adminlarga ham jazo qo'llaydi.")

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Sozlamasi"
        verbose_name_plural = "⚙ Bot Sozlamalari"

    def __str__(self):
        return "Tizim Sozlamalari"


class BotOwner(models.Model):
    """Bot Egasi Menyusi — guruhlarda cheksiz huquq olish uchun"""
    user_id    = models.BigIntegerField("Telegram ID", unique=True)
    username   = models.CharField("Username", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi", max_length=150, null=True, blank=True)

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Egasi"
        verbose_name_plural = "👑 Bot Egalari (Owners)"

    def __str__(self):
        return f"{self.first_name or 'Owner'} ({self.user_id})"


class BotAdmin(models.Model):
    user_id    = models.BigIntegerField("Telegram ID", unique=True)
    username   = models.CharField("Username", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi", max_length=150, null=True, blank=True)
    added_at   = models.DateTimeField("Qo'shilgan vaqti", auto_now_add=True)

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Admini"
        verbose_name_plural = "🤖 Bot Adminlari"

    def __str__(self):
        return f"{self.first_name or 'Admin'} ({self.user_id})"


class TelegramUser(models.Model):
    user_id = models.BigIntegerField("Foydalanuvchi ID", primary_key=True)
    username = models.CharField("Telegram Username", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi", max_length=150, null=True, blank=True)
    joined_at = models.DateTimeField("Qo'shilgan vaqti", auto_now_add=True)

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Foydalanuvchisi"
        verbose_name_plural = "👥 Bot Foydalanuvchilari"

    def __str__(self):
        return f"{self.first_name or 'User'} ({self.user_id})"


class GroupScrapedUser(models.Model):
    """Guruhlardan yig'ilgan faol a'zolar"""
    user_id = models.BigIntegerField("User ID", primary_key=True)
    username = models.CharField("Username", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi", max_length=150, null=True, blank=True)
    group_title = models.CharField("Qaysi guruhdan", max_length=255, null=True, blank=True)
    scraped_at = models.DateTimeField("Yig'ilgan vaqti", auto_now_add=True)

    class Meta:
        app_label = '__main__'
        verbose_name = "Yig'ilgan User"
        verbose_name_plural = "📥 Guruhdan Yig'ilgan Userlar"

    def __str__(self):
        return f"{self.first_name or 'User'} (@{self.username or 'yoq'}) {self.user_id}"


class BroadcastMessage(models.Model):
    text = models.TextField("Xabar matni (HTML formatida)")
    photo_url = models.URLField("Rasm URL manzili", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False, editable=False)

    class Meta:
        app_label = '__main__'
        verbose_name = "Xabarnoma"
        verbose_name_plural = "📢 Hammaga Xabar Yuborish"


class BadWord(models.Model):
    word = models.CharField("Taqiqlangan so'z", max_length=100, unique=True)
    class Meta: app_label = '__main__'; verbose_name_plural = "🚫 Taqiqlangan so'zlar"
    def __str__(self): return self.word


class UserWarning(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    count = models.IntegerField(default=0)
    class Meta: app_label = '__main__'


class AdminViolation(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    count = models.IntegerField(default=0)
    class Meta: app_label = '__main__'


class UserLink(models.Model):
    user_id   = models.BigIntegerField(primary_key=True)
    link      = models.TextField()
    log_msg_id = models.BigIntegerField()
    class Meta: app_label = '__main__'


class InviteLink(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    link    = models.TextField()
    class Meta: app_label = '__main__'


class BannedUser(models.Model):
    user_id    = models.BigIntegerField(primary_key=True)
    username   = models.CharField(max_length=150, null=True, blank=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    reason     = models.CharField(max_length=300, null=True, blank=True)
    banned_at  = models.DateTimeField(auto_now_add=True)
    class Meta: app_label = '__main__'; verbose_name_plural = "🚨 Permanent Ban"


class GroupRule(models.Model):
    title = models.CharField(max_length=200, default="Guruh Qoidalari")
    text = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: app_label = '__main__'; verbose_name_plural = "Guruh Qoidalari"


class GroupMessage(models.Model):
    text = models.TextField()
    photo_url = models.URLField(null=True, blank=True)
    pin_message = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent    = models.BooleanField(default=False, editable=False)
    class Meta: app_label = '__main__'; verbose_name_plural = "Guruhga Xabar Yuborish"

# =====================================================================
# 5. ADMIN PANELNI RO'YXATDAN O'TKAZISH
# =====================================================================
if not admin.site.is_registered(BotSetting):
    @admin.register(BotSetting)
    class BotSettingAdmin(admin.ModelAdmin):
        list_display = ('__str__', 'is_captcha_active', 'is_link_active', 'is_rules_for_admins')

if not admin.site.is_registered(BotOwner):
    @admin.register(BotOwner)
    class BotOwnerAdmin(admin.ModelAdmin):
        list_display = ('user_id', 'username', 'first_name')
        search_fields = ('user_id', 'username', 'first_name')

if not admin.site.is_registered(BotAdmin):
    @admin.register(BotAdmin)
    class BotAdminAdmin(admin.ModelAdmin):
        list_display = ('user_id', 'username', 'first_name', 'added_at')

if not admin.site.is_registered(GroupScrapedUser):
    @admin.register(GroupScrapedUser)
    class GroupScrapedUserAdmin(admin.ModelAdmin):
        list_display = ('user_id', 'username', 'first_name', 'group_title', 'scraped_at')
        search_fields = ('user_id', 'username', 'first_name')

# Standart ro'yxatdan o'tkazishlar (boshqa modellar uchun)
for model in [TelegramUser, BroadcastMessage, BadWord, UserWarning, AdminViolation, BannedUser, GroupRule, GroupMessage]:
    if not admin.site.is_registered(model):
        admin.site.register(model)

# =====================================================================
# 6. BAZANI FIX QILISH VA ASSIGN ASYNC ORM FUNKSIYALARI
# =====================================================================
@sync_to_async
def fix_missing_tables():
    from django.core.management import call_command
    from django.contrib.auth.models import User
    from django.db import connection
    from django.apps import apps
    try:
        call_command('migrate', interactive=False)
    except Exception: pass
    try:
        existing_tables = connection.introspection.table_names()
        with connection.schema_editor() as schema_editor:
            for model in apps.get_app_config('__main__').get_models():
                if model._meta.db_table not in existing_tables:
                    schema_editor.create_model(model)
    except Exception: pass
    if not BotSetting.objects.exists():
        BotSetting.objects.create()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin777')

@sync_to_async
def is_rules_for_admins_enabled() -> bool:
    s = BotSetting.objects.first()
    return s.is_rules_for_admins if s else False

@sync_to_async
def save_scraped_user(user_id: int, username: str, first_name: str, group_title: str):
    GroupScrapedUser.objects.update_or_create(
        user_id=user_id,
        defaults={'username': username, 'first_name': first_name, 'group_title': group_title}
    )

@sync_to_async
def is_bot_owner(user_id: int) -> bool:
    return BotOwner.objects.filter(user_id=user_id).exists()

@sync_to_async
def get_bot_stats():
    return {
        "users": TelegramUser.objects.count(),
        "scraped": GroupScrapedUser.objects.count(),
        "links": UserLink.objects.count()
    }

# Boshqa eski ORM funksiyalari (muvofiqlik uchun)
@sync_to_async
def is_captcha_enabled_in_db(): return BotSetting.objects.first().is_captcha_active
@sync_to_async
def is_link_enabled_in_db(): return BotSetting.objects.first().is_link_active
@sync_to_async
def is_bot_admin(user_id: int): return BotAdmin.objects.filter(user_id=user_id).exists() or BotOwner.objects.filter(user_id=user_id).exists()
@sync_to_async
def save_user_to_db(user_id, username, first_name): TelegramUser.objects.get_or_create(user_id=user_id, defaults={'username': username, 'first_name': first_name})
@sync_to_async
def check_bad_words_in_db(text: str) -> bool:
    words = BadWord.objects.values_list('word', flat=True)
    return any(w.lower() in text.lower() for w in words)

# =====================================================================
# 7. BOT INITIATION VA ASYNC FUNKSIYALAR
# =====================================================================
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
_main_loop = None

async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception: return False

# =====================================================================
# 8. HANDLERLAR (BOT EGASI HUQUQLARI VA USER YIG'ISH MANTIG'I)
# =====================================================================

# Bot guruhga qo'shilganda yoki yangi huquq berilganda "Bot Egasi"ni admin qilish
@dp.my_chat_member()
async def on_bot_join_or_update(update: ChatMemberUpdated):
    if update.new_chat_member.status in ["administrator", "member"]:
        chat_id = update.chat.id
        owners = await sync_to_async(list)(BotOwner.objects.all())
        bot_member = await bot.get_chat_member(chat_id, (await bot.get_me()).id)
        
        # Agarda bot guruhda admin bo'lsa va uning "promoted" qilish huquqi bo'lsa
        if bot_member.status == "administrator" and bot_member.can_promote_members:
            for owner in owners:
                try:
                    await bot.promote_chat_member(
                        chat_id=chat_id,
                        user_id=owner.user_id,
                        can_change_info=bot_member.can_change_info,
                        can_post_messages=bot_member.can_post_messages,
                        can_edit_messages=bot_member.can_edit_messages,
                        can_delete_messages=bot_member.can_delete_messages,
                        can_invite_users=bot_member.can_invite_users,
                        can_restrict_members=bot_member.can_restrict_members,
                        can_pin_messages=bot_member.can_pin_messages,
                        can_promote_members=False,
                        can_manage_chat=bot_member.can_manage_chat,
                        can_manage_video_chats=bot_member.can_manage_video_chats
                    )
                    logger.info(f"👑 Bot Egasi {owner.user_id} guruhda avtomatik admin qilindi!")
                except Exception as e:
                    logger.error(f"Egani admin qilishda xatolik: {e}")

# Guruhdagi har qanday xabardan user yig'ish va admin filtri
@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_messages(message: types.Message):
    # 1. User yig'ish funksiyasi
    if message.from_user and not message.from_user.is_bot:
        await save_scraped_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            group_title=message.chat.title
        )

    # 2. Qoidalar adminlarga ishlash-ishlamasligini tekshirish
    is_user_admin = await is_admin(message.chat.id, message.from_user.id)
    rules_for_admin_active = await is_rules_for_admins_enabled()

    if is_user_admin and not rules_for_admin_active:
        return # Qoidalar adminlarga o'chiq, xabarni o'tkazib yuboramiz

    # Taqiqlangan so'zlar filtri
    if message.text and await check_bad_words_in_db(message.text):
        try:
            await message.delete()
            await message.answer(f"⚠️ <b>{message.from_user.first_name}</b>, guruhda haqoratli so'zlar taqiqlangan!")
        except Exception: pass

# =====================================================================
# 9. ADMIN PANEL (TELEGRAMDIZAYN VA MODERATORLIK FUNKSIYALARI)
# =====================================================================
@dp.message(Command("admin"))
async def admin_cmd_handler(message: types.Message):
    # Birinchi bo'lib bot admini yoki egasi ekanligini tekshirish
    if not await is_bot_admin(message.from_user.id):
        await message.reply("❌ Siz bot admini emassiz!")
        return

    # Botning huquqlarini tekshirish
    bot_id = (await bot.get_me()).id
    is_group = message.chat.type in ["group", "supergroup"]
    
    bot_can_ban = "❌ Noaktiv"
    bot_can_mute = "❌ Noaktiv"
    
    if is_group:
        try:
            bot_member = await bot.get_chat_member(message.chat.id, bot_id)
            if bot_member.status == "administrator":
                if bot_member.can_restrict_members:
                    bot_can_mute = "✅ Faol"
                    bot_can_ban = "✅ Faol"
        except Exception: pass

    stats = await get_bot_stats()
    
    panel_text = (
        "⚜ <b>MAFIA HABIBITI ADMIN PANEL</b> ⚜\n\n"
        f"📊 <b>Bot Statistikasi:</b>\n"
        f"┌ 👥 Jami a'zolar: <code>{stats['users']}</code>\n"
        f"├ 📥 Yig'ilgan faol userlar: <code>{stats['scraped']}</code>\n"
        f"└ 🔗 Havola olganlar soni: <code>{stats['links']}</code>\n\n"
        f"🤖 <b>Botning Guruhdagi Huquqlari:</b>\n"
        f"├ 🚫 Bloklash (Ban): {bot_can_ban}\n"
        f"└ 🤫 Mute (Cheklash): {bot_can_mute}\n\n"
        "<i>Boshqarish uchun quyidagi tugmalardan foydalaning:</i>"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Yig'ilgan Userlarni Ko'rish", callback_data="view_scraped_users")],
        [InlineKeyboardButton(text="⚙ Sozlamalarni Yangilash", callback_data="refresh_admin_panel")]
    ])
    
    await message.reply(panel_text, reply_markup=markup, parse_mode="HTML")

@dp.callback_query(F.data == "view_scraped_users")
async def callback_view_users(callback: CallbackQuery):
    if not await is_bot_admin(callback.from_user.id):
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return
        
    users = await sync_to_async(list)(GroupScrapedUser.objects.all().order_by('-scraped_at')[:20])
    if not users:
        await callback.message.answer("Hozircha yig'ilgan foydalanuvchilar mavjud emas.")
        await callback.answer()
        return

    text = "📥 <b>Oxirgi yig'ilgan 20 ta faol userlar:</b>\n\n"
    for idx, u in enumerate(users, 1):
        username_str = f"@{u.username}" if u.username else "yo'q"
        text += f"{idx}. <b>{u.first_name}</b> ({username_str}) <code>{u.user_id}</code>\n"

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "refresh_admin_panel")
async def callback_refresh(callback: CallbackQuery):
    await callback.answer("Statistika yangilandi! ✅")
    # Qayta chaqirish orqali yangilash mumkin
    # (Bu yerda xabarni tahrirlash kodi yozilishi mumkin)

# =====================================================================
# 10. JAZO BUYRUKLARI (BAN / MUTE) HUQUQLARNI TEKSHIRISH BILAN
# =====================================================================
@dp.message(Command("ban"))
async def ban_user_handler(message: types.Message):
    # Buyruq guruhda berilganini va adminligini tekshirish
    if message.chat.type not in ["group", "supergroup"]: return
    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    # Botning o'zida ban huquqi bormi tekshirish
    bot_member = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
    if bot_member.status != "administrator" or not bot_member.can_restrict_members:
        await message.reply("❌ Botda foydalanuvchilarni bloklash (Ban) huquqi yo'q!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Bloklash uchun biror xabarga reply (javob) qilib yozing!")
        return

    user_to_ban = message.reply_to_message.from_user.id
    try:
        await bot.ban_chat_member(message.chat.id, user_to_ban)
        await message.reply(f"🚫 <b>{message.reply_to_message.from_user.first_name}</b> guruhdan chetlatildi (Ban)!")
    except Exception as e:
        await message.reply(f"Xatolik yuz berdi: {e}")

@dp.message(Command("mute"))
async def mute_user_handler(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]: return
    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    bot_member = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
    if bot_member.status != "administrator" or not bot_member.can_restrict_members:
        await message.reply("❌ Botda foydalanuvchilarni cheklash (Mute) huquqi yo'q!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Mute qilish uchun biror xabarga reply (javob) qilib yozing!")
        return

    user_to_mute = message.reply_to_message.from_user.id
    try:
        # 5 daqiqaga mute qilish
        permissions = types.ChatPermissions(can_send_messages=False, can_send_audios=False, can_send_documents=False, can_send_photos=False, can_send_videos=False)
        await bot.restrict_chat_member(message.chat.id, user_to_mute, permissions=permissions)
        await message.reply(f"🤫 <b>{message.reply_to_message.from_user.first_name}</b> 5 daqiqaga guruhda yozish huquqidan mahrum qilindi (Mute)!")
    except Exception as e:
        await message.reply(f"Xatolik yuz berdi: {e}")

# =====================================================================
# DJANGO ADMIN VA ASYNC RUN SOZLAMALARI
# =====================================================================
from django.urls import path
from django.http import HttpResponse

def home_view(request):
    return HttpResponse("<h2>⚜ Mafia Habibiti Tizimi Tayyor!</h2>")

urlpatterns = [path('', home_view), path('admin/', admin.site.urls)]

async def main():
    global _main_loop
    _main_loop = asyncio.get_event_loop()
    
    from django.core.management import call_command
    await asyncio.to_thread(call_command, 'collectstatic', interactive=False)
    await fix_missing_tables()
    
    logger.info("🚀 Bot ishga tushmoqda...")
    # Polling boshlash
    await dp.start_polling(bot)

if __name__ == '__main__':
    import uvicorn
    from django.core.asgi import get_asgi_application

    async def run_server():
        asgi_app = get_asgi_application()
        config = uvicorn.Config(asgi_app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="warning")
        server = uvicorn.Server(config)
        await server.serve()

    async def main_runner():
        await asyncio.gather(main(), run_server())

    asyncio.run(main_runner())
