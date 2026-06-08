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
        STATICFILES_DIRS=[
            os.path.join(BASE_DIR, 'static'),   
        ],
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
    is_join_request_active   = models.BooleanField("Arizalarni qabul qilsinmi? / Принимать заявки?", default=True)
    is_subscription_active   = models.BooleanField(
        "Botga /start bosmaganlar yoza olmasinmi? / Блокировать незарегистрированных?",
        default=False,
        help_text="Yoqilsa — botga /start bosmagan foydalanuvchilar guruhda yoza olmaydi."
    )

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Sozlamasi"
        verbose_name_plural = "⚙ Bot Sozlamalari"

    def __str__(self):
        return "Tizim Sozlamalari"


class BotAdmin(models.Model):
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
    user_id = models.BigIntegerField("Telegram ID", primary_key=True)
    username = models.CharField("Username", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi", max_length=150, null=True, blank=True)
    reason = models.CharField("Sabab", max_length=300, null=True, blank=True)
    banned_at = models.DateTimeField("Ban vaqti", auto_now_add=True)

    def __str__(self):
        return f"{self.first_name or 'User'} ({self.user_id})"

    class Meta:
        app_label = '__main__'
        verbose_name = "Hafli foydalanuvchi"
        verbose_name_plural = "🚨 Hafli Foydalanuvchilar (Permanent Ban)"


class GroupRule(models.Model):
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
        list_display  = ('__str__', 'is_captcha_active', 'is_link_active', 'is_join_request_active', 'is_subscription_active')
        fieldsets = (
            ("⚙️ Bot Sozlamalari", {
                'fields': ('is_captcha_active', 'is_link_active', 'is_join_request_active', 'is_subscription_active'),
                'description': (
                    '<p style="color:#ffd700; font-size:13px;">'
                    '⚙️ Bu yerda botning asosiy funksiyalarini yoqib/o\'chirishingiz mumkin.<br>'
                    '🔐 <b>Kaptcha</b> — Guruhga kirmoqchi bo\'lganlar uchun rasm-kod tekshiruvi.<br>'
                    '🔗 <b>Havola olish</b> — Foydalanuvchilar bot orqali guruhga link ola olishi.<br>'
                    '🚪 <b>Arizalarni qabul qilish</b> — Guruhga qo\'shilish arizalarini avtomatik qabul/rad qilish.<br>'
                    '🤖 <b>Bot start tekshiruvi</b> — Botga /start bosmagan foydalanuvchilar guruhda yoza olmaydi.'
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
                                f"🚨 <b>Hafli user banlandi!</b>\n"
                                f"👤 {fname or 'User'} — <code>{uid}</code>\n"
                                f"📝 Sabab: {reason or 'ko\'rsatilmagan'}"
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

    try:
        call_command('migrate', interactive=False)
        logger.info("✅ Migratsiyalar muvaffaqiyatli bajarildi!")
    except Exception as e:
        logger.error(f"Migrate xatolik: {e}")

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

    try:
        if not BotSetting.objects.exists():
            BotSetting.objects.create(is_captcha_active=True, is_link_active=True, is_join_request_active=True, is_subscription_active=False)
            logger.info("Standart bot sozlamalari yaratildi.")
        else:
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
    except Exception: return True

@sync_to_async
def is_link_enabled_in_db() -> bool:
    try:
        setting = BotSetting.objects.first()
        return setting.is_link_active if setting else True
    except Exception: return True

@sync_to_async
def is_join_request_enabled_in_db() -> bool:
    try:
        setting = BotSetting.objects.first()
        return setting.is_join_request_active if setting else True
    except Exception: return True

@sync_to_async
def get_subscription_settings():
    try:
        s = BotSetting.objects.first()
        if not s: return False
        return s.is_subscription_active
    except Exception: return False

@sync_to_async
def user_has_started_bot(user_id: int) -> bool:
    return TelegramUser.objects.filter(user_id=user_id).exists()

@sync_to_async
def is_bot_admin(user_id: int) -> bool:
    try: return BotAdmin.objects.filter(user_id=user_id).exists()
    except Exception: return False

@sync_to_async
def get_bot_settings_status():
    try:
        setting = BotSetting.objects.first()
        if not setting: return {"captcha": True, "link": True}
        return {
            "captcha":       setting.is_captcha_active,
            "link":          setting.is_link_active,
            "join_request":  setting.is_join_request_active,
            "subscription":  setting.is_subscription_active,
        }
    except Exception: return {"captcha": True, "link": True}

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
        if re.search(pattern, text_lower): return True
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
    markup = None
    if unblock_button and user_id:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data=f"unblock_{user_id}")
        ]])
    if admin_name:
        text = text + f"\n👮 <b>Bajardi:</b> {admin_name}"
    try: await bot.send_message(LOG_CHAT_ID, text, reply_markup=markup, parse_mode="HTML")
    except Exception as e: logger.error(f"Log xatolik: {e}")

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
            max_tokens=5,
            temperature=0.0
        )
        return "HA" in response.choices[0].message.content.strip().upper()
    except Exception as e:
        logger.error(f"OpenAI xatolik: {e}")
        return False

