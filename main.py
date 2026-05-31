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
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from asgiref.sync import sync_to_async
import dj_database_url

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
# 2. LOGGING SOZLAMALARI
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# =====================================================================
# 3. DJANGO SOZLAMALARI — MAFIA HABIBITI PREMIUM DARK GOLD DIZAYN
# =====================================================================
import django
from django.conf import settings
from django.db import models
from django.contrib import admin

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not settings.configured:
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "worker-production-1a55.up.railway.app")
    
    # Siz taqdim etgan yoki Railway tomonidan beriladigan ma'lumotlar bazasi manzili
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
            'jazzmin',           # ← Birinchi bo'lishi SHART
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
            'whitenoise.middleware.WhiteNoiseMiddleware',  # 🚀 RAILWAY'DA DIZAYN CHIQISHI UCHUN QO'SHILDI!
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
        STATICFILES_DIRS=[
            os.path.join(BASE_DIR, 'static'),   # ← mafia_custom.css shu yerda
        ],
        STATIC_ROOT=os.path.join(BASE_DIR, 'staticfiles'), # 🚀 DIZAYNLARNI JAMLOVCHI PAPKA!

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
            "search_model": ["auth.User", "__main__.BadWord"],
            "show_sidebar":          True,
            "navigation_expanded":   True,
            "hide_apps":             [],
            "hide_models":           [],
            "icons": {
                "auth":                      "fas fa-users-cog",
                "auth.user":                 "fas fa-user-shield",
                "auth.Group":                "fas fa-users",
                "__main__.TelegramUser":     "fas fa-users",
                "__main__.BroadcastMessage": "fas fa-paper-plane",
                "__main__.BadWord":          "fas fa-ban",
                "__main__.UserWarning":      "fas fa-exclamation-triangle",
                "__main__.AdminViolation":   "fas fa-user-lock",
                "__main__.BotSetting":       "fas fa-cogs",
            },
            "default_icon_parents":  "fas fa-chevron-circle-right",
            "default_icon_children": "fas fa-circle",
            "order_with_respect_to": [
                "__main__.BotSetting",
                "__main__.TelegramUser",
                "__main__.BroadcastMessage",
                "__main__.BadWord",
                "__main__.UserWarning",
                "__main__.AdminViolation",
                "auth",
            ],
            "custom_css": "admin/css/mafia_custom.css",
            "custom_js":  None,
            "show_ui_builder":    False,
            "changeform_format":  "horizontal_tabs",
            "language_chooser":   False,
        },

        JAZZMIN_UI_TWEAKS={
            "theme":           "darkly",
            "navbar":          "navbar-dark bg-dark",
            "no_navbar_border": True,
            "navbar_fixed":    True,
            "sidebar":         "sidebar-dark-warning",
            "sidebar_nav_small_text":   False,
            "sidebar_disable_expand":   False,
            "sidebar_nav_child_indent": True,
            "sidebar_nav_compact_style": False,
            "sidebar_nav_flat_style":   False,
            "sidebar_nav_legacy_style": False,
            "accent": "accent-warning",
            "footer_fixed": False,
            "button_classes": {
                "primary":   "btn-warning text-dark font-weight-bold",
                "secondary": "btn-outline-secondary",
                "info":      "btn-outline-info",
                "warning":   "btn-warning text-dark",
                "danger":    "btn-danger",
                "success":   "btn-success",
            },
            "actions_sticky_top": True,
        },
    )
    django.setup()

# =====================================================================
# 4. MODELLAR
# =====================================================================
class BotSetting(models.Model):
    is_captcha_active = models.BooleanField("Kaptcha faolmi? / Активна ли каптча?", default=True)

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Sozlamasi"
        verbose_name_plural = "⚙ Bot Sozlamalari"

    def __str__(self):
        return "Tizim Sozlamalari"


