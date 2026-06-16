import os
import sys
import io
import re
import html
import base64
import random
import asyncio
import logging
import aiohttp
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from openai import OpenAI
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramRetryAfter
from moderator import MOD
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
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

    )
    django.setup()


# =====================================================================
# 4. MODELLAR
# =====================================================================
class BotSetting(models.Model):
    is_captcha_active      = models.BooleanField("Kaptcha faolmi?", default=True)
    is_link_active         = models.BooleanField("Havola olish faolmi?", default=True)
    is_join_request_active = models.BooleanField("Arizalarni qabul qilsinmi?", default=True)
    is_subscription_active = models.BooleanField(
        "Botga /start bosmaganlar yoza olmasinmi?",
        default=False,
        help_text="Yoqilsa — botga /start bosmagan foydalanuvchilar guruhda yoza olmaydi."
    )
    admin_rules_active = models.BooleanField(
        "Qoidalar adminlarga ham ishlashmi?",
        default=False,
        help_text="Yoqilsa — adminlar ham so'kinish va rasm tekshiruviga uchraydi."
    )
    # ── Welcome ──────────────────────────────────────────────────────
    is_welcome_active = models.BooleanField(
        "Guruhda xush kelibsiz xabari",
        default=True,
        help_text="Yoqilsa — yangi a'zo kirganida guruhda salom xabari yuboriladi."
    )
    welcome_text = models.TextField(
        "Xush kelibsiz matni",
        default="👋 Salom, {name}! Guruhga xush kelibsiz! 🎉\n\nQoidalarga rioya qiling va yaxshi muloqot qiling. 😊",
        help_text="Ishlatish mumkin bo'lgan o'zgaruvchilar: {name} — foydalanuvchi ismi, {username} — username, {count} — a'zolar soni."
    )
    # ── Flood control ─────────────────────────────────────────────────
    is_flood_active = models.BooleanField(
        "Flood nazorati (anti-spam)",
        default=True,
        help_text="Yoqilsa — qisqa vaqtda ko'p xabar yuborganlar mutega olinadi."
    )
    flood_limit = models.PositiveIntegerField(
        "Flood: max xabar soni",
        default=5,
        help_text="Qancha xabar yuborilsa flood deb hisoblansin (default: 5)."
    )
    flood_window = models.PositiveIntegerField(
        "Flood: vaqt oynasi (soniya)",
        default=10,
        help_text="Necha soniya ichida xabarlar sanalsin (default: 10s)."
    )
    flood_mute_seconds = models.PositiveIntegerField(
        "Flood: mute muddati (soniya)",
        default=300,
        help_text="Flood qilganda necha soniya mute qilinsin (default: 300 = 5 daqiqa)."
    )
    # ── Anti-link ─────────────────────────────────────────────────────
    is_anti_link = models.BooleanField(
        "Anti-link (adminlarsiz havola taqiq)",
        default=False,
        help_text="Yoqilsa — faqat adminlar havola yubora oladi, qolganlarga ogohlantirish beriladi."
    )
    # ── Media filter ──────────────────────────────────────────────────
    is_media_filter_active = models.BooleanField(
        "Media filter (rasm/video/stiker taqiq)",
        default=False,
        help_text="Yoqilsa — adminlardan boshqa hech kim media yubora olmaydi."
    )
    # ── Warn limit ────────────────────────────────────────────────────
    warn_limit = models.PositiveIntegerField(
        "Ogohlantirish limiti (ban oldin)",
        default=3,
        help_text="Nechta ogohlantirishdan keyin foydalanuvchi banlansin (default: 3)."
    )
    # ── /sutag (hammani tag qilish) ─────────────────────────────────────
    sutag_admin_only = models.BooleanField(
        "Tag (/sutag): faqat adminlar ishlatsinmi?",
        default=True,
        help_text="Yoqilsa — /sutag ni faqat bot/guruh adminlari ishlata oladi. O'chirilsa — guruhdagi hamma ishlata oladi."
    )

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Sozlamasi"
        verbose_name_plural = "Bot Sozlamalari"

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
        verbose_name_plural = "Bot Adminlari"


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
        verbose_name_plural = "Bot Foydalanuvchilari"


class BroadcastMessage(models.Model):
    text = models.TextField("Xabar matni (HTML formatida yozish mumkin)", help_text="Masalan: <b>Salom</b>")
    photo_url = models.URLField("Rasm URL manzili (ixtiyoriy)", null=True, blank=True, help_text="Rasm bilan yuborish uchun havola qo'ying")
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    is_sent = models.BooleanField("Yuborildimi?", default=False, editable=False)

    class Meta:
        app_label = '__main__'
        verbose_name = "Xabarnoma yuborish"
        verbose_name_plural = "Hammaga Xabar Yuborish (Rassilka)"


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
        verbose_name_plural = "Taqiqlangan so'zlar / Запрещённые слова"


class UserWarning(models.Model):
    user_id = models.BigIntegerField("Foydalanuvchi ID / ID пользователя", primary_key=True)
    count = models.IntegerField("Ogohlantirishlar soni / Кол-во предупреждений", default=0)
    class Meta:
        app_label = '__main__'
        verbose_name = "Foydalanuvchi ogohlantirishi"
        verbose_name_plural = "Ogohlantirishlar / Предупреждения"


class AdminViolation(models.Model):
    user_id = models.BigIntegerField("Admin ID / ID админа", primary_key=True)
    count = models.IntegerField("Qoida buzish soni / Кол-во нарушения", default=0)
    class Meta:
        app_label = '__main__'
        verbose_name = "Admin xatosi"
        verbose_name_plural = "Admin xatolari / Нарушения админов"


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
        verbose_name_plural = "Hafli Foydalanuvchilar (Permanent Ban)"