async def get_image_bytes(file_id: str) -> bytes | None:
    try:
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file.file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200: return None
                content = await response.read()
                try:
                    image = Image.open(io.BytesIO(content)).convert("RGB")
                except Exception:
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
    try:
        if message.photo:
            return await get_image_bytes(message.photo[-1].file_id)
        if message.video and message.video.thumbnail:
            return await get_image_bytes(message.video.thumbnail.file_id)
        if message.video_note and message.video_note.thumbnail:
            return await get_image_bytes(message.video_note.thumbnail.file_id)
        if message.animation:
            if message.animation.thumbnail:
                result = await get_image_bytes(message.animation.thumbnail.file_id)
                if result: return result
            return await get_image_bytes(message.animation.file_id)
        if message.sticker:
            if message.sticker.thumbnail:
                result = await get_image_bytes(message.sticker.thumbnail.file_id)
                if result: return result
            if not message.sticker.is_animated and not message.sticker.is_video:
                return await get_image_bytes(message.sticker.file_id)
    except Exception as e:
        logger.error(f"Thumbnail olishda xatolik: {e}")
    return None

# =====================================================================
# 11. JAZOLASH MANTIG'I
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
# 12. CAPTCHA TEKSHIRUVI
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
        draw.text((25 + (i * 40), 25), char, fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)), font=font)
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue(), captcha_text

# =====================================================================
# 13. AIOGRAM BOT HANDLERLARI (Barcha Kiruvchi Xabarlar Va Guruh Nazorati)
# =====================================================================

@dp.message(F.chat.type == "private", commands=["start"])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if await is_permanently_banned(user_id):
        await message.reply("Siz ushbu botdan foydalanishdan butunlay cheklangansiz! 🚫")
        return
    await save_user_to_db(user_id, message.from_user.username, message.from_user.first_name)
    await message.reply("⚜ <b>Mafia Habibiti tizimiga xush kelibsiz!</b>\nBot orqali guruh qoidalarini olishingiz va yordam xizmati bilan bog'lanishingiz mumkin.", parse_mode="HTML")

@dp.message(F.chat.type == "private", commands=["help", "rules"])
async def rules_handler(message: types.Message):
    rules = await get_active_rules()
    if rules:
        await message.reply(rules, parse_mode="HTML")
    else:
        await message.reply("Guruh qoidalari hozircha o'rnatilmagan.")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.new_chat_members)
async def new_member_handler(message: types.Message):
    for member in message.new_chat_members:
        user_id = member.id
        if await is_permanently_banned(user_id):
            try: await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
            except Exception: pass
            continue
        
        # Qoidalarni shaxsiy xabarga yuborish
        rules = await get_active_rules()
        if rules:
            await send_private(user_id, f"⚜ <b>Guruhimizga xush kelibsiz!</b>\n\n{rules}")

        if await is_captcha_enabled_in_db():
            captcha_img, captcha_code = create_image_captcha()
            captcha_pending[user_id] = {
                "code": captcha_code,
                "msg_ids": [],
                "attempts": 0
            }
            try:
                # Guruhda ogohlantirish xabari
                warn_msg = await message.reply(f"⚠️ [{member.first_name}](tg://user?id={user_id}) bot emasligingizni tasdiqlang! Tizim sizga shaxsiy xabarda rasm-kod yubordi.", parse_mode="Markdown")
                captcha_pending[user_id]["msg_ids"].append(warn_msg.message_id)
                
                # Lichkaga kaptchani yuborish
                photo_file = types.BufferedInputFile(captcha_img, filename="captcha.jpg")
                cap_msg = await bot.send_photo(chat_id=user_id, photo=photo_file, caption="Rasmdagi kodni kiriting (Katta harflar bilan):")
                
                # Agar foydalanuvchi 120 soniyada javob bermasa avtomatik chiqarib yuborish
                async def captcha_timeout(uid, chat_id):
                    await asyncio.sleep(120)
                    if uid in captcha_pending:
                        try:
                            await bot.ban_chat_member(chat_id=chat_id, user_id=uid)
                            await bot.unban_chat_member(chat_id=chat_id, user_id=uid)
                            await bot.send_message(uid, "Kaptchadan o'tish vaqti tugadi! Qayta urinib ko'ring.")
                        except Exception: pass
                        for mid in captcha_pending[uid]["msg_ids"]:
                            try: await bot.delete_message(chat_id=chat_id, message_id=mid)
                            except Exception: pass
                        captcha_pending.pop(uid, None)
                
                asyncio.create_task(captcha_timeout(user_id, MAIN_CHAT_ID))
            except Exception as e:
                logger.error(f"Kaptcha jo'natish xatosi: {e}")