class TelegramUser(models.Model):
    user_id = models.BigIntegerField("Foydalanuvchi ID", primary_key=True)
    username = models.CharField("Telegram Username", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi", max_length=150, null=True, blank=True)
    joined_at = models.DateTimeField("Qo'shilgan vaqti", auto_now_add=True)

    def __str__(self):
        return f"{self.first_name or 'User'} ({self.user_id})"

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Foydalanuvchisi"
        verbose_name_plural = "👥 Bot Foydalanuvchilari"


class BroadcastMessage(models.Model):
    text = models.TextField("Xabar matni (HTML formatida yozish mumkin)", help_text="Masalan: <b>Salom</b>")
    photo_url = models.URLField("Rasm URL manzili (ixtiyoriy)", null=True, blank=True, help_text="Rasm bilan yuborish uchun havola qo'ying")
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    is_sent = models.BooleanField("Yuborildimi?", default=False, editable=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.is_sent:
            # asyncio.get_event_loop() Django thread pool ichida ishlamaydi.
            # Global _main_loop o'zgaruvchisini ishlatamiz (main() da saqlanadi).
            try:
                loop = _main_loop
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.start_broadcast(), loop)
                else:
                    logger.error("❌ Rassilka: asosiy event loop topilmadi!")
            except Exception as e:
                logger.error(f"❌ Rassilka ishga tushirishda xatolik: {e}")

    async def start_broadcast(self):
        await asyncio.sleep(2)
        users = await sync_to_async(list)(TelegramUser.objects.all())
        logger.info(f"📢 Rassilka boshlandi. Jami foydalanuvchilar: {len(users)}")

        success, failed = 0, 0
        for u in users:
            try:
                if self.photo_url:
                    await bot.send_photo(chat_id=u.user_id, photo=self.photo_url, caption=self.text, parse_mode="HTML")
                else:
                    await bot.send_message(chat_id=u.user_id, text=self.text, parse_mode="HTML")
                success += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                failed += 1
                logger.error(f"Rassilka xatolik user {u.user_id}: {e}")

        await sync_to_async(BroadcastMessage.objects.filter(pk=self.pk).update)(is_sent=True)
        logger.info(f"📢 Rassilka yakunlandi! Muvaffaqiyatli: {success}, Xatolik: {failed}")

    class Meta:
        app_label = '__main__'
        verbose_name = "Xabarnoma yuborish"
        verbose_name_plural = "📢 Hammaga Xabar Yuborish (Rassilka)"


class BadWord(models.Model):
    word = models.CharField("Taqiqlangan so'z / Запрещённое слово", max_length=100, unique=True)
    def __str__(self): return self.word
    class Meta:
        app_label = '__main__'
        verbose_name = "Taqiqlangan so'z"
        verbose_name_plural = "🚫 Taqiqlangan so'zlar / Запрещённые слова"


class UserWarning(models.Model):
    user_id = models.BigIntegerField("Foydalanuvchi ID / ID пользователя", primary_key=True)
    count = models.IntegerField("Ogohlantirishlar soni / Кол-во предупреждений", default=0)
    class Meta:
        app_label = '__main__'
        verbose_name = "Foydalanuvchi ogohlantirishi"
        verbose_name_plural = "⚠️ Ogohlantirishlar / Предупреждения"


class AdminViolation(models.Model):
    user_id = models.BigIntegerField("Admin ID / ID админа", primary_key=True)
    count = models.IntegerField("Qoida buzish soni / Кол-во нарушения", default=0)
    class Meta:
        app_label = '__main__'
        verbose_name = "Admin xatosi"
        verbose_name_plural = "👮 Admin xatolari / Нарушения админов"


class UserLink(models.Model):
    user_id   = models.BigIntegerField(primary_key=True)
    link      = models.TextField()
    log_msg_id = models.BigIntegerField()
    class Meta: app_label = '__main__'


class InviteLink(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    link    = models.TextField()
    class Meta: app_label = '__main__'


# =====================================================================
# 5. ADMIN REGISTRATSIYA
# =====================================================================
if not admin.site.is_registered(BotSetting):
    @admin.register(BotSetting)
    class BotSettingAdmin(admin.ModelAdmin):
        list_display = ('__str__', 'is_captcha_active')
        editable_fields = ('is_captcha_active',)

if not admin.site.is_registered(TelegramUser):
    @admin.register(TelegramUser)
    class TelegramUserAdmin(admin.ModelAdmin):
        list_display = ('user_id', 'username', 'first_name', 'joined_at')
        search_fields = ('user_id', 'username', 'first_name')

if not admin.site.is_registered(BroadcastMessage):
    @admin.register(BroadcastMessage)
    class BroadcastMessageAdmin(admin.ModelAdmin):
        list_display = ('id', 'created_at', 'is_sent')
        readonly_fields = ('is_sent',)

if not admin.site.is_registered(BadWord):
    @admin.register(BadWord)
    class BadWordAdmin(admin.ModelAdmin):
        list_display, search_fields, ordering, list_per_page = ('id', 'word'), ('word',), ('word',), 25

if not admin.site.is_registered(UserWarning):
    @admin.register(UserWarning)
    class UserWarningAdmin(admin.ModelAdmin):
        list_display, search_fields, ordering, list_per_page = ('user_id', 'count'), ('user_id',), ('-count',), 25

if not admin.site.is_registered(AdminViolation):
    @admin.register(AdminViolation)
    class AdminViolationAdmin(admin.ModelAdmin):
        list_display, search_fields, ordering, list_per_page = ('user_id', 'count'), ('user_id',), ('-count',), 25

admin.site.site_header = "⚜ Mafia Habibiti"
admin.site.index_title = "Boshqaruv paneli"

# =====================================================================
# 6. BAZANI SOZLASH (MIGRATIONS AND INITIAL DATA)
# =====================================================================
@sync_to_async
def fix_missing_tables():
    from django.core.management import call_command
    from django.contrib.auth.models import User
    from django.db import connection
    from django.apps import apps

    # 1. Django standart jadvallarini yaratish (auth, sessions va h.k.)
    try:
        call_command('migrate', interactive=False)
        logger.info("✅ Migratsiyalar muvaffaqiyatli bajarildi!")
    except Exception as e:
        logger.error(f"Migrate xatolik: {e}")

    # 2. __main__ app modellari uchun jadvallarni to'g'ridan-to'g'ri yaratish
    # (chunki __main__ uchun migration fayllari yo'q, migrate ularni o'tkazib ketadi)
    try:
        existing_tables = connection.introspection.table_names()
        with connection.schema_editor() as schema_editor:
            for model in apps.get_app_config('__main__').get_models():
                table_name = model._meta.db_table
                if table_name not in existing_tables:
                    try:
                        schema_editor.create_model(model)
                        logger.info(f"✅ Jadval yaratildi: {table_name}")
                    except Exception as e:
                        logger.error(f"Jadval yaratishda xatolik ({model.__name__}): {e}")
                else:
                    logger.info(f"ℹ️ Jadval mavjud: {table_name}")
    except Exception as e:
        logger.error(f"Schema editor xatolik: {e}")

    # 3. Defolt bot sozlamasini yaratish
    try:
        if not BotSetting.objects.exists():
            BotSetting.objects.create(is_captcha_active=True)
            logger.info("⚙ Standart bot sozlamalari yaratildi.")
    except Exception as e:
        logger.error(f"BotSetting yaratishda xatolik: {e}")

    try:
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin777')
            logger.info("🔐 Admin foydalanuvchisi yaratildi. Login: admin | Parol: admin777")
    except Exception as e:
        logger.error(f"Admin yaratishda xatolik: {e}")

# =====================================================================
# 7. URL SOZLAMALARI
# =====================================================================
from django.urls import path
from django.http import HttpResponse

def home_view(request):
    return HttpResponse("""
    <html>
    <head>
        <title>⚜ Mafia Habibiti</title>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700&family=Rajdhani:wght@500&display=swap" rel="stylesheet">
        <style>
            body { background:#080a0f; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; font-family:'Rajdhani',sans-serif; }
            .box { background:rgba(13,15,24,0.95); border:1px solid rgba(255,215,0,0.15); border-radius:14px; padding:40px; text-align:center; max-width:400px; }
            h2 { font-family:'Cinzel',serif; color:#ffd700; margin-bottom:16px; font-size:22px; letter-spacing:0.08em; }
            p { color:rgba(255,215,0,0.4); margin-bottom:28px; font-size:14px; }
            a { background:linear-gradient(135deg,#b8860b,#ffd700); color:#000; padding:12px 28px; border-radius:8px; text-decoration:none; font-weight:700; font-size:13px; letter-spacing:0.06em; text-transform:uppercase; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>⚜ Mafia Habibiti</h2>
            <p>Tizim muvaffaqiyatli ishga tushdi</p>
            <a href="/admin/">Admin panelga kirish</a>
        </div>
    </body>
    </html>
    """)

urlpatterns = [
    path('', home_view),
    path('admin/', admin.site.urls),
]

# =====================================================================
# 8. ORM FUNKSIYALARI (ASYNC)
# =====================================================================
@sync_to_async
def is_captcha_enabled_in_db() -> bool:
    try:
        setting = BotSetting.objects.first()
        return setting.is_captcha_active if setting else True
    except Exception:
        return True

@sync_to_async
def save_user_to_db(user_id: int, username: str, first_name: str):
    TelegramUser.objects.get_or_create(
        user_id=user_id,
        defaults={'username': username, 'first_name': first_name}
    )

@sync_to_async
def check_bad_words_in_db(text: str) -> bool:
    text_lower = text.lower()
    words = BadWord.objects.values_list('word', flat=True)
    for bad_word in words:
        pattern = r'\b' + re.escape(bad_word.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return True
    return False

@sync_to_async
def get_warning(user_id: int) -> int:
    obj, _ = UserWarning.objects.get_or_create(user_id=user_id)
    return obj.count

@sync_to_async
def set_warning(user_id: int, count: int):
    if count <= 0: UserWarning.objects.filter(user_id=user_id).delete()
    else: UserWarning.objects.update_or_create(user_id=user_id, defaults={'count': count})

@sync_to_async
def get_admin_violation(user_id: int) -> int:
    obj, _ = AdminViolation.objects.get_or_create(user_id=user_id)
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
# 9. BOT INSTANCELARI
# =====================================================================
openai_client = OpenAI(api_key=OPENAI_API_KEY)
bot     = Bot(token=TELEGRAM_TOKEN)
log_bot = Bot(token=LOG_BOT_TOKEN)
dp      = Dispatcher()
userbot = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)

captcha_pending  = {}
user_to_support  = {}
support_to_user  = {}
waiting_support  = set()

# Rassilka uchun global event loop (Django thread pool ichidan foydalanish uchun)
_main_loop: asyncio.AbstractEventLoop | None = None

# =====================================================================
# 10. YORDAMCHI FUNKSIYALAR
# =====================================================================
async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception: return False

async def send_private(user_id: int, text: str, reply_markup=None):
    try:
        await bot.send_message(user_id, text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        try: await userbot.send_message(user_id, text)
        except Exception as e: logger.error(f"Shaxsiy xabar yuborib bo'lmadi: {e}")

async def send_log(text: str, user_id: int = None, unblock_button: bool = False):
    markup = None
    if unblock_button and user_id:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data=f"unblock_{user_id}")
        ]])
    try: await bot.send_message(LOG_CHAT_ID, text, reply_markup=markup, parse_mode="HTML")
    except Exception as e: logger.error(f"Log xatolik: {e}")