class BotOwner(models.Model):
    """Bot egasi — bot guruhga qo'shilganida shu odamni avtomatik admin qiladi."""
    user_id    = models.BigIntegerField("Telegram ID", unique=True)
    username   = models.CharField("Username (ixtiyoriy)", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi (ixtiyoriy)", max_length=150, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name or 'Egasi'} ({self.user_id})"

    class Meta:
        app_label = '__main__'
        verbose_name = "Bot Egasi"
        verbose_name_plural = "Bot Egasi (Owner)"


class GroupAdminPromotion(models.Model):
    """Admin paneldan foydalanuvchini guruhda admin qilish."""
    user_id    = models.BigIntegerField("Telegram ID", unique=True)
    username   = models.CharField("Username (ixtiyoriy)", max_length=150, null=True, blank=True)
    first_name = models.CharField("Ismi (ixtiyoriy)", max_length=150, null=True, blank=True)
    promoted_at = models.DateTimeField("Admin qilingan vaqti", auto_now_add=True)
    is_promoted = models.BooleanField("Admin qilinganmi?", default=False, editable=False)

    def __str__(self):
        return f"{self.first_name or 'User'} ({self.user_id})"

    class Meta:
        app_label = '__main__'
        verbose_name = "Guruhda Admin Qilish"
        verbose_name_plural = "Guruhda Admin Qilish"


class BotStats(models.Model):
    """Bot statistikasi — yagona yozuv, avtomatik yangilanadi."""
    total_links_given    = models.IntegerField("Jami havola berildi",        default=0)
    total_captcha_passed = models.IntegerField("Kaptcha muvaffaqiyatli o'tdi", default=0)
    total_blocked        = models.IntegerField("Bot tomonidan blok qilindi",  default=0)

    def __str__(self):
        return "Bot Statistikasi"

    class Meta:
        app_label = '__main__'
        verbose_name = "Statistika"
        verbose_name_plural = "Bot Statistikasi"


class DailyStats(models.Model):
    """Kunlik statistika — har kun avtomatik yig'iladi."""
    date            = models.DateField("Sana", unique=True)
    warns_given     = models.IntegerField("Berilgan warnlar",        default=0)
    bans_given      = models.IntegerField("Berilgan banlar",         default=0)
    links_given     = models.IntegerField("Berilgan havolalar",      default=0)
    new_members     = models.IntegerField("Yangi a'zolar",           default=0)
    admin_violations= models.IntegerField("Admin qoida buzishlari",  default=0)
    messages_count  = models.IntegerField("Xabarlar soni",           default=0)

    def __str__(self):
        return f"Statistika: {self.date}"

    class Meta:
        app_label = '__main__'
        verbose_name = "Kunlik Statistika"
        verbose_name_plural = "Kunlik Statistika"
        ordering = ['-date']


class GroupActivity(models.Model):
    """Guruhda faol bo'lgan a'zolar — xabar yozgan kunlar."""
    user_id     = models.BigIntegerField("Foydalanuvchi ID")
    first_name  = models.CharField("Ismi", max_length=150, null=True, blank=True)
    username    = models.CharField("Username", max_length=150, null=True, blank=True)
    date        = models.DateField("Sana")
    msg_count   = models.IntegerField("Xabarlar soni", default=1)

    class Meta:
        app_label = '__main__'
        verbose_name = "Guruh Faolligi"
        verbose_name_plural = "Guruh Faolligi"
        unique_together = ('user_id', 'date')
        ordering = ['-date', '-msg_count']

    def __str__(self):
        return f"{self.first_name or self.user_id} — {self.date}"


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


class ScheduledMessage(models.Model):
    """Rejalashtirilgan xabarlar — belgilangan vaqtda guruhga yuboriladi."""
    REPEAT_CHOICES = [
        ('once',   'Bir marta'),
        ('hourly', 'Har soat'),
        ('daily',  'Har kuni'),
        ('weekly', 'Har hafta'),
    ]
    title      = models.CharField("Sarlavha", max_length=200)
    text       = models.TextField("Xabar matni (HTML qo'llab-quvvatlanadi)")
    send_at    = models.DateTimeField(
        "Yuborish vaqti (UTC)",
        help_text="Birinchi yuborish vaqtini belgilang."
    )
    repeat     = models.CharField("Takrorlash", max_length=10, choices=REPEAT_CHOICES, default='once')
    is_active  = models.BooleanField("Faolmi?", default=True)
    last_sent  = models.DateTimeField("Oxirgi yuborildi", null=True, blank=True)
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        app_label = '__main__'
        verbose_name = "Rejalashtirilgan Xabar"
        verbose_name_plural = "Rejalashtirilgan Xabarlar"
        ordering = ['send_at']

    def __str__(self):
        return f"{self.title} → {self.send_at.strftime('%d.%m.%Y %H:%M')}"


class BotNote(models.Model):
    """Eslatmalar — /note save bilan saqlash, #kalit bilan chaqirish."""
    keyword    = models.CharField(
        "Kalit so'z", max_length=100, unique=True,
        help_text="Masalan: qoidalar, admin, link"
    )
    text       = models.TextField(
        "Eslatma matni",
        help_text="HTML teglari: <b>, <i>, <code>, <a href=...>"
    )
    created_by = models.BigIntegerField("Kim qo'shgan (ID)", null=True, blank=True)
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    class Meta:
        app_label = '__main__'
        verbose_name = "Eslatma (Note)"
        verbose_name_plural = "Eslatmalar (Notes)"
        ordering = ['keyword']

    def __str__(self):
        return f"#{self.keyword}"


# =====================================================================
# 5. ADMIN REGISTRATSIYA
# =====================================================================

# ── Custom AdminSite: Dashboard context ──────────────────────────────
from django.contrib.admin import AdminSite as _BaseAdminSite
from django.utils.timezone import now as _tz_now

def _build_dashboard_context(request):
    """Dashboard uchun DB dan statistika yig'adi."""
    from datetime import date, timedelta
    today = date.today()
    week_ago = today - timedelta(days=6)

    # ── Stat cards ───────────────────────────────────────────────────
    try:
        users_count    = TelegramUser.objects.count()
        new_today      = TelegramUser.objects.filter(
            joined_at__date=today
        ).count() if hasattr(TelegramUser, 'joined_at') else 0
        total_warns    = UserWarning.objects.count()
        daily_warns    = DailyStats.objects.filter(
            date=today
        ).aggregate(s=models.Sum('warns_count'))['s'] or 0
        banned_count   = BannedUser.objects.count()
        daily_messages = DailyStats.objects.filter(
            date=today
        ).aggregate(s=models.Sum('messages_count'))['s'] or 0
    except Exception:
        users_count = total_warns = banned_count = daily_messages = 0
        new_today = daily_warns = 0

    # ── Weekly bar chart ─────────────────────────────────────────────
    day_labels = ['Du','Se','Ch','Pa','Ju','Sh','Ya']
    bar_colors = ['#7C3AED','#06B6D4','#F97316','#10b981',
                  '#7C3AED','#06B6D4','#F97316']
    try:
        chart_days_data = []
        stats_by_date = {
            s.date: s for s in
            DailyStats.objects.filter(date__gte=week_ago, date__lte=today)
        }
        vals = []
        for i in range(7):
            d = week_ago + timedelta(days=i)
            s = stats_by_date.get(d)
            v = (s.messages_count or 0) if s else 0
            vals.append(v)
        max_v = max(vals) if any(vals) else 1
        for i, (v, lbl, clr) in enumerate(zip(vals, day_labels, bar_colors)):
            pct = round((v / max_v) * 100)
            chart_days_data.append({
                'label': lbl,
                'val':   v,
                'pct':   max(pct, 3),
                'color': clr,
            })
        chart_y = [str(round(max_v * p / 100)) for p in [100, 75, 50, 25, 0]]
    except Exception:
        chart_days_data = [
            {'label': d, 'val': 0, 'pct': 5, 'color': bar_colors[i]}
            for i, d in enumerate(day_labels)
        ]
        chart_y = ['100','75','50','25','0']

    # ── Top admins ───────────────────────────────────────────────────
    ava_colors = [
        ('#7C3AED', 'rgba(124,58,237,0.25)','rgba(124,58,237,0.2)'),
        ('#06B6D4', 'rgba(6,182,212,0.2)',  'rgba(6,182,212,0.15)'),
        ('#F97316', 'rgba(249,115,22,0.2)', 'rgba(249,115,22,0.15)'),
        ('#10b981', 'rgba(16,185,129,0.2)', 'rgba(16,185,129,0.14)'),
    ]
    try:
        admins_qs = BotAdmin.objects.all()[:4]
        top_admins = []
        for i, adm in enumerate(admins_qs):
            clr, bg, bbg = ava_colors[i % len(ava_colors)]
            name = (adm.first_name or str(adm.user_id))
            initials = ''.join(p[0].upper() for p in name.split()[:2]) or 'A'
            top_admins.append({
                'name':         name,
                'initials':     initials[:2],
                'color':        clr,
                'bg':           bg,
                'badge_bg':     bbg,
                'action_count': 0,
                'role':         'Egasi' if i == 0 else 'Admin',
            })
    except Exception:
        top_admins = []

    # ── Recent actions ───────────────────────────────────────────────
    try:
        recent_warnings = list(
            UserWarning.objects.order_by('-id').select_related()[:4]
        )
        recent_actions = []
        for w in recent_warnings:
            count = w.warning_count if hasattr(w, 'warning_count') else '?'
            recent_actions.append({
                'user_id':  w.user_id,
                'username': getattr(w, 'username', None),
                'action':   f'Warn ×{count}',
                'type':     'warn',
            })
        banned_list = list(BannedUser.objects.order_by('-id')[:2])
        for b in banned_list:
            recent_actions.append({
                'user_id':  b.user_id,
                'username': getattr(b, 'username', None),
                'action':   'Ban',
                'type':     'ban',
            })
        recent_actions = recent_actions[:6]
    except Exception:
        recent_actions = []

    # ── Donut taqsimoti ──────────────────────────────────────────────
    CIRC = 289  # 2πr = 2 * π * 46 ≈ 289
    try:
        mute_n  = 0  # mute log yo'q — kelajakda qo'shiladi
        warn_n  = total_warns
        ban_n   = banned_count
        other_n = max(0, users_count // 10)
        total_d = mute_n + warn_n + ban_n + other_n or 1
        def _dash(n):
            arc = round((n / total_d) * CIRC)
            return arc, CIRC - arc
        md, mg = _dash(mute_n)
        wd, wg = _dash(warn_n)
        bd, bg = _dash(ban_n)
        od, og = _dash(other_n)
        pct = lambda n: round(n / total_d * 100)
        # offsets (cumulative negative)
        wo = -(md)
        bo = -(md + wd)
        oo = -(md + wd + bd)
        donut = {
            'total':        total_d,
            'mute':  mute_n, 'mute_pct':  pct(mute_n),
            'warn':  warn_n, 'warn_pct':  pct(warn_n),
            'ban':   ban_n,  'ban_pct':   pct(ban_n),
            'other': other_n,'other_pct': pct(other_n),
            'mute_dash':  md, 'mute_gap':  mg,
            'warn_dash':  wd, 'warn_gap':  wg, 'warn_offset':  wo,
            'ban_dash':   bd, 'ban_gap':   bg, 'ban_offset':   bo,
            'other_dash': od, 'other_gap': og, 'other_offset': oo,
        }
    except Exception:
        donut = {
            'total':0,'mute':0,'warn':0,'ban':0,'other':0,
            'mute_pct':0,'warn_pct':0,'ban_pct':0,'other_pct':0,
            'mute_dash':0,'mute_gap':289,
            'warn_dash':0,'warn_gap':289,'warn_offset':0,
            'ban_dash':0,'ban_gap':289,'ban_offset':0,
            'other_dash':0,'other_gap':289,'other_offset':0,
        }

    # ── Recent events ────────────────────────────────────────────────
    try:
        events = []
        for w in UserWarning.objects.order_by('-id')[:3]:
            events.append({
                'icon':       'ti ti-alert-triangle',
                'icon_bg':    'rgba(249,115,22,0.15)',
                'icon_color': '#fb923c',
                'action':     f'@{getattr(w,"username","user")} — ogohlantirish',
                'meta':       'Habibti guruhi',
                'time':       'Az oldin',
            })
        for b in BannedUser.objects.order_by('-id')[:1]:
            events.append({
                'icon':       'ti ti-ban',
                'icon_bg':    'rgba(239,68,68,0.15)',
                'icon_color': '#f87171',
                'action':     f'@{getattr(b,"username","user")} — ban',
                'meta':       'Habibti guruhi',
                'time':       'Az oldin',
            })
        if not events:
            events = [{
                'icon': 'ti ti-check', 'icon_bg': 'rgba(16,185,129,0.15)',
                'icon_color': '#34d399',
                'action': 'Tizim ishlayapti', 'meta': 'Barcha xizmatlar normal',
                'time': 'Hozir',
            }]
        events = events[:3]
    except Exception:
        events = []

    return {
        'stats': {
            'users':          users_count,
            'new_today':      new_today,
            'total_warns':    total_warns,
            'daily_warns':    daily_warns,
            'banned':         banned_count,
            'ban_trend':      'down',
            'daily_messages': daily_messages,
        },
        'chart': {
            'days':     chart_days_data,
            'y_labels': chart_y,
        },
        'top_admins':     top_admins,
        'recent_actions': recent_actions,
        'donut':          donut,
        'recent_events':  events,
    }


# Patch AdminSite.index to inject dashboard context
_orig_index = admin.site.__class__.index

def _custom_index(self, request, extra_context=None):
    try:
        ctx = _build_dashboard_context(request)
    except Exception as e:
        logger.error(f"Dashboard context xatolik: {e}")
        ctx = {}
    extra_context = extra_context or {}
    extra_context.update(ctx)
    return _orig_index(self, request, extra_context=extra_context)

admin.site.__class__.index = _custom_index


if not admin.site.is_registered(BotSetting):
    @admin.register(BotSetting)
    class BotSettingAdmin(admin.ModelAdmin):
        list_display = ('__str__', 'is_captcha_active', 'is_anti_link', 'is_flood_active',
                        'is_welcome_active', 'is_media_filter_active', 'warn_limit', 'sutag_admin_only')
        fieldsets = (
            ("⚙️ Asosiy Sozlamalar", {
                'fields': ('is_captcha_active', 'is_link_active', 'is_join_request_active',
                           'is_subscription_active', 'admin_rules_active'),
            }),
            ("👋 Xush Kelibsiz Xabari", {
                'fields': ('is_welcome_active', 'welcome_text'),
            }),
            ("🛡 Flood Nazorati (Anti-Spam)", {
                'fields': ('is_flood_active', 'flood_limit', 'flood_window', 'flood_mute_seconds'),
            }),
            ("🔗 Anti-Link & Media Filter", {
                'fields': ('is_anti_link', 'is_media_filter_active'),
            }),
            ("⚠️ Ogohlantirish Tizimi", {
                'fields': ('warn_limit',),
            }),
            ("🏷 Hammani Tag Qilish (/sutag)", {
                'fields': ('sutag_admin_only',),
                'description': (
                    '<p style="color:#ffd700; font-size:13px;">'
                    '🏷 /sutag — guruhdagi barcha a\'zolarni ismi bilan birma-bir tag qiladi.<br>'
                    '⛔ To\'xtatish: <code>/stutag</code> (har doim adminlarga ruxsat bor).<br>'
                    '✅ Yoqilsa (belgilansa) — faqat adminlar ishlatadi. ❌ O\'chirilsa — guruhdagi hamma ishlata oladi.'
                    '</p>'
                ),
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

if not admin.site.is_registered(BotOwner):
    @admin.register(BotOwner)
    class BotOwnerAdmin(admin.ModelAdmin):
        list_display  = ('user_id', 'username', 'first_name')
        search_fields = ('user_id', 'username', 'first_name')
        fieldsets = (
            ("👑 Bot Egasi Ma'lumotlari", {
                'fields': ('user_id', 'username', 'first_name'),
                'description': (
                    '<p style="color:#ffd700; font-size:13px;">'
                    '👑 <b>Bot Egasi</b> — bot qaysi guruhga qo\'shilmasin, '
                    'avtomatik ravishda botning barcha admin huquqlari beriladi.<br>'
                    '⚠️ Faqat <b>bitta</b> bot egasini qo\'shish tavsiya etiladi.<br>'
                    '📌 Telegram ID ni raqam ko\'rinishida kiriting (masalan: 123456789).<br>'
                    '🔍 ID ni bilish uchun: @userinfobot botga /start yozing.'
                    '</p>'
                )
            }),
        )

        def save_model(self, request, obj, form, change):
            super().save_model(request, obj, form, change)
            self.message_user(
                request,
                f"✅ Bot egasi ({obj.user_id}) saqlandi. "
                "Bot keyingi guruhga qo'shilganida uni avtomatik admin qiladi.",
            )


if not admin.site.is_registered(GroupAdminPromotion):
    @admin.register(GroupAdminPromotion)
    class GroupAdminPromotionAdmin(admin.ModelAdmin):
        list_display   = ('user_id', 'username', 'first_name', 'is_promoted', 'promoted_at')
        search_fields  = ('user_id', 'username', 'first_name')
        ordering       = ('-promoted_at',)
        readonly_fields = ('promoted_at', 'is_promoted')
        fieldsets = (
            ("⭐ Guruhda Admin Qilish", {
                'fields': ('user_id', 'username', 'first_name'),
                'description': (
                    '<p style="color:#ffd700; font-size:13px;">'
                    '⭐ <b>Guruhda Admin Qilish</b> — Telegram ID ni kiriting, '
                    'saqlashingiz bilan bot o\'sha foydalanuvchini MAIN_CHAT_ID guruhida '
                    'barcha admin huquqlari bilan darhol admin qiladi.<br>'
                    '⚠️ Bot guruhda admin bo\'lishi va <b>can_promote_members</b> huquqiga ega bo\'lishi shart.<br>'
                    '📌 Telegram ID ni raqam ko\'rinishida kiriting (masalan: 123456789).<br>'
                    '🔍 ID ni bilish uchun: @userinfobot yoki @RawDataBot ga yozing.'
                    '</p>'
                )
            }),
            ("Ma'lumot", {
                'fields': ('is_promoted', 'promoted_at'),
                'classes': ('collapse',),
            }),
        )

        def save_model(self, request, obj, form, change):
            super().save_model(request, obj, form, change)
            import threading

            def do_promote(uid=obj.user_id, fname=obj.first_name or str(obj.user_id)):
                try:
                    if _main_loop is None:
                        logger.error("❌ Asosiy event loop tayyor emas — promote bajarilmadi!")
                        return

                    async def _promote():
                        try:
                            # Barcha mavjud admin huquqlarini berish
                            await bot.promote_chat_member(
                                chat_id=MAIN_CHAT_ID,
                                user_id=uid,
                                can_manage_chat=True,
                                can_delete_messages=True,
                                can_restrict_members=True,
                                can_promote_members=True,
                                can_change_info=True,
                                can_invite_users=True,
                                can_pin_messages=True,
                                can_manage_video_chats=True,
                            )
                            # is_promoted = True
                            await asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: GroupAdminPromotion.objects.filter(user_id=uid).update(is_promoted=True)
                            )
                            await send_log(
                                f"⭐ <b>Foydalanuvchi guruhda admin qilindi!</b>\n"
                                f"👤 {fname} — <code>{uid}</code>\n"
                                f"✅ Barcha admin huquqlari berildi."
                            )
                            logger.info(f"✅ User {uid} guruhda admin qilindi.")
                        except Exception as e:
                            logger.error(f"❌ Admin qilishda xatolik (ID {uid}): {e}")
                            await send_log(
                                f"⚠️ <b>Admin qilishda xatolik!</b>\n"
                                f"👤 <code>{uid}</code>\n"
                                f"❌ Xato: {e}"
                            )

                    future = asyncio.run_coroutine_threadsafe(_promote(), _main_loop)
                    future.result(timeout=30)
                except Exception as e:
                    logger.error(f"Promote thread xatolik: {e}")

            threading.Thread(target=do_promote, daemon=True).start()
            self.message_user(
                request,
                f"⭐ Foydalanuvchi ({obj.user_id}) admin qilish jarayoni boshlandi. "
                "Log kanaliga natija keladi.",
            )


if not admin.site.is_registered(BotStats):
    @admin.register(BotStats)
    class BotStatsAdmin(admin.ModelAdmin):
        list_display = (
            'get_total_users', 'total_links_given',
            'total_captcha_passed', 'total_blocked',
            'get_total_bans', 'get_total_warns',
        )
        readonly_fields = (
            'total_links_given', 'total_captcha_passed', 'total_blocked',
            'get_total_users', 'get_total_bans', 'get_total_warns',
        )
        fieldsets = (
            ("📈 Statistika (avtomatik)", {
                'fields': (
                    'get_total_users', 'total_links_given',
                    'total_captcha_passed', 'total_blocked',
                    'get_total_bans', 'get_total_warns',
                ),
                'description': (
                    '<p style="color:#ffd700; font-size:13px;">'
                    '📈 Bu sahifa botning umumiy statistikasini ko\'rsatadi.<br>'
                    '♻️ Sahifani yangilash uchun F5 bosing.'
                    '</p>'
                )
            }),
        )

        def get_total_users(self, obj):
            return f"👥 {TelegramUser.objects.count():,} ta"
        get_total_users.short_description = "Jami foydalanuvchi"

        def get_total_bans(self, obj):
            return f"🚫 {BannedUser.objects.count():,} ta"
        get_total_bans.short_description = "Permanent ban"

        def get_total_warns(self, obj):
            from django.db.models import Sum
            total = UserWarning.objects.aggregate(total=Sum('count'))['total'] or 0
            users = UserWarning.objects.filter(count__gt=0).count()
            return f"⚠️ {total} ta ({users} foydalanuvchi)"
        get_total_warns.short_description = "Jami ogohlantirishlar"

        def has_add_permission(self, request):
            return not BotStats.objects.exists()

        def has_delete_permission(self, request, obj=None):
            return False


if not admin.site.is_registered(DailyStats):
    @admin.register(DailyStats)
    class DailyStatsAdmin(admin.ModelAdmin):
        list_display = ('date', 'warns_given', 'bans_given', 'links_given',
                        'new_members', 'admin_violations', 'messages_count')
        readonly_fields = ('date', 'warns_given', 'bans_given', 'links_given',
                           'new_members', 'admin_violations', 'messages_count')
        ordering = ('-date',)
        list_per_page = 30
        date_hierarchy = 'date'

        def has_add_permission(self, request):
            return False

        def has_delete_permission(self, request, obj=None):
            return False

        def changelist_view(self, request, extra_context=None):
            """Grafik bilan statistika sahifasi."""
            import json
            from datetime import date, timedelta

            # Oxirgi 30 kun statistikasi
            today = date.today()
            start = today - timedelta(days=29)
            qs = DailyStats.objects.filter(date__gte=start).order_by('date')

            labels = []
            warns_data = []
            bans_data  = []
            links_data = []
            members_data = []
            violations_data = []

            for row in qs:
                labels.append(row.date.strftime("%d.%m"))
                warns_data.append(row.warns_given)
                bans_data.append(row.bans_given)
                links_data.append(row.links_given)
                members_data.append(row.new_members)
                violations_data.append(row.admin_violations)

            # Umumiy ko'rsatkichlar
            total_warns = sum(warns_data)
            total_bans  = sum(bans_data)
            total_links = sum(links_data)
            total_mem   = sum(members_data)
            total_viol  = sum(violations_data)

            extra_context = extra_context or {}
            extra_context.update({
                'chart_labels':   json.dumps(labels),
                'chart_warns':    json.dumps(warns_data),
                'chart_bans':     json.dumps(bans_data),
                'chart_links':    json.dumps(links_data),
                'chart_members':  json.dumps(members_data),
                'chart_violations': json.dumps(violations_data),
                'total_warns':    total_warns,
                'total_bans':     total_bans,
                'total_links':    total_links,
                'total_members':  total_mem,
                'total_violations': total_viol,
                'stats_title':    'Oxirgi 30 kunlik statistika',
            })
            return super().changelist_view(request, extra_context=extra_context)


if not admin.site.is_registered(GroupActivity):
    @admin.register(GroupActivity)
    class GroupActivityAdmin(admin.ModelAdmin):
        list_display = ('date', 'user_display', 'msg_count')
        readonly_fields = ('user_id', 'first_name', 'username', 'date', 'msg_count')
        list_filter = ('date',)
        search_fields = ('first_name', 'username', 'user_id')
        ordering = ('-date', '-msg_count')
        list_per_page = 50
        date_hierarchy = 'date'

        def user_display(self, obj):
            uname = f" (@{obj.username})" if obj.username else ""
            return f"{obj.first_name or 'Noma\'lum'}{uname} [{obj.user_id}]"
        user_display.short_description = "Foydalanuvchi"

        def has_add_permission(self, request):
            return False

        def has_delete_permission(self, request, obj=None):
            return False

        def changelist_view(self, request, extra_context=None):
            """Guruh faollik grafigi."""
            import json
            from datetime import date, timedelta

            today = date.today()
            start = today - timedelta(days=29)

            # Har kun nechta unique user faol bo'lgan
            from django.db.models import Count as DjCount
            daily_active = (
                GroupActivity.objects
                .filter(date__gte=start)
                .values('date')
                .annotate(active_users=DjCount('user_id', distinct=True),
                          total_msgs=models.Sum('msg_count'))
                .order_by('date')
            )

            labels = []
            active_data = []
            msgs_data   = []
            for row in daily_active:
                labels.append(row['date'].strftime("%d.%m"))
                active_data.append(row['active_users'])
                msgs_data.append(row['total_msgs'] or 0)

            # Top 10 faol foydalanuvchi (oxirgi 30 kun)
            top_users = (
                GroupActivity.objects
                .filter(date__gte=start)
                .values('user_id', 'first_name', 'username')
                .annotate(total=models.Sum('msg_count'))
                .order_by('-total')[:10]
            )

            extra_context = extra_context or {}
            extra_context.update({
                'chart_labels':      json.dumps(labels),
                'chart_active':      json.dumps(active_data),
                'chart_msgs':        json.dumps(msgs_data),
                'top_users':         list(top_users),
                'stats_title':       'Guruh faolligi — Oxirgi 30 kun',
            })
            return super().changelist_view(request, extra_context=extra_context)


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

if not admin.site.is_registered(ScheduledMessage):
    @admin.register(ScheduledMessage)
    class ScheduledMessageAdmin(admin.ModelAdmin):
        list_display  = ('title', 'send_at', 'repeat', 'is_active', 'last_sent')
        list_filter   = ('repeat', 'is_active')
        ordering      = ('send_at',)
        readonly_fields = ('last_sent', 'created_at')
        fieldsets = (
            ("⏰ Rejalashtirilgan Xabar", {
                'fields': ('title', 'text', 'send_at', 'repeat', 'is_active'),
                'description': (
                    '<p style="color:#90ee90;font-size:13px;">'
                    '⏰ Xabar belgilangan vaqtda guruhga avtomatik yuboriladi.<br>'
                    '<b>Takrorlash:</b> Bir marta / Har soat / Har kuni / Har hafta.<br>'
                    '📝 Matnda HTML teglar (<b>, <i>, <code>) ishlatsa bo\'ladi.<br>'
                    '⚠️ Vaqtni UTC da kiriting. O\'zbekiston = UTC+5.'
                    '</p>'
                )
            }),
            ("📊 Holat", {
                'fields': ('last_sent', 'created_at'),
                'classes': ('collapse',)
            }),
        )

if not admin.site.is_registered(BotNote):
    @admin.register(BotNote)
    class BotNoteAdmin(admin.ModelAdmin):
        list_display  = ('keyword', 'text_preview', 'created_by', 'updated_at')
        search_fields = ('keyword', 'text')
        ordering      = ('keyword',)
        readonly_fields = ('created_by', 'created_at', 'updated_at')
        fieldsets = (
            ("📝 Eslatma", {
                'fields': ('keyword', 'text'),
                'description': (
                    '<p style="color:#87ceeb;font-size:13px;">'
                    '📝 Bot buyruqlari:<br>'
                    '• <code>/note save qoidalar [matn]</code> — saqlash<br>'
                    '• <code>#qoidalar</code> yoki <code>/getnote qoidalar</code> — chaqirish<br>'
                    '• <code>/delnote qoidalar</code> — o\'chirish<br>'
                    '• <code>/notes</code> — barcha eslatmalar ro\'yxati'
                    '</p>'
                )
            }),
            ("Ma'lumot", {
                'fields': ('created_by', 'created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        )

        def text_preview(self, obj):
            return obj.text[:60] + "..." if len(obj.text) > 60 else obj.text
        text_preview.short_description = "Matn (qisqa)"

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
            BotSetting.objects.create(is_captcha_active=True, is_link_active=True, is_join_request_active=True, is_subscription_active=False)
            logger.info("Standart bot sozlamalari yaratildi.")
        else:
            # Mavjud yozuvda is_link_active None bo'lishi mumkin -- True ga o'rnat
            BotSetting.objects.filter(is_link_active__isnull=True).update(is_link_active=True)
    except Exception as e:
        logger.error(f"BotSetting yaratishda xatolik: {e}")

    try:
        if not BotStats.objects.exists():
            BotStats.objects.create()
            logger.info("BotStats yozuvi yaratildi.")
    except Exception as e:
        logger.error(f"BotStats yaratishda xatolik: {e}")

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
from django.http import HttpResponse, JsonResponse

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


def stats_api_view(request):
    """API: real-time statistika JSON formatida."""
    from datetime import date, timedelta
    from django.db.models import Sum as DjSum

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    today = date.today()
    week_start = today - timedelta(days=6)
    month_start = today - timedelta(days=29)

    def get_period_stats(start):
        qs = DailyStats.objects.filter(date__gte=start)
        return {
            'warns':      qs.aggregate(t=DjSum('warns_given'))['t'] or 0,
            'bans':       qs.aggregate(t=DjSum('bans_given'))['t'] or 0,
            'links':      qs.aggregate(t=DjSum('links_given'))['t'] or 0,
            'members':    qs.aggregate(t=DjSum('new_members'))['t'] or 0,
            'violations': qs.aggregate(t=DjSum('admin_violations'))['t'] or 0,
            'messages':   qs.aggregate(t=DjSum('messages_count'))['t'] or 0,
        }

    today_stats = DailyStats.objects.filter(date=today).first()

    data = {
        'today': {
            'warns':      getattr(today_stats, 'warns_given', 0),
            'bans':       getattr(today_stats, 'bans_given', 0),
            'links':      getattr(today_stats, 'links_given', 0),
            'members':    getattr(today_stats, 'new_members', 0),
            'violations': getattr(today_stats, 'admin_violations', 0),
            'messages':   getattr(today_stats, 'messages_count', 0),
        },
        'weekly':  get_period_stats(week_start),
        'monthly': get_period_stats(month_start),
        'total': {
            'users': TelegramUser.objects.count(),
            'bans':  BannedUser.objects.count(),
            'warns': UserWarning.objects.aggregate(t=DjSum('count'))['t'] or 0,
        }
    }
    return JsonResponse(data)


urlpatterns = [
    path('', home_view),
    path('admin/', admin.site.urls),
    path('api/stats/', stats_api_view),
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
def get_subscription_settings():
    try:
        s = BotSetting.objects.first()
        if not s:
            return False
        return s.is_subscription_active
    except Exception:
        return False

@sync_to_async
def user_has_started_bot(user_id: int) -> bool:
    """Foydalanuvchi avval /start bosganmi? TelegramUser jadvalida bor/yo'qligini tekshiradi."""
    return TelegramUser.objects.filter(user_id=user_id).exists()

@sync_to_async
def is_bot_admin(user_id: int) -> bool:
    try:
        return BotAdmin.objects.filter(user_id=user_id).exists()
    except Exception:
        return False

@sync_to_async
def get_bot_settings_status():
    try:
        s = BotSetting.objects.first()
        if not s:
            return {
                "captcha": True, "link": True, "join_request": True,
                "subscription": False, "admin_rules": False,
                "welcome": True, "flood": True, "anti_link": False,
                "media_filter": False, "warn_limit": 3,
                "flood_limit": 5, "flood_window": 10, "flood_mute": 300,
                "welcome_text": "👋 Salom, {name}! Guruhga xush kelibsiz! 🎉",
                "sutag_admin_only": True,
            }
        return {
            "captcha":      s.is_captcha_active,
            "link":         s.is_link_active,
            "join_request": s.is_join_request_active,
            "subscription": s.is_subscription_active,
            "admin_rules":  s.admin_rules_active,
            "welcome":      s.is_welcome_active,
            "flood":        s.is_flood_active,
            "anti_link":    s.is_anti_link,
            "media_filter": s.is_media_filter_active,
            "warn_limit":   s.warn_limit,
            "flood_limit":  s.flood_limit,
            "flood_window": s.flood_window,
            "flood_mute":   s.flood_mute_seconds,
            "welcome_text": s.welcome_text,
            "sutag_admin_only": s.sutag_admin_only,
        }
    except Exception:
        return {
            "captcha": True, "link": True, "join_request": True,
            "subscription": False, "admin_rules": False,
            "welcome": True, "flood": True, "anti_link": False,
            "media_filter": False, "warn_limit": 3,
            "flood_limit": 5, "flood_window": 10, "flood_mute": 300,
            "welcome_text": "👋 Salom, {name}! Guruhga xush kelibsiz! 🎉",
            "sutag_admin_only": True,
        }

@sync_to_async
def get_note(keyword: str):
    try:
        return BotNote.objects.get(keyword=keyword.lower().strip())
    except BotNote.DoesNotExist:
        return None

@sync_to_async
def save_note(keyword: str, text: str, user_id: int):
    obj, created = BotNote.objects.update_or_create(
        keyword=keyword.lower().strip(),
        defaults={'text': text, 'created_by': user_id}
    )
    return created  # True = yangi, False = yangilandi

@sync_to_async
def delete_note(keyword: str) -> bool:
    deleted, _ = BotNote.objects.filter(keyword=keyword.lower().strip()).delete()
    return deleted > 0

@sync_to_async
def get_all_notes():
    return list(BotNote.objects.values_list('keyword', flat=True).order_by('keyword'))

@sync_to_async
def get_scheduled_messages_to_send():
    """Hozir yuborilishi kerak bo'lgan faol xabarlarni qaytaradi."""
    now = _tz_now()
    msgs = list(ScheduledMessage.objects.filter(is_active=True, send_at__lte=now))
    return msgs

@sync_to_async
def update_scheduled_after_send(msg_id: int, repeat: str):
    """Xabar yuborilgandan keyin send_at ni yangilaydi yoki o'chiradi."""
    try:
        msg = ScheduledMessage.objects.get(pk=msg_id)
        msg.last_sent = _tz_now()
        if repeat == 'once':
            msg.is_active = False
        elif repeat == 'hourly':
            msg.send_at = msg.send_at + timedelta(hours=1)
        elif repeat == 'daily':
            msg.send_at = msg.send_at + timedelta(days=1)
        elif repeat == 'weekly':
            msg.send_at = msg.send_at + timedelta(weeks=1)
        msg.save()
    except Exception as e:
        logger.error(f"Scheduled update xatolik: {e}")

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


@sync_to_async
def is_admin_rules_active_in_db() -> bool:
    """Adminlarga ham qoidalar ishlaydimi?"""
    try:
        s = BotSetting.objects.first()
        return s.admin_rules_active if s else False
    except Exception:
        return False


@sync_to_async
def get_bot_owner_ids() -> list:
    """Bot egalarining Telegram ID ro'yxatini qaytaradi."""
    try:
        return list(BotOwner.objects.values_list('user_id', flat=True))
    except Exception:
        return []


@sync_to_async
def toggle_bot_setting(field_name: str) -> bool:
    """BotSetting maydonini o'zgartiradi, yangi qiymatni qaytaradi."""
    try:
        setting = BotSetting.objects.first()
        if not setting:
            setting = BotSetting.objects.create()
        current = getattr(setting, field_name, False)
        setattr(setting, field_name, not current)
        setting.save(update_fields=[field_name])
        return not current
    except Exception as e:
        logger.error(f"Toggle setting xatolik ({field_name}): {e}")
        return False


@sync_to_async
def increment_link_stat():
    """Havola berilganda statistikani yangilaydi."""
    try:
        BotStats.objects.get_or_create(pk=1)
        BotStats.objects.filter(pk=1).update(
            total_links_given=models.F('total_links_given') + 1
        )
        from datetime import date
        today = date.today()
        DailyStats.objects.get_or_create(date=today)
        DailyStats.objects.filter(date=today).update(
            links_given=models.F('links_given') + 1
        )
    except Exception:
        pass


@sync_to_async
def increment_captcha_stat():
    """Kaptcha o'tganda statistikani yangilaydi."""
    try:
        BotStats.objects.get_or_create(pk=1)
        BotStats.objects.filter(pk=1).update(
            total_captcha_passed=models.F('total_captcha_passed') + 1
        )
    except Exception:
        pass


@sync_to_async
def increment_blocked_stat():
    """Ban berilganda statistikani yangilaydi."""
    try:
        BotStats.objects.get_or_create(pk=1)
        BotStats.objects.filter(pk=1).update(
            total_blocked=models.F('total_blocked') + 1
        )
        # Kunlik statistikaga ham qo'shamiz
        from datetime import date
        today = date.today()
        DailyStats.objects.get_or_create(date=today)
        DailyStats.objects.filter(date=today).update(
            bans_given=models.F('bans_given') + 1
        )
    except Exception:
        pass


@sync_to_async
def increment_daily_warn():
    """Warn berilganda kunlik statistikani yangilaydi."""
    try:
        from datetime import date
        today = date.today()
        DailyStats.objects.get_or_create(date=today)
        DailyStats.objects.filter(date=today).update(
            warns_given=models.F('warns_given') + 1
        )
    except Exception:
        pass


@sync_to_async
def increment_daily_admin_violation():
    """Admin qoida buzganda kunlik statistikani yangilaydi."""
    try:
        from datetime import date
        today = date.today()
        DailyStats.objects.get_or_create(date=today)
        DailyStats.objects.filter(date=today).update(
            admin_violations=models.F('admin_violations') + 1
        )
    except Exception:
        pass


@sync_to_async
def increment_daily_new_member():
    """Yangi a'zo qo'shilganda kunlik statistikani yangilaydi."""
    try:
        from datetime import date
        today = date.today()
        DailyStats.objects.get_or_create(date=today)
        DailyStats.objects.filter(date=today).update(
            new_members=models.F('new_members') + 1
        )
    except Exception:
        pass


@sync_to_async
def record_group_message(user_id: int, first_name: str, username: str):
    """Guruhda xabar yozilganda faollikni qayd etadi."""
    try:
        from datetime import date
        today = date.today()
        obj, created = GroupActivity.objects.get_or_create(
            user_id=user_id,
            date=today,
            defaults={'first_name': first_name, 'username': username, 'msg_count': 1}
        )
        if not created:
            GroupActivity.objects.filter(user_id=user_id, date=today).update(
                msg_count=models.F('msg_count') + 1,
                first_name=first_name,
                username=username,
            )
        # Kunlik xabarlar sonini ham oshiramiz
        DailyStats.objects.get_or_create(date=today)
        DailyStats.objects.filter(date=today).update(
            messages_count=models.F('messages_count') + 1
        )
    except Exception:
        pass


@sync_to_async
def get_full_stats() -> dict:
    """Bot statistikasini to'liq qaytaradi."""
    try:
        from django.db.models import Sum
        total_users = TelegramUser.objects.count()
        total_bans  = BannedUser.objects.count()
        total_warns = UserWarning.objects.aggregate(total=Sum('count'))['total'] or 0
        users_with_warns = UserWarning.objects.filter(count__gt=0).count()
        stats = BotStats.objects.first()
        total_links    = stats.total_links_given    if stats else 0
        total_captcha  = stats.total_captcha_passed if stats else 0
        total_blocked  = stats.total_blocked        if stats else 0
        return {
            'users':           total_users,
            'bans':            total_bans,
            'warns':           total_warns,
            'users_with_warns': users_with_warns,
            'links':           total_links,
            'captcha':         total_captcha,
            'blocked':         total_blocked,
        }
    except Exception:
        return {'users': 0, 'bans': 0, 'warns': 0,
                'users_with_warns': 0, 'links': 0, 'captcha': 0, 'blocked': 0}


@sync_to_async
def get_group_roster() -> list:
    """
    /sutag uchun: guruhda kamida bir marta yozgan barcha a'zolarning
    ro'yxatini (user_id, eng so'nggi ismi/username) qaytaradi.
    Telegram bot API orqali "guruh a'zolari" ro'yxatini to'liq olishning
    iloji yo'q, shuning uchun GroupActivity jadvali (xabar yozganlar)
    asosida tuzilgan ro'yxat ishlatiladi. Hafli (permanent ban) userlar
    chiqarib tashlanadi.
    """
    try:
        banned_ids = set(BannedUser.objects.values_list('user_id', flat=True))
        roster = {}
        rows = (
            GroupActivity.objects
            .order_by('-date')
            .values('user_id', 'first_name', 'username')
        )
        for r in rows:
            uid = r['user_id']
            if uid in banned_ids or uid in roster:
                continue
            roster[uid] = {
                'user_id': uid,
                'first_name': r['first_name'] or f"ID:{uid}",
                'username': r['username'] or "",
            }
        return list(roster.values())
    except Exception as e:
        logger.error(f"Guruh ro'yxatini olishda xatolik: {e}")
        return []

# =====================================================================
# 9. BOT INSTANCELARI
# =====================================================================
openai_client = OpenAI(api_key=OPENAI_API_KEY)
bot     = Bot(token=TELEGRAM_TOKEN)
log_bot = Bot(token=LOG_BOT_TOKEN) if LOG_BOT_TOKEN else None
dp      = Dispatcher()

captcha_pending  = {}
user_to_support  = {}
support_to_user  = {}
waiting_support  = set()

# Rassilka uchun global event loop (Django thread pool ichidan foydalanish uchun)
_main_loop: asyncio.AbstractEventLoop | None = None

# ── Flood nazorati uchun xotira ───────────────────────────────────────
# { user_id: deque([timestamp1, timestamp2, ...]) }
_flood_tracker: dict[int, deque] = defaultdict(lambda: deque())

# ── /sutag uchun: hozir davom etayotgan tag jarayonlari ────────────────
# { chat_id: {"active": bool, "started_by": user_id} }
_sutag_jobs: dict[int, dict] = {}

# =====================================================================
# 10. YORDAMCHI FUNKSIYALAR
# =====================================================================
async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception: return False


async def check_bot_permission(chat_id: int, permission: str) -> bool:
    """Bot berilgan huquqqa ega yoki yo'qligini tekshiradi.

    permission qiymatlari:
      'can_promote_members'  — admin qilish/olib tashlash
      'can_restrict_members' — ban / mute
      'can_delete_messages'  — xabar o'chirish
      'can_pin_messages'     — pin qilish
    """
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
        if member.status == "creator":
            return True
        if member.status == "administrator":
            return bool(getattr(member, permission, False))
        return False
    except Exception:
        return False

async def send_private(user_id: int, text: str, reply_markup=None):
    try:
        await bot.send_message(user_id, text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Shaxsiy xabar yuborib bo'lmadi: {e}")

async def send_log(text: str, user_id: int = None, unblock_button: bool = False, admin_name: str = None):
    """Log kanalga xabar yuboradi. admin_name — kimligini ko'rsatadi."""
    if not LOG_CHAT_ID:
        return
    markup = None
    if unblock_button and user_id:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data=f"unblock_{user_id}")
        ]])
    if admin_name:
        text = text + f"\n👮 <b>Bajardi:</b> {admin_name}"
    # log_bot mavjud bo'lsa uni ishlatamiz, aks holda asosiy botni
    _sender = log_bot if log_bot else bot
    try:
        await _sender.send_message(LOG_CHAT_ID, text, reply_markup=markup, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Log xatolik: {e}")

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
    await increment_daily_admin_violation()
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
    await increment_daily_warn()
    settings = await get_bot_settings_status()
    warn_limit = settings.get("warn_limit", 3)
    if count >= warn_limit:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await increment_blocked_stat()
            await send_log(
                f"🚫 <b>BAN:</b> {message.from_user.first_name} ({reason})\n"
                f"⚠️ {warn_limit} ta ogohlantirish to'ldi.",
                user_id=user_id, unblock_button=True
            )
            await set_warning(user_id, 0)
        except Exception as e:
            logger.error(f"Ban xatolik: {e}")
    else:
        await send_private(
            user_id,
            f"⚠️ Ogohlantirish: {count}/{warn_limit}. Sabab: {reason}\n"
            f"{'⛔ Keyingisida banlanasiz!' if count == warn_limit - 1 else ''}"
        )

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
        f"🤖 <b>Kaptcha tekshiruvi:</b>    {icon(status['captcha'])}\n"
        f"🔗 <b>Havola olish (link):</b>   {icon(status['link'])}\n"
        f"🚪 <b>Ariza qabul qilish:</b>    {icon(status['join_request'])}\n"
        f"📛 <b>Start tekshiruvi:</b>      {icon(status['subscription'])}\n"
        f"👮 <b>Admin qoidalari:</b>       {icon(status['admin_rules'])}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎛 Tez boshqarish uchun: /panel\n"
        "🛠 To'liq sozlamalar: <b>Admin panel → ⚙ Bot Sozlamalari</b>"
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

@dp.message(F.chat.type == "private", ~F.text.startswith("/"))
async def handle_private_message(message: types.Message):
    user_id = message.from_user.id
    await save_user_to_db(user_id, message.from_user.username, message.from_user.first_name)

    # KAPTCHA TEKSHIRUVI (BUG FIX: avval bu ignore qilingan edi)
    if user_id in captcha_pending:
        if not message.text:
            await message.answer("⚠️ Iltimos, kaptcha kodini <b>matn</b> sifatida yuboring.", parse_mode="HTML")
            return
        expected = captcha_pending[user_id]["code"]
        task      = captcha_pending[user_id]["task"]

        if message.text.strip().upper() == expected:
            # ✅ To'g'ri javob
            task.cancel()
            del captcha_pending[user_id]
            try:
                await bot.approve_chat_join_request(MAIN_CHAT_ID, user_id)
                await message.answer(
                    "✅ <b>Kaptcha muvaffaqiyatli o'tdi!</b>\n"
                    "🎉 Guruhga xush kelibsiz!",
                    parse_mode="HTML"
                )
                await increment_captcha_stat()
            except Exception as e:
                logger.error(f"Join request qabul xatolik: {e}")
                await message.answer("❌ Qo'shishda xatolik yuz berdi. Admin bilan bog'laning.")
        else:
            # ❌ Noto'g'ri javob
            await message.answer(
                "❌ <b>Noto'g'ri kod!</b> Qayta urinib ko'ring.\n"
                "⚠️ Kaptcha rasmiga diqqat bilan qarang.",
                parse_mode="HTML"
            )
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
        log_msg = await bot.send_message(LOG_CHAT_ID, f"🔗 <b>Havola olindi</b>\n👤 {callback.from_user.first_name}\n🆔 <code>{user_id}</code>\n🌐 {invite.invite_link}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_link_{user_id}")]]))
        await set_user_link(user_id, invite.invite_link, log_msg.message_id)
        await increment_link_stat()
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

async def check_subscription(user_id: int) -> bool:
    """Foydalanuvchi botga /start bosganmi? True = start bosgan yoki tekshiruv o'chirilgan."""
    sub_active = await get_subscription_settings()
    if not sub_active:
        return True
    return await user_has_started_bot(user_id)

# =====================================================================
# 13. FLOOD NAZORATI YORDAMCHI FUNKSIYA
# =====================================================================
async def check_flood(message: types.Message) -> bool:
    """
    True qaytarsa — flood aniqlandi, xabar o'chirildi va mute qilindi.
    False qaytarsa — hamma yaxshi.
    """
    settings = await get_bot_settings_status()
    if not settings.get("flood"):
        return False
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        return False

    uid    = message.from_user.id
    now    = time.time()
    limit  = settings.get("flood_limit", 5)
    window = settings.get("flood_window", 10)
    mute_s = settings.get("flood_mute", 300)

    dq = _flood_tracker[uid]
    # Eski timestamp larni tozalaymiz
    while dq and now - dq[0] > window:
        dq.popleft()
    dq.append(now)

    if len(dq) >= limit:
        _flood_tracker.pop(uid, None)   # reset
        try:
            await message.delete()
        except Exception:
            pass
        until = _tz_now() + timedelta(seconds=mute_s)
        try:
            from aiogram.types import ChatPermissions
            await bot.restrict_chat_member(
                chat_id=MAIN_CHAT_ID,
                user_id=uid,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
        except Exception as e:
            logger.error(f"Flood mute xatolik: {e}")
            return False
        mins = mute_s // 60
        try:
            sent = await bot.send_message(
                MAIN_CHAT_ID,
                f"🛡 <b>{message.from_user.first_name}</b>, flood aniqlandi!\n"
                f"⏳ <b>{mins} daqiqa</b> mute qilindi.",
                parse_mode="HTML"
            )
            await asyncio.sleep(15)
            await sent.delete()
        except Exception:
            pass
        await send_log(
            f"🛡 <b>FLOOD:</b> {message.from_user.first_name} "
            f"(<code>{uid}</code>) — {mins} daqiqa mute."
        )
        return True
    return False


# ─────────────────────────────────────────────────────────────────────
# NOTES BUYRUQLARI: /note, /getnote, /delnote, /notes + #kalit
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text.regexp(r'(?s)^/note\s+save\s+(\S+)\s+(.+)$'))
async def cmd_note_save(message: types.Message):
    """Admin: /note save <kalit> <matn>"""
    if not (await is_bot_admin(message.from_user.id) or
            await is_admin(MAIN_CHAT_ID, message.from_user.id)):
        return
    m = re.match(r'^/note\s+save\s+(\S+)\s+(.+)$', message.text, re.DOTALL)
    if not m:
        return
    keyword, text = m.group(1), m.group(2)
    created = await save_note(keyword, text, message.from_user.id)
    action  = "saqlandi ✅" if created else "yangilandi 🔄"
    await message.reply(f"📝 Eslatma <b>#{keyword}</b> {action}", parse_mode="HTML")

@dp.message(F.text.regexp(r'^/getnote\s+(\S+)$'))
async def cmd_note_get(message: types.Message):
    keyword = re.match(r'^/getnote\s+(\S+)$', message.text).group(1)
    note = await get_note(keyword)
    if note:
        await message.reply(note.text, parse_mode="HTML")
    else:
        await message.reply(f"❌ <b>#{keyword}</b> eslatmasi topilmadi.", parse_mode="HTML")

@dp.message(F.text.regexp(r'^#(\w+)$'))
async def cmd_note_hashtag(message: types.Message):
    """Guruhda #kalit yozilsa eslatmani chiqaradi."""
    keyword = re.match(r'^#(\w+)$', message.text).group(1)
    note = await get_note(keyword)
    if note:
        await message.reply(note.text, parse_mode="HTML")

@dp.message(F.text.regexp(r'^/delnote\s+(\S+)$'))
async def cmd_note_del(message: types.Message):
    if not (await is_bot_admin(message.from_user.id) or
            await is_admin(MAIN_CHAT_ID, message.from_user.id)):
        return
    keyword = re.match(r'^/delnote\s+(\S+)$', message.text).group(1)
    ok = await delete_note(keyword)
    if ok:
        await message.reply(f"🗑 <b>#{keyword}</b> o'chirildi.", parse_mode="HTML")
    else:
        await message.reply(f"❌ <b>#{keyword}</b> topilmadi.", parse_mode="HTML")

@dp.message(F.text == "/notes")
async def cmd_notes_list(message: types.Message):
    keywords = await get_all_notes()
    if not keywords:
        await message.reply("📭 Hozircha birorta eslatma yo'q.")
        return
    text = "📝 <b>Barcha eslatmalar:</b>\n\n" + "\n".join(f"• #{k}" for k in keywords)
    await message.reply(text, parse_mode="HTML")


# ─────────────────────────────────────────────────────────────────────
# KENGAYTIRILGAN STATISTIKA: /stats
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text == "/stats")
async def cmd_stats(message: types.Message):
    if not (await is_bot_admin(message.from_user.id) or
            await is_admin(MAIN_CHAT_ID, message.from_user.id)):
        return
    stats = await get_full_stats()
    try:
        chat = await bot.get_chat(MAIN_CHAT_ID)
        member_count = await bot.get_chat_member_count(MAIN_CHAT_ID)
    except Exception:
        chat, member_count = None, "?"

    text = (
        "📊 <b>Kengaytirilgan Statistika</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Guruh a'zolari:</b> {member_count:,}\n"
        f"🤖 <b>Bot foydalanuvchilari:</b> {stats['users']:,}\n\n"
        "📈 <b>Jami ko'rsatkichlar:</b>\n"
        f"  🔗 Havola oldi: <b>{stats['links']:,}</b>\n"
        f"  🤖 Kaptcha o'tdi: <b>{stats['captcha']:,}</b>\n"
        f"  🚫 Ban qilindi: <b>{stats['blocked']:,}</b>\n"
        f"  🔒 Permanent ban: <b>{stats['bans']:,}</b>\n"
        f"  ⚠️ Ogohlantirishlar bor: <b>{stats['users_with_warns']}</b> kishi\n\n"
        "📅 <b>Bugun:</b>\n"
        f"  👋 Yangi a'zo: <b>{stats.get('daily_new_members', 0)}</b>\n"
        f"  ⚠️ Ogohlantirish: <b>{stats.get('daily_warns', 0)}</b>\n"
        f"  🚫 Bloklandi: <b>{stats.get('daily_blocked', 0)}</b>\n"
        f"  👮 Admin qoidabuzarlik: <b>{stats.get('daily_admin', 0)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await message.reply(text, parse_mode="HTML")


@dp.message(F.chat.id == MAIN_CHAT_ID, F.text, ~F.text.startswith("/"))
async def check_text(message: types.Message):
    # Admin xabarlarini tekshirma (agar admin_rules o'chirilgan bo'lsa)
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        if not await is_admin_rules_active_in_db():
            # Baribir faollikni qayd et
            await record_group_message(
                message.from_user.id,
                message.from_user.first_name or "",
                message.from_user.username or ""
            )
            return

    # Bot start tekshiruvi — /start bosmagan bo'lsa yozishni chekla
    if not await check_subscription(message.from_user.id):
        try:
            await message.delete()
        except Exception:
            pass
        bot_info = await bot.get_me()
        bot_link = f"https://t.me/{bot_info.username}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🤖 Botga o'tish", url=bot_link),
        ]])
        sent = await bot.send_message(
            message.chat.id,
            f"⚠️ <b>{message.from_user.first_name}</b>, guruhda yozish uchun\n"
            f"avval botga <b>/start</b> bosing!",
            parse_mode="HTML",
            reply_markup=kb
        )
        # 10 soniyadan so'ng bu xabarni ham o'chiramiz
        await asyncio.sleep(10)
        try:
            await sent.delete()
        except Exception:
            pass
        return

    # Faollikni qayd etamiz
    await record_group_message(
        message.from_user.id,
        message.from_user.first_name or "",
        message.from_user.username or ""
    )

    # Flood nazorati
    if await check_flood(message):
        return

    # Anti-link tekshiruvi
    settings = await get_bot_settings_status()
    if settings.get("anti_link"):
        url_pattern = re.compile(
            r'(https?://\S+|t\.me/\S+|@\w{4,}|www\.\S+)',
            re.IGNORECASE
        )
        if url_pattern.search(message.text):
            await handle_user_penalty(message, reason="Ruxsatsiz havola")
            return

    if await check_bad_words_in_db(message.text):
        await handle_user_penalty(message, reason="So'kinish")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.photo)
