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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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

# Django ASGI + whitenoise StreamingHttpResponse ogohlantirishini jimlatamiz
# (bot ishiga ta'sir qilmaydi, faqat shovqinli log)
import warnings
warnings.filterwarnings(
    "ignore",
    message="StreamingHttpResponse must consume synchronous iterators",
    category=Warning,
)
logging.getLogger("django.request").setLevel(logging.ERROR)
logging.getLogger("django.server").setLevel(logging.ERROR)

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
            "search_model": ["auth.User", "__main__.BadWord", "__main__.BotAdmin"],
            "show_sidebar":          True,
            "navigation_expanded":   True,
            "hide_apps":             [],
            "hide_models":           [],
            "icons": {
                "auth":                      "fas fa-users-cog",
                "auth.user":                 "fas fa-user-shield",
                "auth.Group":                "fas fa-users",
                "__main__.BotAdmin":         "fas fa-user-cog",
                "__main__.TelegramUser":     "fas fa-users",
                "__main__.BroadcastMessage": "fas fa-paper-plane",
                "__main__.BadWord":          "fas fa-ban",
                "__main__.UserWarning":      "fas fa-exclamation-triangle",
                "__main__.AdminViolation":   "fas fa-user-lock",
                "__main__.BotSetting":       "fas fa-cogs",
                "__main__.GroupRule":        "fas fa-scroll",
                "__main__.GroupMessage":     "fas fa-bullhorn",
            },
            "default_icon_parents":  "fas fa-chevron-circle-right",
            "default_icon_children": "fas fa-circle",
            "order_with_respect_to": [
                "__main__.BotSetting",
                "__main__.BotAdmin",
                "__main__.GroupMessage",
                "__main__.GroupRule",
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
    is_captcha_active      = models.BooleanField("Kaptcha faolmi? / Активна ли каптча?", default=True)
    is_link_active         = models.BooleanField("Havola olish faolmi? / Активна ли кнопка ссылки?", default=True)
    is_join_request_active = models.BooleanField("Arizalarni qabul qilsinmi? / Принимать заявки?", default=True)

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Sozlamasi"
        verbose_name_plural = "⚙ Bot Sozlamalari"

    def __str__(self):
        return "Tizim Sozlamalari"


class BotAdmin(models.Model):
    """Bot adminlari — faqat admin panel orqali qo'shiladi."""
    user_id    = models.BigIntegerField("Telegram ID", unique=True)
    username   = models.CharField("Username (ixtiyoriy)", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi", max_length=150, null=True, blank=True)
    added_at   = models.DateTimeField("Qo'shilgan vaqti", auto_now_add=True)

    def __str__(self):
        return f"{self.first_name or 'Admin'} ({self.user_id})"

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Admini"
        verbose_name_plural = "🤖 Bot Adminlari"


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

    class Meta:
        app_label = '__main__'
        verbose_name = "Xabarnoma yuborish"
        verbose_name_plural = "📢 Hammaga Xabar Yuborish (Rassilka)"


async def _do_broadcast(msg):
    """BroadcastMessage ni barcha foydalanuvchilarga yuboradi."""
    users = await sync_to_async(list)(TelegramUser.objects.all())
    logger.info(f"📢 Rassilka boshlandi. Jami: {len(users)}")
    success, failed = 0, 0
    for u in users:
        try:
            if msg.photo_url:
                await bot.send_photo(chat_id=u.user_id, photo=msg.photo_url, caption=msg.text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=u.user_id, text=msg.text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Rassilka xatolik user {u.user_id}: {e}")
    await sync_to_async(BroadcastMessage.objects.filter(pk=msg.pk).update)(is_sent=True)
    logger.info(f"📢 Rassilka yakunlandi! Muvaffaqiyatli: {success}, Xatolik: {failed}")


async def _do_send_to_group(msg):
    """GroupMessage ni MAIN_CHAT_ID ga yuboradi."""
    try:
        if msg.photo_url:
            sent = await bot.send_photo(
                chat_id=MAIN_CHAT_ID,
                photo=msg.photo_url,
                caption=msg.text,
                parse_mode="HTML"
            )
        else:
            sent = await bot.send_message(
                chat_id=MAIN_CHAT_ID,
                text=msg.text,
                parse_mode="HTML"
            )
        if msg.pin_message:
            try:
                await bot.pin_chat_message(chat_id=MAIN_CHAT_ID, message_id=sent.message_id)
            except Exception as e:
                logger.error(f"Pin xatolik: {e}")
        await sync_to_async(GroupMessage.objects.filter(pk=msg.pk).update)(is_sent=True)
        await send_log(f"📣 <b>Guruhga xabar yuborildi (Admin panel)</b>\n📝 {msg.text[:100]}...")
        logger.info(f"Guruh xabari #{msg.pk} yuborildi.")
    except Exception as e:
        logger.error(f"Guruh xabari xatolik: {e}")


@sync_to_async
def get_active_rules() -> str | None:
    """Faol guruh qoidasini qaytaradi."""
    try:
        rule = GroupRule.objects.filter(is_active=True).order_by('-updated_at').first()
        if rule:
            return f"<b>{rule.title}</b>\n\n{rule.text}"
        return None
    except Exception:
        return None


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


class BannedUser(models.Model):
    user_id    = models.BigIntegerField("Telegram ID", primary_key=True)
    username   = models.CharField("Username", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi", max_length=150, null=True, blank=True)
    reason     = models.CharField("Sabab", max_length=300, null=True, blank=True)
    banned_at  = models.DateTimeField("Ban vaqti", auto_now_add=True)

    def __str__(self):
        return f"{self.first_name or 'User'} ({self.user_id})"

    class Meta:
        app_label = '__main__'
        verbose_name = "Hafli foydalanuvchi"
        verbose_name_plural = "🚨 Hafli Foydalanuvchilar (Permanent Ban)"


class GroupRule(models.Model):
    """Guruh qoidalari — yangi a'zoga lichkaga yuboriladi."""
    title = models.CharField(
        "Sarlavha",
        max_length=200,
        default="Guruh Qoidalari",
        help_text="Masalan: Mafia Habibiti Qoidalari"
    )
    text = models.TextField(
        "Qoidalar matni (HTML qollabquvvatlanadi)",
        help_text="HTML teglar ishlatish mumkin: qalin, kursiv, kod. Har bir qoida yangi qatorda yozing."
    )
    is_active = models.BooleanField("Faolmi?", default=True)
    updated_at = models.DateTimeField("Oxirgi yangilangan", auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        app_label = '__main__'
        verbose_name = "Guruh Qoidasi"
        verbose_name_plural = "Guruh Qoidalari"


class GroupMessage(models.Model):
    """Admin paneldan guruhga togridantoghri xabar yuborish."""
    text = models.TextField(
        "Xabar matni (HTML formatida)",
        help_text="Masalan: E'lon: Bugun kechqurun musobaqa boladi!"
    )
    photo_url = models.URLField(
        "Rasm URL (ixtiyoriy)",
        null=True, blank=True,
        help_text="Rasm bilan yubormoqchi bolsangiz URL qoying"
    )
    pin_message = models.BooleanField(
        "Xabarni pin qilish?",
        default=False,
        help_text="Belgilansa, xabar guruhda pin qilinadi"
    )
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    is_sent    = models.BooleanField("Yuborildimi?", default=False, editable=False)

    def __str__(self):
        return f"Guruh xabari #{self.pk}"

    class Meta:
        app_label = '__main__'
        verbose_name = "Guruhga xabar yuborish"
        verbose_name_plural = "Guruhga Xabar Yuborish"


# =====================================================================
# 5. ADMIN REGISTRATSIYA
# =====================================================================
if not admin.site.is_registered(BotSetting):
    @admin.register(BotSetting)
    class BotSettingAdmin(admin.ModelAdmin):
        list_display  = ('__str__', 'is_captcha_active', 'is_link_active', 'is_join_request_active')
        fieldsets = (
            ("⚙️ Bot Sozlamalari", {
                'fields': ('is_captcha_active', 'is_link_active', 'is_join_request_active'),
                'description': (
                    '<p style="color:#ffd700; font-size:13px;">'
                    '⚙️ Bu yerda botning asosiy funksiyalarini yoqib/o\'chirishingiz mumkin.<br>'
                    '🔐 <b>Kaptcha</b> — Guruhga kirmoqchi bo\'lganlar uchun rasm-kod tekshiruvi.<br>'
                    '🔗 <b>Havola olish</b> — Foydalanuvchilar bot orqali guruhga link ola olishi.<br>'
                    '🚪 <b>Arizalarni qabul qilish</b> — Guruhga qo\'shilish arizalarini avtomatik qabul/rad qilish.'
                    '</p>'
                )
            }),
        )

if not admin.site.is_registered(BotAdmin):
    @admin.register(BotAdmin)
    class BotAdminAdmin(admin.ModelAdmin):
        list_display  = ('user_id', 'username', 'first_name', 'added_at')
        search_fields = ('user_id', 'username', 'first_name')
        ordering      = ('-added_at',)
        readonly_fields = ('added_at',)
        fieldsets = (
            ("🤖 Bot Admini Ma'lumotlari", {
                'fields': ('user_id', 'username', 'first_name'),
                'description': (
                    '<p style="color:#ffd700; font-size:13px;">'
                    '🤖 Bot adminlari — /status komandasi va bot funksiyalarini boshqara oladigan odamlar.<br>'
                    '⚠️ Faqat shu yerdan qo\'shilgan Telegram ID egalari bot admini hisoblanadi.'
                    '</p>'
                )
            }),
            ('Qo\'shilgan vaqti', {'fields': ('added_at',), 'classes': ('collapse',)}),
        )

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
        actions = ['send_broadcast_action']

        def send_broadcast_action(self, request, queryset):
            import threading
            for msg in queryset.filter(is_sent=False):
                def run(m=msg):
                    try:
                        if _main_loop is None:
                            logger.error("❌ Asosiy event loop tayyor emas!")
                            return
                        future = asyncio.run_coroutine_threadsafe(_do_broadcast(m), _main_loop)
                        future.result(timeout=300)
                    except Exception as e:
                        logger.error(f"Broadcast thread xatolik: {e}")
                threading.Thread(target=run, daemon=True).start()
            self.message_user(request, "✅ Rassilka ishga tushirildi!")
        send_broadcast_action.short_description = "📢 Tanlangan xabarlarni yuborish"

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

if not admin.site.is_registered(BannedUser):
    @admin.register(BannedUser)
    class BannedUserAdmin(admin.ModelAdmin):
        list_display  = ('user_id', 'username', 'first_name', 'reason', 'banned_at')
        search_fields = ('user_id', 'username', 'first_name')
        ordering      = ('-banned_at',)
        list_per_page = 25

        def save_model(self, request, obj, form, change):
            super().save_model(request, obj, form, change)
            import threading
            def do_ban(uid=obj.user_id, fname=obj.first_name, reason=obj.reason):
                try:
                    if _main_loop is None:
                        return
                    async def _ban():
                        try:
                            await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=uid)
                            await send_log(
                                f"\U0001f6a8 <b>Hafli user banlandi!</b>\n"
                                f"\U0001f464 {fname or 'User'} — <code>{uid}</code>\n"
                                f"\U0001f4dd Sabab: {reason or 'ko\'rsatilmagan'}"
                            )
                            logger.info(f"Hafli user {uid} darhol banlandi.")
                        except Exception as e:
                            logger.error(f"Darhol ban xatolik: {e}")
                    future = asyncio.run_coroutine_threadsafe(_ban(), _main_loop)
                    future.result(timeout=30)
                except Exception as e:
                    logger.error(f"Ban thread xatolik: {e}")
            threading.Thread(target=do_ban, daemon=True).start()

if not admin.site.is_registered(GroupRule):
    @admin.register(GroupRule)
    class GroupRuleAdmin(admin.ModelAdmin):
        list_display  = ('title', 'is_active', 'updated_at')
        list_editable = ('is_active',)
        ordering      = ('-updated_at',)
        save_on_top   = True

        fieldsets = (
            (None, {
                'fields': ('title', 'text', 'is_active'),
                'description': (
                    '<p style="color:#ffd700; font-size:13px;">'
                    '📜 Bu yerda yozgan qoidalaringiz guruhga yangi kirgan har bir odamga '
                    'lichkasiga avtomatik yuboriladi. HTML formatida yozishingiz mumkin.'
                    '</p>'
                )
            }),
        )

if not admin.site.is_registered(GroupMessage):
    @admin.register(GroupMessage)
    class GroupMessageAdmin(admin.ModelAdmin):
        list_display  = ('__str__', 'pin_message', 'is_sent', 'created_at')
        readonly_fields = ('is_sent', 'created_at')
        ordering      = ('-created_at',)
        save_on_top   = True
        actions       = ['send_to_group_action']

        fieldsets = (
            (None, {
                'fields': ('text', 'photo_url', 'pin_message'),
                'description': (
                    '<p style="color:#ffd700; font-size:13px;">'
                    '📣 Xabar yozing va "Guruhga yuborish" tugmasini bosing. '
                    'Xabar to\'g\'ridan-to\'g\'ri guruhga yuboriladi.'
                    '</p>'
                )
            }),
            ('Holat', {
                'fields': ('is_sent', 'created_at'),
                'classes': ('collapse',)
            }),
        )

        def send_to_group_action(self, request, queryset):
            import threading
            for msg in queryset.filter(is_sent=False):
                def run(m=msg):
                    try:
                        if _main_loop is None:
                            logger.error("Event loop tayyor emas!")
                            return
                        future = asyncio.run_coroutine_threadsafe(
                            _do_send_to_group(m), _main_loop
                        )
                        future.result(timeout=60)
                    except Exception as e:
                        logger.error(f"GroupMessage thread xatolik: {e}")
                threading.Thread(target=run, daemon=True).start()
            self.message_user(request, "✅ Xabar guruhga yuborilmoqda!")
        send_to_group_action.short_description = "📣 Tanlangan xabarlarni guruhga yuborish"

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
                        logger.info(f"Jadval yaratildi: {table_name}")
                    except Exception as e:
                        logger.error(f"Jadval yaratishda xatolik ({model.__name__}): {e}")
                else:
                    # Jadval mavjud -- lekin yangi ustunlar bo'lishi mumkin, tekshir
                    try:
                        existing_columns = {
                            col.name
                            for col in connection.introspection.get_table_description(
                                connection.cursor(), table_name
                            )
                        }
                        for field in model._meta.local_fields:
                            col_name = field.column
                            if col_name not in existing_columns:
                                schema_editor.add_field(model, field)
                                logger.info(f"Yangi ustun qo'shildi: {table_name}.{col_name}")
                    except Exception as e:
                        logger.error(f"Ustun qo'shishda xatolik ({model.__name__}): {e}")
    except Exception as e:
        logger.error(f"Schema editor xatolik: {e}")

    # 3. Defolt bot sozlamasini yaratish
    try:
        if not BotSetting.objects.exists():
            BotSetting.objects.create(is_captcha_active=True, is_link_active=True, is_join_request_active=True)
            logger.info("Standart bot sozlamalari yaratildi.")
        else:
            # Mavjud yozuvda is_link_active None bo'lishi mumkin -- True ga o'rnat
            BotSetting.objects.filter(is_link_active__isnull=True).update(is_link_active=True)
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
def is_link_enabled_in_db() -> bool:
    try:
        setting = BotSetting.objects.first()
        return setting.is_link_active if setting else True
    except Exception:
        return True

@sync_to_async
def is_join_request_enabled_in_db() -> bool:
    try:
        setting = BotSetting.objects.first()
        return setting.is_join_request_active if setting else True
    except Exception:
        return True

@sync_to_async
def is_bot_admin(user_id: int) -> bool:
    try:
        return BotAdmin.objects.filter(user_id=user_id).exists()
    except Exception:
        return False

@sync_to_async
def get_bot_settings_status():
    try:
        setting = BotSetting.objects.first()
        if not setting:
            return {"captcha": True, "link": True}
        return {
            "captcha":       setting.is_captcha_active,
            "link":          setting.is_link_active,
            "join_request":  setting.is_join_request_active,
        }
    except Exception:
        return {"captcha": True, "link": True}

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

@sync_to_async
def is_permanently_banned(user_id: int) -> bool:
    return BannedUser.objects.filter(user_id=user_id).exists()

# =====================================================================
# 9. BOT INSTANCELARI
# =====================================================================
openai_client = OpenAI(api_key=OPENAI_API_KEY)
bot     = Bot(token=TELEGRAM_TOKEN)
log_bot = Bot(token=LOG_BOT_TOKEN)
dp      = Dispatcher()

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
    except Exception as e:
        logger.error(f"Shaxsiy xabar yuborib bo'lmadi: {e}")

async def send_log(text: str, user_id: int = None, unblock_button: bool = False, admin_name: str = None):
    """Log kanalga xabar yuboradi. admin_name — kimligini ko'rsatadi."""
    markup = None
    if unblock_button and user_id:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data=f"unblock_{user_id}")
        ]])
    # Admin ismi qo'shiladi
    if admin_name:
        text = text + f"\n👮 <b>Bajardi:</b> {admin_name}"
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
            async with session.get(file_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    return None
                content = await response.read()

        # Har qanday formatni (WebP, TGS thumbnail, GIF kadr, PNG) JPEG ga o'tkazamiz
        try:
            image = Image.open(io.BytesIO(content)).convert("RGB")
        except Exception:
            # GIF bo'lsa birinchi kadrni olamiz
            try:
                gif = Image.open(io.BytesIO(content))
                gif.seek(0)
                image = gif.convert("RGB")
            except Exception as e:
                logger.error(f"Rasm ochib bo'lmadi: {e}")
                return None

        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Rasm yuklashda xatolik (Async): {e}")
        return None


async def get_thumbnail_bytes(message: types.Message) -> bytes | None:
    """
    Har qanday media turidan (photo, video, sticker, animation, video_note)
    tahlil uchun rasm baytlarini qaytaradi.
    Animatsiyali / video stiker uchun thumbnail ishlatiladi.
    """
    try:
        # --- Rasm ---
        if message.photo:
            return await get_image_bytes(message.photo[-1].file_id)

        # --- Video / video_note ---
        if message.video and message.video.thumbnail:
            return await get_image_bytes(message.video.thumbnail.file_id)
        if message.video_note and message.video_note.thumbnail:
            return await get_image_bytes(message.video_note.thumbnail.file_id)

        # --- GIF (animation) ---
        if message.animation:
            # Avval thumbnail sinab ko'r
            if message.animation.thumbnail:
                result = await get_image_bytes(message.animation.thumbnail.file_id)
                if result:
                    return result
            # Thumbnail yo'q bo'lsa to'g'ridan faylni yuklab GIF ning 1-kadrini olamiz
            return await get_image_bytes(message.animation.file_id)

        # --- Stiker (oddiy WebP, animatsiyali TGS, video stiker) ---
        if message.sticker:
            # Video stiker yoki animatsiyali stikerning thumbnail'i bor
            if message.sticker.thumbnail:
                result = await get_image_bytes(message.sticker.thumbnail.file_id)
                if result:
                    return result
            # Oddiy WebP stikerni to'g'ridan yuklaymiz
            if not message.sticker.is_animated and not message.sticker.is_video:
                return await get_image_bytes(message.sticker.file_id)

    except Exception as e:
        logger.error(f"Thumbnail olishda xatolik: {e}")
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
        await bot.send_photo(user_id, captcha_file, caption=f"Salom, {user_name}! 👋\n🤖 Rasm ichidagi kodni yozib yuboring!\n⏳ Vaqt: 60 soniya.")
    except Exception as e: logger.error(f"Captcha yuborishda xatolik: {e}")

# =====================================================================
# 13. AIOGRAM HANDLERS
# =====================================================================

# ─────────────────────────────────────────────────────────────────────
# MODERATSIYA YORDAMCHI FUNKSIYALARI
# ─────────────────────────────────────────────────────────────────────
def mod_buttons(user_id: int, warn_count: int) -> InlineKeyboardMarkup:
    """Foydalanuvchi uchun moderatsiya tugmalari."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"⚠️ Warn ({warn_count}/3)", callback_data=f"mod_warn_{user_id}"),
            InlineKeyboardButton(text="🗑 Warn olib tash",         callback_data=f"mod_unwarn_{user_id}"),
        ],
        [
            InlineKeyboardButton(text="🔇 Mute",   callback_data=f"mod_mute_{user_id}"),
            InlineKeyboardButton(text="🔊 Unmute", callback_data=f"mod_unmute_{user_id}"),
        ],
        [
            InlineKeyboardButton(text="🚫 Ban",    callback_data=f"mod_ban_{user_id}"),
            InlineKeyboardButton(text="✅ Unban",  callback_data=f"mod_unban_{user_id}"),
        ],
        [
            InlineKeyboardButton(text="👑 Admin qil",     callback_data=f"mod_admin_{user_id}"),
            InlineKeyboardButton(text="❌ Admin olib tash", callback_data=f"mod_unadmin_{user_id}"),
        ],
    ])

async def get_target_user(message: types.Message):
    """Reply qilingan xabardan yoki komanda argumentidan user_id va first_name oladi."""
    if message.reply_to_message:
        u = message.reply_to_message.from_user
        return u.id, u.first_name or "Foydalanuvchi"
    # /komanda ID yoki @username formatida
    parts = message.text.split()
    if len(parts) > 1:
        arg = parts[1]
        if arg.isdigit():
            return int(arg), f"ID:{arg}"
        if arg.startswith("@"):
            try:
                chat = await bot.get_chat(arg)
                return chat.id, chat.first_name or arg
            except Exception:
                pass
    return None, None

# ─────────────────────────────────────────────────────────────────────
# /warns — Barcha warn'larni ko'rsatish
# ─────────────────────────────────────────────────────────────────────
@sync_to_async
def get_all_warnings() -> list:
    return list(UserWarning.objects.filter(count__gt=0).order_by('-count').values('user_id', 'count'))

@dp.message(F.text.startswith("/warns"), F.chat.id == MAIN_CHAT_ID)
async def cmd_warns_list(message: types.Message):
    if not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return await message.reply("❌ Faqat adminlar uchun!")

    warnings = await get_all_warnings()
    if not warnings:
        return await message.reply("✅ Hozircha hech kim ogohlantirish olmagan.")

    lines = ["📋 <b>Ogohlantirish jadvali:</b>\n"]
    for i, w in enumerate(warnings, 1):
        lines.append(f"{i}. ID <code>{w['user_id']}</code> — <b>{w['count']}/3</b> ogohlantirish")
    await message.reply("\n".join(lines), parse_mode="HTML")

# ─────────────────────────────────────────────────────────────────────
# /warn — Foydalanuvchini ogohlantirish
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text.startswith("/warn"), F.chat.id == MAIN_CHAT_ID)
async def cmd_warn(message: types.Message):
    if not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return await message.reply("❌ Faqat adminlar uchun!")

    user_id, first_name = await get_target_user(message)
    if not user_id:
        return await message.reply("❗ Reply qiling yoki /warn @username / ID yozing.")

    if await is_admin(MAIN_CHAT_ID, user_id):
        return await message.reply("⚠️ Admin ogohlantirish olmaydi!")

    admin_name = message.from_user.first_name or "Admin"
    count = await get_warning(user_id) + 1
    await set_warning(user_id, count)

    if count >= 3:
        try:
            await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
            await set_warning(user_id, 0)
            await message.reply(
                f"🚫 <b>{first_name}</b> 3/3 ogohlantirish to'ldirib banlandi!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Unban", callback_data=f"mod_unban_{user_id}")
                ]])
            )
            await send_log(
                f"🚫 <b>Ban (warn to'ldi):</b>\n👤 {first_name} — <code>{user_id}</code>",
                user_id=user_id, unblock_button=True, admin_name=admin_name
            )
        except Exception as e:
            await message.reply(f"❌ Ban qilishda xatolik: {e}")
    else:
        await message.reply(
            f"⚠️ <b>{first_name}</b> ogohlantirish oldi: <b>{count}/3</b>",
            parse_mode="HTML",
            reply_markup=mod_buttons(user_id, count)
        )
        await send_log(
            f"⚠️ <b>Warn:</b>\n👤 {first_name} — <code>{user_id}</code>\n📊 {count}/3",
            admin_name=admin_name
        )

# ─────────────────────────────────────────────────────────────────────
# /unwarn — Ogohlantirish olib tashlash
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text.startswith("/unwarn"), F.chat.id == MAIN_CHAT_ID)
async def cmd_unwarn(message: types.Message):
    if not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return await message.reply("❌ Faqat adminlar uchun!")

    user_id, first_name = await get_target_user(message)
    if not user_id:
        return await message.reply("❗ Reply qiling yoki /unwarn @username / ID yozing.")

    count = await get_warning(user_id)
    if count <= 0:
        return await message.reply(f"ℹ️ <b>{first_name}</b> ning ogohlantirishi yo'q.", parse_mode="HTML")

    admin_name = message.from_user.first_name or "Admin"
    new_count = count - 1
    await set_warning(user_id, new_count)
    await message.reply(
        f"✅ <b>{first_name}</b> dan 1 ogohlantirish olib tashlandi. Qoldi: <b>{new_count}/3</b>",
        parse_mode="HTML",
        reply_markup=mod_buttons(user_id, new_count)
    )
    await send_log(
        f"✅ <b>Unwarn:</b>\n👤 {first_name} — <code>{user_id}</code>\n📊 {new_count}/3",
        admin_name=admin_name
    )

# ─────────────────────────────────────────────────────────────────────
# /ban — Ban
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text.startswith("/ban"), F.chat.id == MAIN_CHAT_ID)
async def cmd_ban(message: types.Message):
    if not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return await message.reply("❌ Faqat adminlar uchun!")

    user_id, first_name = await get_target_user(message)
    if not user_id:
        return await message.reply("❗ Reply qiling yoki /ban @username / ID yozing.")

    if await is_admin(MAIN_CHAT_ID, user_id):
        return await message.reply("⛔ Adminni ban qilib bo'lmaydi!")

    admin_name = message.from_user.first_name or "Admin"
    parts = message.text.split(maxsplit=2)
    reason = parts[2] if len(parts) > 2 else (parts[1] if not parts[1].startswith("@") and not parts[1].isdigit() else "Ko'rsatilmagan")
    if message.reply_to_message and len(parts) > 1:
        reason = " ".join(parts[1:])

    try:
        await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
        await set_warning(user_id, 0)
        await message.reply(
            f"🚫 <b>{first_name}</b> banlandi!\n📝 Sabab: {reason}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Unban", callback_data=f"mod_unban_{user_id}")
            ]])
        )
        await send_log(
            f"🚫 <b>Ban:</b>\n👤 {first_name} — <code>{user_id}</code>\n📝 {reason}",
            user_id=user_id, unblock_button=True, admin_name=admin_name
        )
    except Exception as e:
        await message.reply(f"❌ Ban xatolik: {e}")

# ─────────────────────────────────────────────────────────────────────
# /unban — Unban
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text.startswith("/unban"), F.chat.id == MAIN_CHAT_ID)
async def cmd_unban(message: types.Message):
    if not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return await message.reply("❌ Faqat adminlar uchun!")

    user_id, first_name = await get_target_user(message)
    if not user_id:
        return await message.reply("❗ Reply qiling yoki /unban @username / ID yozing.")

    admin_name = message.from_user.first_name or "Admin"
    try:
        # Avval guruhda holat tekshiramiz
        try:
            member = await bot.get_chat_member(MAIN_CHAT_ID, user_id)
            status = member.status
        except Exception:
            status = "kicked"  # Telegram topsa ham, topilmasa ham ban deb faraz qilamiz

        if status not in ("kicked", "restricted", "left"):
            return await message.reply(
                f"ℹ️ <b>{first_name}</b> allaqachon guruhda yoki ban emas.",
                parse_mode="HTML"
            )

        # only_if_banned=False — chunki "left" statusli ban ham bo'lishi mumkin
        try:
            await bot.unban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id, only_if_banned=False)
        except Exception as ue:
            if "PARTICIPANT_ID_INVALID" not in str(ue):
                raise
        await message.reply(f"✅ <b>{first_name}</b> ban olib tashlandi!", parse_mode="HTML")
        await send_log(
            f"✅ <b>Unban:</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )
    except Exception as e:
        await message.reply(f"❌ Unban xatolik: {e}")

# ─────────────────────────────────────────────────────────────────────
# /mute — Mute (xabar yoza olmaydi)
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text.startswith("/mute"), F.chat.id == MAIN_CHAT_ID)
async def cmd_mute(message: types.Message):
    if not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return await message.reply("❌ Faqat adminlar uchun!")

    user_id, first_name = await get_target_user(message)
    if not user_id:
        return await message.reply("❗ Reply qiling yoki /mute @username / ID yozing.")

    if await is_admin(MAIN_CHAT_ID, user_id):
        return await message.reply("⛔ Adminni mute qilib bo'lmaydi!")

    admin_name = message.from_user.first_name or "Admin"
    from aiogram.types import ChatPermissions
    try:
        await bot.restrict_chat_member(
            chat_id=MAIN_CHAT_ID,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await message.reply(
            f"🔇 <b>{first_name}</b> mute qilindi!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔊 Unmute", callback_data=f"mod_unmute_{user_id}")
            ]])
        )
        await send_log(
            f"🔇 <b>Mute:</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )
    except Exception as e:
        await message.reply(f"❌ Mute xatolik: {e}")

# ─────────────────────────────────────────────────────────────────────
# /unmute — Unmute
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text.startswith("/unmute"), F.chat.id == MAIN_CHAT_ID)
async def cmd_unmute(message: types.Message):
    if not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return await message.reply("❌ Faqat adminlar uchun!")

    user_id, first_name = await get_target_user(message)
    if not user_id:
        return await message.reply("❗ Reply qiling yoki /unmute @username / ID yozing.")

    admin_name = message.from_user.first_name or "Admin"
    from aiogram.types import ChatPermissions
    try:
        await bot.restrict_chat_member(
            chat_id=MAIN_CHAT_ID,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )
        await message.reply(f"🔊 <b>{first_name}</b> unmute qilindi!", parse_mode="HTML")
        await send_log(
            f"🔊 <b>Unmute:</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )
    except Exception as e:
        await message.reply(f"❌ Unmute xatolik: {e}")

# ─────────────────────────────────────────────────────────────────────
# /admin — Admin qilish
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text.startswith("/admin"), F.chat.id == MAIN_CHAT_ID)
async def cmd_make_admin(message: types.Message):
    if not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return await message.reply("❌ Faqat adminlar uchun!")

    user_id, first_name = await get_target_user(message)
    if not user_id:
        return await message.reply("❗ Reply qiling yoki /admin @username / ID yozing.")

    admin_name = message.from_user.first_name or "Admin"
    try:
        await bot.promote_chat_member(
            chat_id=MAIN_CHAT_ID,
            user_id=user_id,
            can_delete_messages=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_invite_users=True,
        )
        await message.reply(f"👑 <b>{first_name}</b> admin qilindi!", parse_mode="HTML")
        await send_log(
            f"👑 <b>Admin qilindi:</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )
    except Exception as e:
        await message.reply(f"❌ Admin qilishda xatolik: {e}")

# ─────────────────────────────────────────────────────────────────────
# /unadmin — Admin olib tashlash
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text.startswith("/unadmin"), F.chat.id == MAIN_CHAT_ID)
async def cmd_unadmin(message: types.Message):
    if not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return await message.reply("❌ Faqat adminlar uchun!")

    user_id, first_name = await get_target_user(message)
    if not user_id:
        return await message.reply("❗ Reply qiling yoki /unadmin @username / ID yozing.")

    admin_name = message.from_user.first_name or "Admin"
    try:
        await bot.promote_chat_member(
            chat_id=MAIN_CHAT_ID,
            user_id=user_id,
            can_delete_messages=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_invite_users=False,
            can_manage_chat=False,
        )
        await message.reply(f"❌ <b>{first_name}</b> admin huquqi olib tashlandi!", parse_mode="HTML")
        await send_log(
            f"❌ <b>Unadmin:</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )
    except Exception as e:
        await message.reply(f"❌ Unadmin xatolik: {e}")

# ─────────────────────────────────────────────────────────────────────
# INLINE BUTTON CALLBACK'LAR — mod_* tugmalari
# ─────────────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("mod_"))
async def mod_callback_handler(callback: CallbackQuery):
    """Barcha moderatsiya tugmalarini bitta handler boshqaradi."""
    if not await is_admin(MAIN_CHAT_ID, callback.from_user.id):
        return await callback.answer("❌ Faqat adminlar!", show_alert=True)

    parts = callback.data.split("_")   # ['mod', 'action', 'user_id']
    action  = parts[1]
    user_id = int(parts[2])
    admin_name = callback.from_user.first_name or "Admin"

    try:
        member = await bot.get_chat_member(MAIN_CHAT_ID, user_id)
        first_name = member.user.first_name or f"ID:{user_id}"
    except Exception:
        first_name = f"ID:{user_id}"

    from aiogram.types import ChatPermissions

    if action == "warn":
        if await is_admin(MAIN_CHAT_ID, user_id):
            return await callback.answer("⛔ Adminni warn qilib bo'lmaydi!", show_alert=True)
        count = await get_warning(user_id) + 1
        await set_warning(user_id, count)
        if count >= 3:
            await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
            await set_warning(user_id, 0)
            await callback.message.edit_text(
                f"🚫 <b>{first_name}</b> 3/3 warn — banlandi!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Unban", callback_data=f"mod_unban_{user_id}")
                ]])
            )
            await send_log(
                f"🚫 <b>Ban (warn to'ldi):</b>\n👤 {first_name} — <code>{user_id}</code>",
                user_id=user_id, unblock_button=True, admin_name=admin_name
            )
        else:
            await callback.message.edit_reply_markup(reply_markup=mod_buttons(user_id, count))
            await send_log(
                f"⚠️ <b>Warn (tugma):</b>\n👤 {first_name} — <code>{user_id}</code>\n📊 {count}/3",
                admin_name=admin_name
            )
        await callback.answer(f"⚠️ Warn berildi: {count}/3")

    elif action == "unwarn":
        count = await get_warning(user_id)
        if count <= 0:
            return await callback.answer("ℹ️ Ogohlantirish yo'q.", show_alert=True)
        new_count = count - 1
        await set_warning(user_id, new_count)
        await callback.message.edit_reply_markup(reply_markup=mod_buttons(user_id, new_count))
        await send_log(
            f"✅ <b>Unwarn (tugma):</b>\n👤 {first_name} — <code>{user_id}</code>\n📊 {new_count}/3",
            admin_name=admin_name
        )
        await callback.answer(f"✅ Warn olib tashlandi. Qoldi: {new_count}/3")

    elif action == "mute":
        if await is_admin(MAIN_CHAT_ID, user_id):
            return await callback.answer("⛔ Adminni mute qilib bo'lmaydi!", show_alert=True)
        await bot.restrict_chat_member(
            chat_id=MAIN_CHAT_ID, user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await callback.answer(f"🔇 {first_name} mute qilindi!")
        await send_log(
            f"🔇 <b>Mute (tugma):</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )

    elif action == "unmute":
        await bot.restrict_chat_member(
            chat_id=MAIN_CHAT_ID, user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )
        await callback.answer(f"🔊 {first_name} unmute qilindi!")
        await send_log(
            f"🔊 <b>Unmute (tugma):</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )

    elif action == "ban":
        if await is_admin(MAIN_CHAT_ID, user_id):
            return await callback.answer("⛔ Adminni ban qilib bo'lmaydi!", show_alert=True)
        await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
        await set_warning(user_id, 0)
        await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Unban", callback_data=f"mod_unban_{user_id}")
        ]]))
        await callback.answer(f"🚫 {first_name} banlandi!")
        await send_log(
            f"🚫 <b>Ban (tugma):</b>\n👤 {first_name} — <code>{user_id}</code>",
            user_id=user_id, unblock_button=True, admin_name=admin_name
        )

    elif action == "unban":
        try:
            await bot.unban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id, only_if_banned=False)
        except Exception as unban_err:
            if "PARTICIPANT_ID_INVALID" not in str(unban_err):
                logger.warning(f"Unban (tugma) muammo: {unban_err}")
        try:
            await callback.message.edit_reply_markup(reply_markup=mod_buttons(user_id, 0))
        except Exception:
            pass
        await callback.answer(f"✅ {first_name} unban qilindi!")
        await send_log(
            f"✅ <b>Unban (tugma):</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )

    elif action == "admin":
        await bot.promote_chat_member(
            chat_id=MAIN_CHAT_ID, user_id=user_id,
            can_delete_messages=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_invite_users=True,
        )
        await callback.answer(f"👑 {first_name} admin qilindi!")
        await send_log(
            f"👑 <b>Admin (tugma):</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )

    elif action == "unadmin":
        await bot.promote_chat_member(
            chat_id=MAIN_CHAT_ID, user_id=user_id,
            can_delete_messages=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_invite_users=False,
            can_manage_chat=False,
        )
        await callback.answer(f"❌ {first_name} admin emas!")
        await send_log(
            f"❌ <b>Unadmin (tugma):</b>\n👤 {first_name} — <code>{user_id}</code>",
            admin_name=admin_name
        )

    else:
        await callback.answer("❓ Noma'lum amal.", show_alert=True)

# ─────────────────────────────────────────────────────────────────────

@dp.message(F.text == "/status")
async def cmd_status(message: types.Message):
    """Bot funksiyalari holati — faqat bot adminlari ko'ra oladi."""
    user_id = message.from_user.id

    # Faqat bot admini yoki guruh creator/admin ko'ra oladi
    is_gadmin = await is_bot_admin(user_id)
    is_grpadmin = await is_admin(MAIN_CHAT_ID, user_id)

    if not (is_gadmin or is_grpadmin):
        return  # Jim o'tkazib yubor

    status = await get_bot_settings_status()

    def icon(val): return "✅ Yoqiq" if val else "❌ O'chiq"

    text = (
        "⚙️ <b>Bot Funksiyalari Holati</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Kaptcha tekshiruvi:</b>  {icon(status['captcha'])}\n"
        f"🔗 <b>Havola olish (link):</b> {icon(status['link'])}\n"
        f"🚪 <b>Ariza qabul qilish:</b>   {icon(status['join_request'])}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 Sozlamalarni o'zgartirish uchun:\n"
        "<b>Admin panel → ⚙ Bot Sozlamalari</b>"
    )
    await message.answer(text, parse_mode="HTML")


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

    # Link yoqiq yoki o'chiqligini tekshir
    link_active = await is_link_enabled_in_db()
    if not link_active:
        await callback.answer(
            "🚫 Havola olish hozircha o'chirilgan.\n"
            "Admin bilan bog'laning va link oling.",
            show_alert=True
        )
        return

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
        # only_if_banned=False — guruhda bo'lmagan / left bo'lgan userlarni ham unban qiladi
        try:
            await bot.unban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id, only_if_banned=False)
        except Exception as ue:
            if "PARTICIPANT_ID_INVALID" not in str(ue):
                raise
        link = await get_invite_link(user_id)
        if not link:
            invite = await bot.create_chat_invite_link(chat_id=MAIN_CHAT_ID, member_limit=1)
            link = invite.invite_link
            await set_invite_link(user_id, link)
        await send_private(user_id, f"✅ Blokdan chiqdingiz. Havola:\n\n{link}")
        try:
            await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Blokdan chiqarildi", callback_data="done")
                ]])
            )
        except Exception:
            pass
        await callback.answer("✅ Bajarildi")
    except Exception as e:
        logger.error(f"Unblock xatolik: {e}")
        await callback.answer(f"❌ Xatolik: {e}", show_alert=True)