# Async OpenAI tahlili
async def analyze_image_async(file_bytes: bytes) -> bool:
    return await asyncio.to_thread(analyze_image_with_openai, file_bytes)

def analyze_image_with_openai(file_bytes: bytes) -> bool:
    try:
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "Ushbu rasmda odobsiz kontent bormi? Faqat HA yoki YOQ deb javob ber."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}],
            max_tokens=5, temperature=0.0
        )
        return "HA" in response.choices[0].message.content.strip().upper()
    except Exception as e:
        logger.error(f"OpenAI xatolik: {e}")
        return False

# 🚀 ASYNCHRONOUS IMAGE DOWNLOADER (Botni muzlatib qo'ymaydi)
async def get_image_bytes(file_id: str) -> bytes | None:
    try:
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file.file_path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url, timeout=30) as response:
                if response.status != 200:
                    return None
                content = await response.read()
                
        image = Image.open(io.BytesIO(content)).convert("RGB")
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Rasm yuklashda xatolik (Async): {e}")
        return None

# =====================================================================
# 11. JAZOLASH
# =====================================================================
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
    user_id = message.from_user.id
    chat_id = message.chat.id
    if await is_admin(chat_id, user_id):
        await handle_admin_violation(message, reason)
        return
    try: await message.delete()
    except Exception: pass
    count = await get_warning(user_id) + 1
    await set_warning(user_id, count)
    if count >= 3:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await send_log(f"🚫 <b>BAN:</b> {message.from_user.first_name} ({reason})", user_id=user_id, unblock_button=True)
            await set_warning(user_id, 0)
        except Exception as e: logger.error(f"Ban xatolik: {e}")
    else:
        await send_private(user_id, f"⚠️ Ogohlantirish: {count}/3. Sabab: {reason}")