async def check_photo(message: types.Message):
    # Admin rasmlarini tekshirma (agar admin_rules o'chirilgan bo'lsa)
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        if not await is_admin_rules_active_in_db():
            return

    # Bot start tekshiruvi — /start bosmagan bo'lsa yozishni chekla
    if not await check_subscription(message.from_user.id):
        try:
            await message.delete()
        except Exception:
            pass
        bot_info = await bot.get_me()
        bot_link = f"https://t.me/{bot_info.username}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🤖 Botga o'tish", url=bot_link),
        ]])
        sent = await bot.send_message(
            message.chat.id,
            f"⚠️ <b>{message.from_user.first_name}</b>, guruhda yozish uchun\n"
            f"avval botga <b>/start</b> bosing!",
            parse_mode="HTML",
            reply_markup=kb
        )
        await asyncio.sleep(10)
        try:
            await sent.delete()
        except Exception:
            pass
        return

    image_bytes = await get_thumbnail_bytes(message)
    if image_bytes and await analyze_image_async(image_bytes):
        await handle_user_penalty(message, reason="Odobsiz rasm")
        return

    # Flood nazorati
    if await check_flood(message):
        return

    # Media filter
    s = await get_bot_settings_status()
    if s.get("media_filter") and not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        await handle_user_penalty(message, reason="Ruxsatsiz media (rasm)")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.video | F.video_note)