@dp.message(F.chat.id == MAIN_CHAT_ID, F.text)
async def check_text(message: types.Message):
    # Admin xabarlarini tekshirma
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return
    if await check_bad_words_in_db(message.text):
        await handle_user_penalty(message, reason="So'kinish")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.photo)
async def check_photo(message: types.Message):
    # Admin rasmlarini tekshirma
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return
    image_bytes = await get_thumbnail_bytes(message)
    if image_bytes and await analyze_image_async(image_bytes):
        await handle_user_penalty(message, reason="Odobsiz rasm")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.video | F.video_note)
async def check_video(message: types.Message):
    # Admin videolarini tekshirma
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return
    image_bytes = await get_thumbnail_bytes(message)
    if image_bytes and await analyze_image_async(image_bytes):
        await handle_user_penalty(message, reason="Odobsiz video")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.animation)
async def check_animation(message: types.Message):
    """GIF va animatsiyali xabarlarni tekshiradi."""
    # Admin GIF/animatsiyalarini tekshirma
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return
    image_bytes = await get_thumbnail_bytes(message)
    if image_bytes and await analyze_image_async(image_bytes):
        await handle_user_penalty(message, reason="Odobsiz GIF/animatsiya")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.sticker)
async def check_sticker(message: types.Message):
    """Barcha stiker turlarini (oddiy, animatsiyali, video) tekshiradi."""
    # Admin stikerlarini tekshirma
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return
    image_bytes = await get_thumbnail_bytes(message)
    if image_bytes and await analyze_image_async(image_bytes):
        await handle_user_penalty(message, reason="Odobsiz stiker")