# =====================================================================
# 12. CAPTCHA MANTIG'I
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
        draw.text((25 + (i * 40), 25), char, fill=(0, 0, 0), font=font)
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue(), captcha_text

async def captcha_timeout(user_id: int):
    await asyncio.sleep(60)
    if user_id in captcha_pending:
        del captcha_pending[user_id]
        await send_private(user_id, "⏰ Captcha vaqti tugadi! Qayta urinib ko'ring.")

async def send_captcha(user_id: int, user_name: str):
    img_bytes, captcha_code = create_image_captcha()
    if user_id in captcha_pending:
        captcha_pending[user_id]["task"].cancel()
    task = asyncio.create_task(captcha_timeout(user_id))
    captcha_pending[user_id] = {"code": captcha_code, "task": task}
    try:
        captcha_file = io.BytesIO(img_bytes)
        captcha_file.name = "captcha.png"
        await userbot.send_file(user_id, captcha_file, caption=f"Salom, {user_name}! 👋\n🤖 Rasm ichidagi kodni yozib yuboring!\n⏳ Vaqt: 60 soniya.")
    except Exception as e: logger.error(f"Captcha yuborishda xatolik: {e}")

# =====================================================================
# 13. AIOGRAM HANDLERS
# =====================================================================
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await save_user_to_db(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    if message.chat.type == "private":
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Havola olish",           callback_data="get_link")],
            [InlineKeyboardButton(text="👨‍💼 Admin bilan bog'lanish", callback_data="contact_admin")],
        ])
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
    await save_user_to_db(user_id, message.from_user.username, message.from_user.first_name)

    if (message.text and message.text.startswith("/")) or user_id in captcha_pending:
        return
    if user_id in waiting_support or user_id in user_to_support:
        waiting_support.discard(user_id)
        header = f"💬 <b>Foydalanuvchi xabari</b>\n👤 Ism: {message.from_user.first_name}\n🆔 ID: <code>{user_id}</code>\n{'—' * 20}\n"
        try:
            sent = await bot.send_message(SUPPORT_CHAT_ID, header + (message.text or "[Media]"), parse_mode="HTML")
            user_to_support[user_id] = sent.message_id
            support_to_user[sent.message_id] = user_id
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
        user_to_support[target_user_id] = message.message_id
        support_to_user[message.message_id] = target_user_id
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
        log_msg = await bot.send_message(LOG_CHAT_ID, f"🔗 <b>Havola olindi</b>\n👤 {callback.from_user.first_name}\n🌐 {invite.invite_link}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_link_{user_id}")]], parse_mode="HTML"))
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
            link = invite.invite_link
            await set_invite_link(user_id, link)
        await send_private(user_id, f"✅ Blokdan chiqdingiz. Havola:\n\n{link}")
        await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Blokdan chiqarildi", callback_data="done")]]))
        await callback.answer("✅ Bajarildi")
    except Exception as e: logger.error(f"Unblock xatolik: {e}")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.text)