async def check_video(message: types.Message):
    # Admin videolarini tekshirma (agar admin_rules o'chirilgan bo'lsa)
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        if not await is_admin_rules_active_in_db():
            return

    # Bot start tekshiruvi — /start bosmagan bo'lsa yozishni chekla
    if not await check_subscription(message.from_user.id):
        try:
            await message.delete()
        except Exception:
            pass
        bot_info = await bot.get_me()
        bot_link = f"https://t.me/{bot_info.username}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🤖 Botga o'tish", url=bot_link),
        ]])
        sent = await bot.send_message(
            message.chat.id,
            f"⚠️ <b>{message.from_user.first_name}</b>, guruhda yozish uchun\n"
            f"avval botga <b>/start</b> bosing!",
            parse_mode="HTML",
            reply_markup=kb
        )
        await asyncio.sleep(10)
        try:
            await sent.delete()
        except Exception:
            pass
        return

    image_bytes = await get_thumbnail_bytes(message)
    if image_bytes and await analyze_image_async(image_bytes):
        await handle_user_penalty(message, reason="Odobsiz video")
        return

    # Flood nazorati
    if await check_flood(message):
        return

    # Media filter
    s = await get_bot_settings_status()
    if s.get("media_filter") and not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        await handle_user_penalty(message, reason="Ruxsatsiz media (video)")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.animation)