@dp.chat_join_request()
async def on_join_request(update: types.ChatJoinRequest):
    if update.chat.id == MAIN_CHAT_ID:
        # Hafli foydalanuvchi ekanligini tekshir
        if await is_permanently_banned(update.from_user.id):
            try:
                await bot.decline_chat_join_request(MAIN_CHAT_ID, update.from_user.id)
                await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=update.from_user.id)
            except Exception as e:
                logger.error(f"Hafli user join rad etishda xatolik: {e}")
            return

        # Ariza qabul qilish yoqiq/o'chiqligini tekshiramiz
        join_active = await is_join_request_enabled_in_db()
        if not join_active:
            try:
                await bot.decline_chat_join_request(MAIN_CHAT_ID, update.from_user.id)
                await send_private(
                    update.from_user.id,
                    "❌ Guruhga kirish hozircha yopiq.\n"
                    "Admin bilan bog'laning: @samir_axii"
                )
            except Exception as e:
                logger.error(f"Ariza rad etishda xatolik: {e}")
            return

        # DB dagi BotSetting holatini tekshiramiz
        captcha_active = await is_captcha_enabled_in_db()
        if captcha_active:
            await send_captcha(update.from_user.id, update.from_user.first_name)
        else:
            try:
                await bot.approve_chat_join_request(MAIN_CHAT_ID, update.from_user.id)
                await send_private(update.from_user.id, "✅ Guruhga xush kelibsiz! 🎉")
            except Exception as e:
                logger.error(f"To'g'ridan-to'g'ri qabul qilishda xatolik: {e}")