@dp.message(F.chat.type == "private")
async def private_message_processor(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    
    # Kaptcha kutilayotgan holat
    if user_id in captcha_pending:
        data = captcha_pending[user_id]
        if text and text.strip().upper() == data["code"]:
            await message.reply("✅ Tabriklaymiz, siz kaptcha tekshiruvidan muvaffaqiyatli o'tdingiz va guruhda yozish huquqiga egasiz!")
            for mid in data["msg_ids"]:
                try: await bot.delete_message(chat_id=MAIN_CHAT_ID, message_id=mid)
                except Exception: pass
            captcha_pending.pop(user_id, None)
        else:
            data["attempts"] += 1
            if data["attempts"] >= 3:
                await message.reply("❌ 3 marta xato kiritdingiz. Guruhdan vaqtincha chetlashtirilasiz.")
                try:
                    await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
                    await bot.unban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
                except Exception: pass
                captcha_pending.pop(user_id, None)
            else:
                await message.reply(f"Kod noto'g'ri. Qayta urinib ko'ring! Qolgan urinishlar: {3 - data['attempts']}")
        return

    # Support / Yordam xizmati mantig'i
    if user_id in user_to_support:
        # Qo'llab-quvvatlash xizmatiga yo'naltirish
        await bot.forward_message(chat_id=SUPPORT_CHAT_ID, from_chat_id=user_id, message_id=message.message_id)
        return

    if text and text.startswith("/"):
        # Maxsus /status komandasi faqat bot adminlari uchun
        if text.startswith("/status"):
            if await is_bot_admin(user_id):
                st = await get_bot_settings_status()
                status_txt = (
                    f"⚜ <b>Tizim joriy holati:</b>\n\n"
                    f"🔐 Kaptcha: {'✅ FAOL' if st['captcha'] else '❌ O`CHIK'}\n"
                    f"🔗 Havola berish: {'✅ FAOL' if st['link'] else '❌ O`CHIK'}\n"
                    f"🚪 Arizalar qabuli: {'✅ FAOL' if st['join_request'] else '❌ O`CHIK'}\n"
                    f"🤖 Start tekshiruvi: {'✅ FAOL' if st['subscription'] else '❌ O`CHIK'}"
                )
                await message.reply(status_txt, parse_mode="HTML")
            return

    # Qo'llab-quvvatlash tizimini boshlash tugmasi
    if text == "🆘 Yordam / Поддержка":
        user_to_support[user_id] = True
        await message.reply("Siz yordam xizmati bo'limiga ulandingiz. Muammo yoki savolingizni yozib qoldiring, guruh operatorlari tez orada javob berishadi. Chiqish uchun /exit yozing.")
        await bot.send_message(SUPPORT_CHAT_ID, f"🔔 Yangi murojaat!\nFoydalanuvchi: {message.from_user.full_name}\nID: <code>{user_id}</code>\nUlanish uchun uning ID raqamidan foydalanib xabarga reply qiling.", parse_mode="HTML")
        return

# Support guruhidan kelgan reply xabarlarni userga yetkazish
@dp.message(F.chat.id == SUPPORT_CHAT_ID, F.reply_to_message)
async def support_reply_handler(message: types.Message):
    rep = message.reply_to_message
    # Reply qilingan xabardan user ID sini aniqlash (logika matndan yoki forwarddan)
    uid = None
    if rep.forward_from:
        uid = rep.forward_from.id
    else:
        # Agar matnda ID ko'rsatilgan bo'lsa re orqali aniqlash
        match = re.search(r"ID:\s*(\d+)", rep.text or "")
        if match: uid = int(match.group(1))

    if uid:
        try:
            if message.text:
                await bot.send_message(chat_id=uid, text=f"👮 <b>Operator javobi:</b>\n{message.text}", parse_mode="HTML")
            elif message.photo:
                await bot.send_photo(chat_id=uid, photo=message.photo[-1].file_id, caption="👮 Operator sizga rasm yubordi.")
            await message.react([types.ReactionTypeEmoji(emoji="⚡")])
        except Exception as e:
            await message.reply(f"Xabar foydalanuvchiga yetkazilmadi: {e}")

@dp.message(F.chat.type == "private", commands=["exit"])
async def exit_support(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_to_support:
        user_to_support.pop(user_id, None)
        await message.reply("Siz yordam xizmati suhbatidan chiqdingiz. Tizim odatiy holatda.")
    else:
        await message.reply("Siz hech qanday faol qo'llab-quvvatlash suhbatida emassiz.")

@dp.callback_query(F.data.startswith("unblock_"))
async def unblock_callback_handler(callback: CallbackQuery):
    try:
        user_id = int(callback.data.split("_")[1])
        await bot.unchat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
        await callback.answer("Foydalanuvchi guruhdan muvaffaqiyatli blokdan chiqarildi! ✅")
        await callback.message.edit_text(callback.message.text + "\n\n✅ [BLOKDAN CHIQARILDI]")
    except Exception as e:
        await callback.answer(f"Xatolik yuz berdi: {e}", show_alert=True)

# =====================================================================
# 14. GURUH NAZORATI — TAQIQLANGAN SO'ZLAR, REKLAMA VA OPENAI FILTRI
# =====================================================================
@dp.message(F.chat.id == MAIN_CHAT_ID)
async def main_group_moderator(message: types.Message):
    user_id = message.from_user.id

    # 1. Start tekshiruvi (is_subscription_active bo'lsa)
    if await get_subscription_settings():
        if not await user_has_started_bot(user_id):
            if not await is_admin(MAIN_CHAT_ID, user_id):
                try: await message.delete()
                except Exception: pass
                await send_private(user_id, "⚠️ <b>Diqqat!</b> Guruhda yoza olishingiz uchun avval botimizga kirib /start tugmasini bosishingiz kerak. \n👉 @bot_username")
                return

    # 2. Taqiqlangan so'zlar filtri
    if message.text or message.caption:
        msg_text = message.text or message.caption
        if await check_bad_words_in_db(msg_text):
            await handle_user_penalty(message, "Taqiqlangan haqoratli so'z ishlatildi")
            return

        # 3. Reklama havolalari filtri (Linklar)
        if "http://" in msg_text or "https://" in msg_text or "@" in msg_text or "t.me/" in msg_text:
            if not await is_admin(MAIN_CHAT_ID, user_id):
                await handle_user_penalty(message, "Guruhga reklama yoki havola joylashtirish taqiqlanadi")
                return

    # 4. Multimedia xabarlarini OpenAI yordamida tahlil qilish (Rasmlar, stikerlar va h.k.)
    media_bytes = await get_thumbnail_bytes(message)
    if media_bytes:
        is_nsfw = await analyze_image_async(media_bytes)
        if is_nsfw:
            await handle_user_penalty(message, "Rasm/Media tarkibida odobsiz kontent aniqlandi (AI tahlili)")
            return

# Chat a'zoligi va arizalarni avtomatik boshqarish
@dp.chat_join_request()
async def join_request_handler(update: types.ChatJoinRequest):
    if await is_join_request_enabled_in_db():
        user_id = update.from_user.id
        if await is_permanently_banned(user_id):
            try: await update.decline()
            except Exception: pass
            return
        try:
            await update.approve()
            await send_private(user_id, "Sizning guruhga qo'shilish haqingizdagi arizangiz avtomatik qabul qilindi! Guruhga kirishingiz mumkin. ⚜")
        except Exception as e:
            logger.error(f"Ariza qabul qilishda xatolik: {e}")

# =====================================================================
# 15. DJANGO ASGI ILOVA VA UVICORN INTEGRATSIYASI
# =====================================================================
import uvicorn
from django.core.asgi import get_asgi_application

async def start_django_and_bot():
    global _main_loop
    logger.info("🚀 TIZIM ISHGA TUSHMOQDA...")
    _main_loop = asyncio.get_event_loop()

    # Statik fayllarni yig'ish (Railway muhitida Jazzmin stillari to'g'ri ko'rinishi uchun)
    from django.core.management import call_command
    await asyncio.to_thread(call_command, 'collectstatic', interactive=False)
    
    # Bazani tekshirish va modellarni yaratish
    await fix_missing_tables()
    
    logger.info("🤖 BOT VA DJANGO ADMIN PANEL TAYYOR!")

    try:
        await bot.send_message(
            MAIN_CHAT_ID,
            "⚠️ <b>Diqqat!</b> Bot muvaffaqiyatli yangilandi va qayta ishga tushdi! Hamma narsa normal rejimda ishlamoqda. ✅",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Guruhga restart xabarini yuborib bo'lmadi: {e}")

    # Botni ishga tushirish (Polling)
    asyncio.create_task(dp.start_polling(bot))

    # Django ASGI serverini uvicorn orqali parallel ishga tushirish
    asgi_app = get_asgi_application()
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🌍 Django {port}-portda ishga tushmoqda...")

    config = uvicorn.Config(asgi_app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(start_django_and_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi!")