async def check_text(message: types.Message):
    if await check_bad_words_in_db(message.text):
        await handle_user_penalty(message, reason="So'kinish")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.photo)
async def check_photo(message: types.Message):
    image_bytes = await get_image_bytes(message.photo[-1].file_id)
    if image_bytes and await analyze_image_async(image_bytes):
        await handle_user_penalty(message, reason="Odobsiz rasm")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.video | F.video_note)
async def check_video(message: types.Message):
    thumb = message.video.thumbnail if message.video else message.video_note.thumbnail
    if thumb:
        image_bytes = await get_image_bytes(thumb.file_id)
        if image_bytes and await analyze_image_async(image_bytes):
            await handle_user_penalty(message, reason="Odobsiz video")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.sticker | F.animation)
async def check_media(message: types.Message):
    file_id = None
    if message.animation: file_id = message.animation.file_id
    elif message.sticker and not message.sticker.is_animated: file_id = message.sticker.file_id
    elif message.sticker and message.sticker.thumbnail: file_id = message.sticker.thumbnail.file_id
    if file_id:
        image_bytes = await get_image_bytes(file_id)
        if image_bytes and await analyze_image_async(image_bytes):
            await handle_user_penalty(message, reason="Odobsiz media")

@dp.chat_join_request()
async def on_join_request(update: types.ChatJoinRequest):
    if update.chat.id == MAIN_CHAT_ID:
        # DB dagi BotSetting holatini tekshiramiz
        captcha_active = await is_captcha_enabled_in_db()
        if captcha_active:
            await send_captcha(update.from_user.id, update.from_user.first_name)
        else:
            try:
                await bot.approve_chat_join_request(MAIN_CHAT_ID, update.from_user.id)
                await send_private(update.from_user.id, "✅ Guruhga xush kelibsiz! (Kaptcha tekshiruvi o'chirilgan) 🎉")
            except Exception as e:
                logger.error(f"To'g'ridan-to'g'ri qabul qilishda xatolik: {e}")