@dp.chat_member()
async def on_chat_member_update(update: types.ChatMemberUpdated):
    """Yangi a'zo kirganida qoida yuboradi va hafli userni qayta ban qiladi."""
    if update.chat.id != MAIN_CHAT_ID:
        return

    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status
    user       = update.new_chat_member.user
    user_id    = user.id

    # ── Yangi a'zo kirdi ──────────────────────────────────────────────
    # "left" yoki "kicked" dan "member" ga o'tish = yangi qo'shildi
    just_joined = (
        old_status in ("left", "kicked") and
        new_status in ("member", "restricted")
    )
    if just_joined:
        rules_text = await get_active_rules()
        if rules_text:
            greeting = (
                f"👋 Salom, <b>{user.first_name}</b>!\n\n"
                f"🎉 <b>Guruhga xush kelibsiz!</b>\n\n"
                f"{rules_text}\n\n"
                f"⚠️ Qoidalarga rioya qilmasangiz, ogohlantirish yoki ban beriladi."
            )
            await send_private(user_id, greeting)
        return  # hafli user tekshiruviga o'tmasin

    # ── Hafli userni qayta ban ─────────────────────────────────────────
    was_banned = old_status in ("kicked", "restricted")
    now_free   = new_status in ("member", "administrator", "creator", "restricted", "left")

    if was_banned and now_free:
        if await is_permanently_banned(user_id):
            try:
                await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
                logger.warning(f"Hafli user {user_id} qayta ban qilindi.")
                await send_log(
                    f"🚨 <b>Hafli user qayta ban!</b>\n"
                    f"👤 {user.first_name} — <code>{user_id}</code>\n"
                    f"⚡ Kimdir unban qildi — bot qayta ban qildi."
                )
            except Exception as e:
                logger.error(f"Hafli user qayta ban xatolik: {e}")


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
    
    logger.info("🤖 BOT VA DJANGO ADMIN TAYYOR!")

    # Restart xabari guruhga
    try:
        await bot.send_message(
            MAIN_CHAT_ID,
            "⚠️ <b>Diqqat!</b> Bot yangilandi va qayta ishga tushdi. Hamma narsa avvalgidek ishlaydi! ✅",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Restart xabari xatolik: {e}")

    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_join_request", "chat_member"]),
        run_django_web_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