async def check_animation(message: types.Message):
    """GIF va animatsiyali xabarlarni tekshiradi."""
    # Admin GIF/animatsiyalarini tekshirma (agar admin_rules o'chirilgan bo'lsa)
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        if not await is_admin_rules_active_in_db():
            return

    # Bot start tekshiruvi — /start bosmagan bo'lsa yozishni chekla
    if not await check_subscription(message.from_user.id):
        try:
            await message.delete()
        except Exception:
            pass
        bot_info = await bot.get_me()
        bot_link = f"https://t.me/{bot_info.username}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="\U0001f916 Botga o'tish", url=bot_link),
        ]])
        sent = await bot.send_message(
            message.chat.id,
            f"\u26a0\ufe0f <b>{message.from_user.first_name}</b>, guruhda yozish uchun\n"
            f"avval botga <b>/start</b> bosing!",
            parse_mode="HTML",
            reply_markup=kb
        )
        await asyncio.sleep(10)
        try:
            await sent.delete()
        except Exception:
            pass
        return

    image_bytes = await get_thumbnail_bytes(message)
    if image_bytes and await analyze_image_async(image_bytes):
        await handle_user_penalty(message, reason="Odobsiz GIF/animatsiya")

@dp.message(F.chat.id == MAIN_CHAT_ID, F.sticker)
async def check_sticker(message: types.Message):
    """Barcha stiker turlarini (oddiy, animatsiyali, video) tekshiradi."""
    # Admin stikerlarini tekshirma (agar admin_rules o'chirilgan bo'lsa)
    if await is_admin(MAIN_CHAT_ID, message.from_user.id):
        if not await is_admin_rules_active_in_db():
            return

    # Bot start tekshiruvi — /start bosmagan bo'lsa yozishni chekla
    if not await check_subscription(message.from_user.id):
        try:
            await message.delete()
        except Exception:
            pass
        bot_info = await bot.get_me()
        bot_link = f"https://t.me/{bot_info.username}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="\U0001f916 Botga o'tish", url=bot_link),
        ]])
        sent = await bot.send_message(
            message.chat.id,
            f"\u26a0\ufe0f <b>{message.from_user.first_name}</b>, guruhda yozish uchun\n"
            f"avval botga <b>/start</b> bosing!",
            parse_mode="HTML",
            reply_markup=kb
        )
        await asyncio.sleep(10)
        try:
            await sent.delete()
        except Exception:
            pass
        return

    image_bytes = await get_thumbnail_bytes(message)
    if image_bytes and await analyze_image_async(image_bytes):
        await handle_user_penalty(message, reason="Odobsiz stiker")
        return

    # Flood nazorati
    if await check_flood(message):
        return

    # Media filter
    s = await get_bot_settings_status()
    if s.get("media_filter") and not await is_admin(MAIN_CHAT_ID, message.from_user.id):
        await handle_user_penalty(message, reason="Ruxsatsiz media (stiker)")