async def setup_userbot_handlers():
    @userbot.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def on_captcha_reply(event):
        user_id = event.sender_id
        if user_id not in captcha_pending: return
        if event.text.strip().upper() == captcha_pending[user_id]["code"]:
            captcha_pending[user_id]["task"].cancel()
            del captcha_pending[user_id]
            try:
                await bot.approve_chat_join_request(MAIN_CHAT_ID, user_id)
                await send_private(user_id, "✅ Guruhga xush kelibsiz! 🎉")
            except Exception as e: logger.error(f"Approve xatolik: {e}")
        else:
            captcha_pending[user_id]["task"].cancel()
            del captcha_pending[user_id]
            try: await bot.decline_chat_join_request(MAIN_CHAT_ID, user_id)
            except Exception: pass

# =====================================================================
# 14. DJANGO WEB SERVER
# =====================================================================
async def run_django_web_server():
    import uvicorn
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "__main__")
    asgi_app = get_asgi_application()

    port = int(os.getenv("PORT", 8080))
    logger.info(f"🌍 Django {port}-portda ishga tushmoqda...")

    config = uvicorn.Config(asgi_app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

# =====================================================================
# MAIN
# =====================================================================
async def main():
    global _main_loop
    logger.info("🚀 TIZIM ISHGA TUSHMOQDA...")

    # Global event loopni saqlaymiz (BroadcastMessage.save() uchun)
    _main_loop = asyncio.get_event_loop()

    # 🚀 RAILWAY ISHGA TUSHGANDA JAZZMIN STILLARINI AVTOMATIK YIG'ISH
    from django.core.management import call_command
    await asyncio.to_thread(call_command, 'collectstatic', interactive=False)
    
    # Jadvallarni tekshirish va yaratish
    await fix_missing_tables()
    
    await userbot.start()
    await setup_userbot_handlers()
    logger.info("🤖 BOT VA DJANGO ADMIN TAYYOR!")

    await asyncio.gather(
        dp.start_polling(bot),
        userbot.run_until_disconnected(),
        run_django_web_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