# ─────────────────────────────────────────────────────────────────────
# /id komandasi moderator.py (MOD) orqali boshqariladi


# ─────────────────────────────────────────────────────────────────────
# PANEL YORDAMCHI FUNKSIYA
# ─────────────────────────────────────────────────────────────────────
async def _build_panel(user_id: int):
    """Panel matn va inline tugmalarini qaytaradi."""
    settings = await get_bot_settings_status()
    stats    = await get_full_stats()

    def bi(v): return "🟢" if v else "🔴"
    def tog_btn(code, val, label):
        icon = "✅" if val else "❌"
        return InlineKeyboardButton(text=f"{icon} {label}", callback_data=f"pnl_t_{code}")

    sutag_admin_only = settings.get('sutag_admin_only', True)
    sutag_mode_label  = "👮 Faqat admin" if sutag_admin_only else "👥 Hammaga ochiq"
    sutag_btn = InlineKeyboardButton(
        text=f"🏷 Tag (/sutag): {sutag_mode_label}",
        callback_data="pnl_t_tag"
    )

    text = (
        "🎛 <b>⚜ Mafia Habibiti — Boshqaruv Paneli</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 <b>Statistika:</b>\n"
        f"👥 Foydalanuvchilar: <b>{stats['users']:,}</b>\n"
        f"🔗 Havola oldi: <b>{stats['links']:,}</b>\n"
        f"🤖 Kaptcha o'tdi: <b>{stats['captcha']:,}</b>\n"
        f"🚫 Bot blok qildi: <b>{stats['blocked']:,}</b>\n"
        f"🔒 Permanent ban: <b>{stats['bans']:,}</b>\n"
        f"⚠️ Ogohlantirishlar: <b>{stats['users_with_warns']}</b> ta foydalanuvchi\n\n"
        "⚙️ <b>Asosiy sozlamalar:</b>\n"
        f"{bi(settings['captcha'])} Kaptcha  "
        f"{bi(settings['link'])} Havola  "
        f"{bi(settings['join_request'])} Ariza\n"
        f"{bi(settings['subscription'])} /Start  "
        f"{bi(settings['admin_rules'])} Admin qoidalari\n\n"
        "🛡 <b>Xavfsizlik:</b>\n"
        f"{bi(settings['flood'])} Flood nazorati  "
        f"{bi(settings['anti_link'])} Anti-link\n"
        f"{bi(settings['welcome'])} Xush kelibsiz  "
        f"{bi(settings['media_filter'])} Media filter\n"
        f"⚠️ Warn limiti: <b>{settings.get('warn_limit', 3)}</b> ta\n\n"
        "🏷 <b>Tag (/sutag):</b> ishlatadiganlar — "
        f"<b>{sutag_mode_label}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="pnl_r")],
        [
            tog_btn("cap", settings['captcha'],      "Kaptcha"),
            tog_btn("lnk", settings['link'],         "Havola"),
        ],
        [
            tog_btn("jrq", settings['join_request'], "Ariza"),
            tog_btn("sub", settings['subscription'], "/Start"),
        ],
        [tog_btn("adm", settings['admin_rules'],     "Admin qoidalari")],
        [
            tog_btn("fld", settings['flood'],        "🛡 Flood"),
            tog_btn("alk", settings['anti_link'],    "🔗 Anti-link"),
        ],
        [
            tog_btn("wlc", settings['welcome'],      "👋 Xush kelibsiz"),
            tog_btn("mfl", settings['media_filter'], "🚫 Media filter"),
        ],
        [sutag_btn],
        [
            InlineKeyboardButton(text="👑 Adminlar",         callback_data="pnl_adm"),
            InlineKeyboardButton(text="🚫 Banlar",           callback_data="pnl_ban"),
        ],
        [
            InlineKeyboardButton(text="⚠️ Ogohlantirishlar", callback_data="pnl_wrn"),
            InlineKeyboardButton(text="📜 Qoidalar",         callback_data="pnl_rul"),
        ],
    ])
    return text, markup


# ─────────────────────────────────────────────────────────────────────
# /panel — Telegram admin paneli
# ─────────────────────────────────────────────────────────────────────
@dp.message(F.text == "/panel")
async def cmd_panel(message: types.Message):
    """Bot boshqaruv paneli — bot adminlari va guruh adminlari uchun.
    Guruhda ham, private chatda ham ishlaydi.
    """
    user_id = message.from_user.id
    is_gadmin   = await is_bot_admin(user_id)
    is_grpadmin = await is_admin(MAIN_CHAT_ID, user_id)

    if not (is_gadmin or is_grpadmin):
        # Jim o'tkazib yubor yoki xabar ko'rsatma
        return

    text, markup = await _build_panel(user_id)
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


# ─────────────────────────────────────────────────────────────────────
# PANEL CALLBACKLARI
# ─────────────────────────────────────────────────────────────────────
_FIELD_MAP = {
    "cap": "is_captcha_active",
    "lnk": "is_link_active",
    "jrq": "is_join_request_active",
    "sub": "is_subscription_active",
    "adm": "admin_rules_active",
    "fld": "is_flood_active",
    "alk": "is_anti_link",
    "wlc": "is_welcome_active",
    "mfl": "is_media_filter_active",
    "tag": "sutag_admin_only",
}

@dp.callback_query(F.data.startswith("pnl_"))
async def pnl_callback_handler(callback: CallbackQuery):
    """Panel tugmalarini boshqaradi."""
    user_id = callback.from_user.id
    is_gadmin   = await is_bot_admin(user_id)
    is_grpadmin = await is_admin(MAIN_CHAT_ID, user_id)

    if not (is_gadmin or is_grpadmin):
        return await callback.answer("❌ Ruxsat yo'q!", show_alert=True)

    action = callback.data[4:]  # "pnl_" dan keyingisi

    # ── Yangilash ─────────────────────────────────────────────────────
    if action == "r":
        text, markup = await _build_panel(user_id)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass
        await callback.answer("✅ Yangilandi")

    # ── Sozlamalarni o'zgartirish ─────────────────────────────────────
    elif action.startswith("t_"):
        code = action[2:]
        field = _FIELD_MAP.get(code)
        if not field:
            return await callback.answer("❓ Noma'lum sozlama", show_alert=True)
        new_val = await toggle_bot_setting(field)
        label_map = {
            "cap": "Kaptcha",          "lnk": "Havola",
            "jrq": "Ariza",            "sub": "/Start tekshiruvi",
            "adm": "Admin qoidalari",  "fld": "🛡 Flood nazorati",
            "alk": "🔗 Anti-link",     "wlc": "👋 Xush kelibsiz",
            "mfl": "🚫 Media filter",
        }
        if code == "tag":
            mode_text = "👮 Endi /sutag faqat ADMINLAR uchun" if new_val else "👥 Endi /sutag HAMMAGA ochiq"
            await callback.answer(mode_text, show_alert=True)
        else:
            lbl = label_map.get(code, code)
            await callback.answer(
                f"{'✅ Yoqildi' if new_val else '❌ O\'chirildi'}: {lbl}",
                show_alert=True
            )
        # Panelni yangilash
        text, markup = await _build_panel(user_id)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    # ── Adminlar ro'yxati ─────────────────────────────────────────────
    elif action == "adm":
        try:
            members = await bot.get_chat_administrators(MAIN_CHAT_ID)
            lines = ["👑 <b>Guruh adminlari:</b>\n"]
            for m in members:
                u = m.user
                if u.is_bot:
                    continue
                un = f" @{u.username}" if u.username else ""
                role = "👑 Egasi" if m.status == "creator" else "⭐ Admin"
                lines.append(f"{role} <b>{u.first_name}</b>{un}\n🆔 <code>{u.id}</code>")
            await callback.message.answer(
                "\n".join(lines), parse_mode="HTML"
            )
            await callback.answer()
        except Exception as e:
            await callback.answer(f"❌ Xatolik: {e}", show_alert=True)

    # ── Banlar ro'yxati ───────────────────────────────────────────────
    elif action == "ban":
        @sync_to_async
        def _bans():
            return list(BannedUser.objects.order_by('-banned_at').values(
                'user_id', 'first_name', 'username', 'reason'
            )[:20])
        bans = await _bans()
        if not bans:
            return await callback.answer("✅ Permanent ban ro'yxati bo'sh.", show_alert=True)
        lines = [f"🚫 <b>Permanent Banlar</b> (oxirgi {len(bans)} ta):\n"]
        for b in bans:
            un = f" @{b['username']}" if b['username'] else ""
            reason = b['reason'] or "—"
            lines.append(
                f"• <b>{b['first_name'] or 'Noma\'lum'}</b>{un}\n"
                f"  🆔 <code>{b['user_id']}</code> | {reason}"
            )
        await callback.message.answer("\n".join(lines), parse_mode="HTML")
        await callback.answer()

    # ── Ogohlantirishlar ──────────────────────────────────────────────
    elif action == "wrn":
        warnings = await get_all_warnings()
        if not warnings:
            return await callback.answer("✅ Hech kim ogohlantirish olmagan.", show_alert=True)
        lines = ["⚠️ <b>Ogohlantirish jadvali:</b>\n"]
        for i, w in enumerate(warnings[:15], 1):
            un = f" @{w['username']}" if w['username'] else ""
            lines.append(
                f"{i}. <b>{w['first_name']}</b>{un}\n"
                f"   🆔 <code>{w['user_id']}</code> — <b>{w['count']}/3</b>"
            )
        await callback.message.answer("\n".join(lines), parse_mode="HTML")
        await callback.answer()

    # ── Qoidalarni guruhga yuborish ───────────────────────────────────
    elif action == "rul":
        rules_text = await get_active_rules()
        if not rules_text:
            return await callback.answer("❌ Faol qoidalar topilmadi. Admin panel → Guruh Qoidalaridan qo'shing.", show_alert=True)
        try:
            await bot.send_message(MAIN_CHAT_ID, f"📜 <b>Guruh Qoidalari</b>\n\n{rules_text}", parse_mode="HTML")
            await callback.answer("✅ Qoidalar guruhga yuborildi!")
        except Exception as e:
            await callback.answer(f"❌ Xatolik: {e}", show_alert=True)

    else:
        await callback.answer("❓ Noma'lum amal.")


# ─────────────────────────────────────────────────────────────────────
# /sutag — guruhning barcha (ma'lum) a'zolarini ismi bilan, alohida-
#          alohida tag qiladi. /stutag — jarayonni to'xtatadi.
# ─────────────────────────────────────────────────────────────────────
SUTAG_RANDOM_PHRASES = [
    "🌙 Tun tushdi... Mafia o'yini boshlanmoqda, hammasi shoshilsin!",
    "🎭 Niqoblaringizni kiying — o'yin boshlanish arafasida!",
    "🔪 Komissar barchani stol atrofiga chaqiryapti!",
    "🕵️ Shubhalilar yig'ilsin! Mafia Habibiti chaqiryapti!",
    "⚜️ Mafia Habibiti e'lon qiladi: barchasi join bo'lsin!",
    "🃏 Qartalar tarqatildi... O'yinga tayyor bo'ling!",
    "🌑 Shahar uxlamoqda... lekin Mafia uyg'oq! Hammasi keling!",
    "📯 E'lon: o'yin boshlanmoqda, hech kim chetda qolmasin!",
]

SUTAG_BATCH_SIZE  = 6     # bitta xabarda nechta odam tag qilinsin
SUTAG_BATCH_DELAY = 1.5   # batchlar orasidagi kutish (soniya) — Telegram flood-dan saqlaydi


@dp.message(F.chat.id == MAIN_CHAT_ID, F.text.regexp(r'(?s)^/sutag(?:@\w+)?(?:\s+(.+))?$'))
async def cmd_sutag(message: types.Message):
    """Guruhning barcha a'zolarini ismi bilan, alohida-alohida tag qiladi."""
    user_id = message.from_user.id
    chat_id = message.chat.id

    settings = await get_bot_settings_status()
    if settings.get("sutag_admin_only", True):
        if not (await is_bot_admin(user_id) or await is_admin(chat_id, user_id)):
            return await message.reply("⛔ Bu buyruqni faqat adminlar ishlata oladi.")

    if _sutag_jobs.get(chat_id, {}).get("active"):
        return await message.reply(
            "⚠️ Hozir tag jarayoni davom etmoqda.\n🛑 To'xtatish uchun: /stutag"
        )

    m = re.match(r'(?s)^/sutag(?:@\w+)?(?:\s+(.+))?$', message.text)
    custom_text = (m.group(1) or "").strip() if m else ""
    header = html.escape(custom_text, quote=False) if custom_text else random.choice(SUTAG_RANDOM_PHRASES)

    roster = await get_group_roster()
    if not roster:
        return await message.reply(
            "📭 Hozircha hech kim aniqlanmadi.\n"
            "ℹ️ Bot faqat guruhda kamida bitta xabar yozgan a'zolarni eslab qoladi — "
            "Telegram Bot API orqali to'liq a'zolar ro'yxatini olishning iloji yo'q."
        )

    _sutag_jobs[chat_id] = {"active": True, "started_by": user_id}
    total       = len(roster)
    sent_count  = 0
    stopped_early = False

    await message.reply(
        f"🏷 <b>Tag boshlandi</b> — {total} a'zo.\n🛑 To'xtatish: /stutag",
        parse_mode="HTML"
    )

    try:
        for i in range(0, total, SUTAG_BATCH_SIZE):
            if not _sutag_jobs.get(chat_id, {}).get("active"):
                stopped_early = True
                break
            batch = roster[i:i + SUTAG_BATCH_SIZE]
            lines = [f"📣 <b>{header}</b>", ""]
            for u in batch:
                safe_name = html.escape(u["first_name"], quote=False)
                lines.append(f"👤 <a href=\"tg://user?id={u['user_id']}\">{safe_name}</a>")
            text = "\n".join(lines)
            try:
                await bot.send_message(chat_id, text, parse_mode="HTML")
                sent_count += len(batch)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
                try:
                    await bot.send_message(chat_id, text, parse_mode="HTML")
                    sent_count += len(batch)
                except Exception as e2:
                    logger.error(f"/sutag batch yuborishda xatolik (retry): {e2}")
            except Exception as e:
                logger.error(f"/sutag batch yuborishda xatolik: {e}")
            await asyncio.sleep(SUTAG_BATCH_DELAY)
    finally:
        _sutag_jobs.pop(chat_id, None)

    if not stopped_early:
        try:
            await bot.send_message(
                chat_id,
                f"✅ Tag yakunlandi — <b>{sent_count}/{total}</b> kishi taglandi.",
                parse_mode="HTML"
            )
        except Exception:
            pass


@dp.message(F.chat.id == MAIN_CHAT_ID, F.text.regexp(r'^/stutag(?:@\w+)?$'))
async def cmd_stutag(message: types.Message):
    """Davom etayotgan /sutag jarayonini to'xtatadi."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    job = _sutag_jobs.get(chat_id)

    if not job or not job.get("active"):
        return await message.reply("ℹ️ Hozir faol tag jarayoni yo'q.")

    allowed = (
        user_id == job.get("started_by")
        or await is_bot_admin(user_id)
        or await is_admin(chat_id, user_id)
    )
    if not allowed:
        return await message.reply("⛔ Faqat boshlagan odam yoki adminlar to'xtatishi mumkin.")

    job["active"] = False
    await message.reply("🛑 Tag jarayoni to'xtatildi.")


# ─────────────────────────────────────────────────────────────────────
# on_my_chat_member — Bot guruhga qo'shilganda egasini admin qilish
# ─────────────────────────────────────────────────────────────────────
@dp.my_chat_member()
async def on_my_chat_member(update: types.ChatMemberUpdated):
    """Bot guruhga qo'shilganida BotOwner jadvalidagi egasini avtomatik admin qiladi."""
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status
    chat       = update.chat

    # Bot guruhga yangi qo'shildi (member yoki administrator bo'ldi)
    bot_just_added = (
        old_status in ("left", "kicked") and
        new_status in ("member", "administrator", "restricted")
    )
    if not bot_just_added:
        return

    logger.info(f"Bot '{chat.title}' ({chat.id}) guruhiga qo'shildi.")

    # Bot egalarini olish
    owner_ids = await get_bot_owner_ids()
    if not owner_ids:
        logger.info("Bot egasi belgilanmagan. Avtomatik admin qilish o'tkazib yuborildi.")
        return

    # Bot admin bo'lsa, uning huquqlarini aniqlaymiz
    bot_perms = {}
    try:
        me = await bot.get_me()
        # Biroz kutamiz — Telegram API ba'zan kech yangilanadi
        await asyncio.sleep(2)
        member = await bot.get_chat_member(chat.id, me.id)
        if member.status == "administrator":
            bot_perms = {
                'can_manage_chat':      getattr(member, 'can_manage_chat',      False) or False,
                'can_delete_messages':  getattr(member, 'can_delete_messages',  False) or False,
                'can_restrict_members': getattr(member, 'can_restrict_members', False) or False,
                'can_promote_members':  getattr(member, 'can_promote_members',  False) or False,
                'can_change_info':      getattr(member, 'can_change_info',      False) or False,
                'can_invite_users':     getattr(member, 'can_invite_users',     False) or False,
                'can_pin_messages':     getattr(member, 'can_pin_messages',     False) or False,
            }
        else:
            logger.warning(f"Bot {chat.title} guruhida admin emas — egasini ham admin qilib bo'lmaydi.")
            return
    except Exception as e:
        logger.error(f"Bot huquqlarini tekshirishda xatolik: {e}")
        return

    for owner_id in owner_ids:
        try:
            await bot.promote_chat_member(chat_id=chat.id, user_id=owner_id, **bot_perms)
            logger.info(f"Bot egasi {owner_id} '{chat.title}' guruhida admin qilindi.")
            await send_log(
                f"👑 <b>Bot egasi avtomatik admin qilindi!</b>\n"
                f"📌 Guruh: <b>{chat.title}</b>\n"
                f"👤 Egasi ID: <code>{owner_id}</code>\n"
                f"✅ Berilgan huquqlar: {', '.join(k for k, v in bot_perms.items() if v)}"
            )
        except Exception as e:
            logger.error(f"Bot egasini admin qilishda xatolik (ID {owner_id}): {e}")
            await send_log(
                f"⚠️ <b>Bot egasini admin qilishda xatolik!</b>\n"
                f"📌 Guruh: {chat.title}\n"
                f"👤 Egasi ID: <code>{owner_id}</code>\n"
                f"❌ Xato: {e}"
            )


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

        # Avto-qabul va kaptcha holatlarini tekshiramiz
        join_active    = await is_join_request_enabled_in_db()
        captcha_active = await is_captcha_enabled_in_db()

        # Agar ikkisi ham o'chiq bo'lsa — bot zayafkaga UMUMAN tegmasin
        if not join_active and not captcha_active:
            return

        # Kaptcha yoqiq bo'lsa — kaptcha yuboramiz (join_active dan qat'iy nazar)
        if captcha_active:
            await send_captcha(update.from_user.id, update.from_user.first_name)
            return

        # Faqat avto-qabul yoqiq, kaptcha o'chiq — to'g'ridan qabul
        try:
            await bot.approve_chat_join_request(MAIN_CHAT_ID, update.from_user.id)
            await send_private(update.from_user.id, "✅ Guruhga xush kelibsiz! 🎉")
        except Exception as e:
            logger.error(f"To'g'ridan-to'g'ri qabul qilishda xatolik: {e}")


@dp.chat_member()
async def on_chat_member_update(update: types.ChatMemberUpdated):
    """A'zo holati o'zgarganda: yangi a'zo, ban, unban, hafli userni qayta ban."""
    if update.chat.id != MAIN_CHAT_ID:
        return

    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status
    user       = update.new_chat_member.user
    user_id    = user.id
    user_name  = user.first_name or f"ID:{user_id}"
    username   = f"@{user.username}" if user.username else "—"

    # Kim ban qilganini aniqlaymiz (agar Telegram bersa)
    banned_by = None
    if update.from_user and update.from_user.id != user_id:
        banned_by = update.from_user.first_name or f"ID:{update.from_user.id}"

    # ── Yangi a'zo kirdi ──────────────────────────────────────────────
    just_joined = (
        old_status in ("left", "kicked") and
        new_status in ("member", "restricted")
    )
    if just_joined:
        await increment_daily_new_member()
        settings = await get_bot_settings_status()

        # ── Guruhda welcome xabari ──────────────────────────────────
        if settings.get("welcome"):
            try:
                member_count = await bot.get_chat_member_count(MAIN_CHAT_ID)
            except Exception:
                member_count = "?"
            uname = f"@{user.username}" if user.username else user_name
            welcome_tpl = settings.get(
                "welcome_text",
                "👋 Salom, {name}! Guruhga xush kelibsiz! 🎉"
            )
            welcome_msg = welcome_tpl.format(
                name=user_name,
                username=uname,
                count=member_count,
            )
            try:
                sent = await bot.send_message(
                    MAIN_CHAT_ID,
                    welcome_msg,
                    parse_mode="HTML"
                )
                # 5 daqiqadan keyin o'chir
                await asyncio.sleep(300)
                try:
                    await sent.delete()
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Welcome xabar xatolik: {e}")

        # ── Private ga qoidalar ─────────────────────────────────────
        rules_text = await get_active_rules()
        if rules_text:
            greeting = (
                f"👋 Salom, <b>{user_name}</b>!\n\n"
                f"🎉 <b>Guruhga xush kelibsiz!</b>\n\n"
                f"{rules_text}\n\n"
                f"⚠️ Qoidalarga rioya qilmasangiz, ogohlantirish yoki ban beriladi."
            )
            await send_private(user_id, greeting)
        return

    by_line = f"\n👮 <b>Kim:</b> {banned_by}" if banned_by else ""

    # ── 1. BAN qilindi ────────────────────────────────────────────────
    just_banned = (
        old_status in ("member", "administrator", "creator", "restricted", "left") and
        new_status == "kicked"
    )
    if just_banned:
        await send_log(
            f"🚫 <b>BAN qilindi</b>\n"
            f"👤 <b>{user_name}</b> ({username})\n"
            f"🆔 <code>{user_id}</code>"
            f"{by_line}"
        )
        logger.info(f"Ban log: {user_id} ({user_name})")
        return

    # ── 2. UNBAN qilindi ──────────────────────────────────────────────
    just_unbanned = (
        old_status == "kicked" and
        new_status in ("member", "left", "restricted")
    )
    if just_unbanned:
        await send_log(
            f"✅ <b>UNBAN qilindi</b>\n"
            f"👤 <b>{user_name}</b> ({username})\n"
            f"🆔 <code>{user_id}</code>"
            f"{by_line}"
        )
        if await is_permanently_banned(user_id):
            try:
                await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
                logger.warning(f"Hafli user {user_id} qayta ban qilindi.")
                await send_log(
                    f"🚨 <b>Hafli user QAYTA BAN!</b>\n"
                    f"👤 {user_name} — <code>{user_id}</code>\n"
                    f"⚡ Kimdir unban qildi — bot qayta ban qildi."
                )
            except Exception as e:
                logger.error(f"Hafli user qayta ban xatolik: {e}")
        return

    # ── 3. MUTE / UNMUTE (restricted holat o'zgardi) ──────────────────
    if old_status in ("member", "restricted") and new_status == "restricted":
        old_can_send = getattr(update.old_chat_member, 'can_send_messages', True)
        new_can_send = getattr(update.new_chat_member, 'can_send_messages', True)
        if old_can_send and not new_can_send:
            await send_log(
                f"🔇 <b>MUTE qilindi</b>\n"
                f"👤 <b>{user_name}</b> ({username})\n"
                f"🆔 <code>{user_id}</code>"
                f"{by_line}"
            )
            return
        if not old_can_send and new_can_send:
            await send_log(
                f"🔊 <b>UNMUTE qilindi</b>\n"
                f"👤 <b>{user_name}</b> ({username})\n"
                f"🆔 <code>{user_id}</code>"
                f"{by_line}"
            )
            return

    # ── 4. ADMIN qilindi ──────────────────────────────────────────────
    if old_status in ("member", "restricted", "left") and new_status == "administrator":
        await send_log(
            f"👑 <b>ADMIN qilindi</b>\n"
            f"👤 <b>{user_name}</b> ({username})\n"
            f"🆔 <code>{user_id}</code>"
            f"{by_line}"
        )
        return

    # ── 5. ADMIN olib tashlandi ───────────────────────────────────────
    if old_status == "administrator" and new_status == "member":
        await send_log(
            f"❌ <b>ADMIN olib tashlandi</b>\n"
            f"👤 <b>{user_name}</b> ({username})\n"
            f"🆔 <code>{user_id}</code>"
            f"{by_line}"
        )
        return

    # ── 6. Hafli userni qayta ban (fallback) ──────────────────────────
    was_banned = old_status in ("kicked", "restricted")
    now_free   = new_status in ("member", "administrator", "creator", "restricted", "left")
    if was_banned and now_free:
        if await is_permanently_banned(user_id):
            try:
                await bot.ban_chat_member(chat_id=MAIN_CHAT_ID, user_id=user_id)
                logger.warning(f"Hafli user {user_id} qayta ban qilindi.")
                await send_log(
                    f"🚨 <b>Hafli user QAYTA BAN!</b>\n"
                    f"👤 {user_name} — <code>{user_id}</code>\n"
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

    # Static fayllar Railway deploy vaqtida yig'iladi
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

    # ── MODERATSIYA MODULI ────────────────────────────────────────────
    MOD.init(
        bot             = bot,
        main_chat       = MAIN_CHAT_ID,
        log_chat        = LOG_CHAT_ID,
        get_warn        = get_warning,
        set_warn        = set_warning,
        is_admin        = is_admin,
        is_bot_admin    = is_bot_admin,
        check_bot_perm  = check_bot_permission,
        inc_blocked     = increment_blocked_stat,
        send_log_fn     = send_log,
    )
    MOD.register(dp)
    logger.info("✅ Moderatsiya moduli ulandi!")

    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_join_request", "chat_member", "my_chat_member"]),
        run_django_web_server(),
        scheduled_messages_loop(),
    )


# ─────────────────────────────────────────────────────────────────────
# REJALASHTIRILGAN XABARLAR LOOP
# ─────────────────────────────────────────────────────────────────────
async def scheduled_messages_loop():
    """Har 60 soniyada rejalashtirilgan xabarlarni tekshiradi va yuboradi."""
    await asyncio.sleep(10)
    logger.info("⏰ Rejalashtirilgan xabarlar loopi boshlandi.")
    while True:
        try:
            msgs = await get_scheduled_messages_to_send()
            for msg in msgs:
                try:
                    await bot.send_message(
                        MAIN_CHAT_ID,
                        msg.text,
                        parse_mode="HTML"
                    )
                    await update_scheduled_after_send(msg.pk, msg.repeat)
                    logger.info(f"⏰ Rejalashtirilgan xabar yuborildi: {msg.title}")
                except Exception as e:
                    logger.error(f"Scheduled xabar yuborishda xatolik: {e}")
        except Exception as e:
            logger.error(f"Scheduled loop xatolik: {e}")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
