"""
╔══════════════════════════════════════════════════════════════╗
║       ⚜  MAFIA HABIBITI — MODERATSIYA TIZIMI  ⚜            ║
║                      moderator.py                            ║
║                                                              ║
║   Barcha mod amallari chiroyli dizayn + to'liq loglash      ║
╚══════════════════════════════════════════════════════════════╝

ISHLATISH (main.py da):
─────────────────────────────────────────────────
    from moderator import MOD

    # main() ichida, bot va dp tayyor bo'lgandan so'ng:
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
─────────────────────────────────────────────────
"""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ChatPermissions,
)

log = logging.getLogger(__name__)
TZ  = ZoneInfo("Asia/Tashkent")


# ══════════════════════════════════════════════════════════════
# 🎨  DIZAYN YORDAMCHILARI
# ══════════════════════════════════════════════════════════════

def _now() -> str:
    """Hozirgi vaqtni Toshkent vaqti bilan qaytaradi."""
    return datetime.now(TZ).strftime("%d.%m.%Y %H:%M")


def _warn_bar(count: int, total: int = 3) -> str:
    """
    Ogohlantirish progress bari:
      0 → ⬜⬜⬜   1 → 🟨⬜⬜   2 → 🟧🟧⬜   3 → 🟥🟥🟥
    """
    colors = {1: "🟨", 2: "🟧", 3: "🟥"}
    color  = colors.get(count, "🟥")
    filled = color  * min(count, total)
    empty  = "⬜" * max(total - count, 0)
    return filled + empty


def _divider(n: int = 24) -> str:
    return "━" * n


# ─── Guruhga yuboriladigan amal kartochkasi ───────────────────────────
def _action_card(
    icon: str, title: str,
    fname: str, uid: int,
    admin: str,
    reason: str = "Ko'rsatilmagan",
    extra: str  = "",
) -> str:
    lines = [
        f"{icon} <b>{title}</b>",
        _divider(),
        f"👤 <b>Foydalanuvchi:</b> {fname}",
        f"🆔 <b>ID:</b> <code>{uid}</code>",
        f"📝 <b>Sabab:</b> {reason}",
        f"👮 <b>Admin:</b> {admin}",
        f"⏰ <b>Vaqt:</b> {_now()}",
    ]
    if extra:
        lines.append(extra)
    lines.append(_divider())
    return "\n".join(lines)


# ─── Log kanalga yuboriladigan batafsil karta ───────────────────────
def _log_card(
    icon: str, title: str,
    fname: str, uname: str,
    uid: int, admin: str,
    reason: str = "—",
    extra: str  = "",
) -> str:
    lines = [
        f"{'▬' * 12} <b>JURNAL</b> {'▬' * 12}",
        f"{icon} <b>AMAL: {title}</b>",
        _divider(),
        f"👤 <b>Nishon:</b> {fname}",
        f"🔖 <b>Username:</b> {uname}",
        f"🆔 <b>ID:</b> <code>{uid}</code>",
        f"📝 <b>Sabab:</b> {reason}",
        f"👮 <b>Bajardi:</b> {admin}",
        f"⏰ <b>Vaqt:</b> {_now()}",
    ]
    if extra:
        lines.append(f"📌 <b>Qo'shimcha:</b> {extra}")
    lines.append(_divider())
    return "\n".join(lines)


# ─── Ogohlantirish kartochkasi ────────────────────────────────────────
def _warn_card(
    fname: str, uid: int,
    admin: str, count: int,
    reason: str = "Ko'rsatilmagan",
) -> str:
    bar = _warn_bar(count)
    danger = "🔴 <b>OXIRGI OGOHLANTIRISH! Keyingisi — BAN!</b>" if count == 2 else \
             f"⚠️ 3 ta warn → Avtomatik ban!"
    return (
        f"⚠️ <b>OGOHLANTIRISH</b>\n"
        f"{_divider()}\n"
        f"👤 <b>Foydalanuvchi:</b> {fname}\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"📝 <b>Sabab:</b> {reason}\n"
        f"👮 <b>Admin:</b> {admin}\n"
        f"⏰ <b>Vaqt:</b> {_now()}\n"
        f"{_divider()}\n"
        f"📊 <b>Holat:</b> {bar}  <b>{count}/3</b>\n"
        f"{danger}"
    )


# ══════════════════════════════════════════════════════════════
# 🔧  ASOSIY KLASS
# ══════════════════════════════════════════════════════════════

class Moderator:
    """Barcha moderatsiya funksiyalarini o'z ichiga oladi."""

    def __init__(self):
        self.bot:        Bot | None = None
        self.main_chat:  int = 0
        self.log_chat:   int = 0

        # Inject qilinadigan funksiyalar
        self._get_warn        = None
        self._set_warn        = None
        self._is_admin        = None
        self._is_bot_admin    = None
        self._check_bot_perm  = None
        self._inc_blocked     = None
        self._send_log_fn     = None

    # ─────────────────────────────────────────────────────────
    def init(
        self,
        bot,
        main_chat: int,
        log_chat: int,
        get_warn,
        set_warn,
        is_admin=None,
        is_bot_admin=None,
        check_bot_perm=None,
        inc_blocked=None,
        send_log_fn=None,
    ):
        self.bot           = bot
        self.main_chat     = main_chat
        self.log_chat      = log_chat
        self._get_warn     = get_warn
        self._set_warn     = set_warn
        self._is_admin     = is_admin
        self._is_bot_admin = is_bot_admin
        self._check_bot_perm = check_bot_perm
        self._inc_blocked  = inc_blocked
        self._send_log_fn  = send_log_fn
        log.info("✅ Moderator moduli ishga tushdi.")

    # ─────────────────────────────────────────────────────────
    def register(self, dp: Dispatcher):
        """Barcha handlerlarni dp ga bog'laydi."""
        dp.message.register(
            self._cmd_warn,   F.text.startswith("/warn"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_unwarn, F.text.startswith("/unwarn"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_warns,  F.text.startswith("/warns"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_ban,    F.text.startswith("/ban"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_unban,  F.text.startswith("/unban"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_mute,   F.text.startswith("/mute"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_unmute, F.text.startswith("/unmute"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_info,   F.text.startswith("/info"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_id,     F.text.startswith("/id"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_admin,   F.text.startswith("/admin"),
            F.chat.id == self.main_chat
        )
        dp.message.register(
            self._cmd_unadmin, F.text.startswith("/unadmin"),
            F.chat.id == self.main_chat
        )
        # Callback uchun "m_" prefiksi ishlatiladi (main.py "mod_" dan farq qiladi)
        dp.callback_query.register(
            self._mod_cb, F.data.startswith("m_")
        )
        log.info("✅ Moderator handlerlari ro'yxatdan o'tdi.")

    # ══════════════════════════════════════════════════════════
    # 🔑  ICHKI YORDAMCHI METODLAR
    # ══════════════════════════════════════════════════════════

    async def _log(
        self, text: str,
        user_id: int = None,
        unblock: bool = False,
    ):
        """Log kanalga xabar yuboradi."""
        if self._send_log_fn:
            await self._send_log_fn(text, user_id=user_id, unblock_button=unblock)
            return
        try:
            markup = None
            if unblock and user_id:
                markup = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="✅ Blokdan chiqarish",
                        callback_data=f"unblock_{user_id}"
                    )
                ]])
            await self.bot.send_message(
                self.log_chat, text,
                parse_mode="HTML", reply_markup=markup
            )
        except Exception as e:
            log.error(f"Log xatolik: {e}")

    async def _get_target(self, message: types.Message):
        """
        Reply yoki argument orqali (user_id, first_name, @username) qaytaradi.
        Uchala qiymat None bo'lishi maqsad topilmaganda.
        """
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            return (
                u.id,
                u.first_name or f"ID:{u.id}",
                f"@{u.username}" if u.username else "—",
            )

        parts = message.text.split()
        if len(parts) > 1:
            arg = parts[1]
            if arg.lstrip("-").isdigit():
                uid = int(arg)
                try:
                    m = await self.bot.get_chat_member(self.main_chat, uid)
                    return (
                        uid,
                        m.user.first_name or f"ID:{uid}",
                        f"@{m.user.username}" if m.user.username else "—",
                    )
                except Exception:
                    return uid, f"ID:{uid}", "—"

            if arg.startswith("@"):
                try:
                    c = await self.bot.get_chat(arg)
                    return (
                        c.id,
                        c.first_name or arg,
                        arg,
                    )
                except Exception:
                    pass

        return None, None, None

    def _get_reason(self, message: types.Message) -> str:
        """Komanda matnidan sababni oladi."""
        parts = message.text.split(maxsplit=1 if message.reply_to_message else 2)
        if message.reply_to_message:
            return parts[1].strip() if len(parts) > 1 else "Ko'rsatilmagan"
        # /ban @user sabab  yoki  /ban ID sabab
        if len(parts) > 2:
            return parts[2].strip()
        return "Ko'rsatilmagan"

    def _mod_kb(self, uid: int, warn_count: int = 0) -> InlineKeyboardMarkup:
        """Universial moderatsiya inline tugmalari to'plami."""
        bar = _warn_bar(warn_count)
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⚠️ Warn  {bar}  {warn_count}/3",
                    callback_data=f"m_warn_{uid}"
                ),
            ],
            [
                InlineKeyboardButton(text="✅ Unwarn",  callback_data=f"m_unwarn_{uid}"),
                InlineKeyboardButton(text="🔇 Mute",    callback_data=f"m_mute_{uid}"),
                InlineKeyboardButton(text="🔊 Unmute",  callback_data=f"m_unmute_{uid}"),
            ],
            [
                InlineKeyboardButton(text="🚫 Ban",     callback_data=f"m_ban_{uid}"),
                InlineKeyboardButton(text="✅ Unban",   callback_data=f"m_unban_{uid}"),
            ],
            [
                InlineKeyboardButton(text="👑 Admin",   callback_data=f"m_mkadm_{uid}"),
                InlineKeyboardButton(text="❌ Unadmin", callback_data=f"m_rmadm_{uid}"),
            ],
        ])

    def _unban_only_kb(self, uid: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Unban", callback_data=f"m_unban_{uid}")
        ]])

    def _unmute_only_kb(self, uid: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔊 Unmute", callback_data=f"m_unmute_{uid}")
        ]])

    # ══════════════════════════════════════════════════════════
    # 📋  KOMANDALAR
    # ══════════════════════════════════════════════════════════

    # ─── /warn ───────────────────────────────────────────────
    async def _cmd_warn(self, message: types.Message):
        if not await self._is_admin(self.main_chat, message.from_user.id):
            return

        uid, fname, uname = await self._get_target(message)
        if not uid:
            return await message.reply(
                "❗ <b>Ishlatish:</b> <code>/warn</code> + reply yoki <code>/warn @username sabab</code>",
                parse_mode="HTML"
            )

        if await self._is_admin(self.main_chat, uid):
            return await message.reply("⛔ Admin ogohlantirish olmaydi!")

        admin  = message.from_user.first_name or "Admin"
        reason = self._get_reason(message)
        count  = await self._get_warn(uid) + 1
        await self._set_warn(uid, count)

        # Kunlik warn statistikasini oshiramiz
        try:
            from __main__ import increment_daily_warn as _idw
            await _idw()
        except Exception:
            pass

        if count >= 3:
            # ── 3/3 → Ban ──────────────────────────────────────
            try:
                await self.bot.ban_chat_member(chat_id=self.main_chat, user_id=uid)
                await self._set_warn(uid, 0)
                if self._inc_blocked:
                    await self._inc_blocked()

                await message.reply(
                    _action_card(
                        "🚫🔨", "BAN  (Warn to'ldi)",
                        fname, uid, admin, reason,
                        extra=f"🟥🟥🟥  <b>3/3 warn → Avtomatik ban!</b>"
                    ),
                    parse_mode="HTML",
                    reply_markup=self._unban_only_kb(uid)
                )
                await self._log(
                    _log_card(
                        "🚫", "BAN (warn to'ldi)", fname, uname, uid, admin, reason,
                        extra=f"🟥🟥🟥  3/3 → avtomatik ban"
                    ),
                    user_id=uid, unblock=True
                )
            except Exception as e:
                await message.reply(f"❌ Ban xatolik: {e}")
        else:
            # ── Warn kartochkasi ────────────────────────────────
            await message.reply(
                _warn_card(fname, uid, admin, count, reason),
                parse_mode="HTML",
                reply_markup=self._mod_kb(uid, count)
            )
            await self._log(
                _log_card(
                    "⚠️", "WARN", fname, uname, uid, admin, reason,
                    extra=f"{_warn_bar(count)}  {count}/3"
                )
            )

    # ─── /unwarn ─────────────────────────────────────────────
    async def _cmd_unwarn(self, message: types.Message):
        if not await self._is_admin(self.main_chat, message.from_user.id):
            return

        uid, fname, uname = await self._get_target(message)
        if not uid:
            return await message.reply(
                "❗ <b>Ishlatish:</b> <code>/unwarn</code> + reply yoki <code>/unwarn @username</code>",
                parse_mode="HTML"
            )

        count = await self._get_warn(uid)
        if count <= 0:
            return await message.reply(
                f"ℹ️ <b>{fname}</b> ning ogohlantirishlari yo'q.",
                parse_mode="HTML"
            )

        admin     = message.from_user.first_name or "Admin"
        new_count = count - 1
        await self._set_warn(uid, new_count)
        bar = _warn_bar(new_count)

        await message.reply(
            f"✅ <b>OGOHLANTIRISH OLIB TASHLANDI</b>\n"
            f"{_divider()}\n"
            f"👤 <b>Foydalanuvchi:</b> {fname}\n"
            f"🆔 <b>ID:</b> <code>{uid}</code>\n"
            f"👮 <b>Admin:</b> {admin}\n"
            f"⏰ <b>Vaqt:</b> {_now()}\n"
            f"{_divider()}\n"
            f"📊 <b>Qoldi:</b> {bar}  <b>{new_count}/3</b>",
            parse_mode="HTML",
            reply_markup=self._mod_kb(uid, new_count)
        )
        await self._log(
            _log_card(
                "✅", "UNWARN", fname, uname, uid, admin,
                extra=f"{bar}  {new_count}/3 qoldi"
            )
        )

    # ─── /warns (ro'yxat) ────────────────────────────────────
    async def _cmd_warns(self, message: types.Message):
        if not await self._is_admin(self.main_chat, message.from_user.id):
            return

        try:
            from asgiref.sync import sync_to_async
            from __main__ import UserWarning as UW, TelegramUser as TU

            @sync_to_async
            def _fetch():
                rows = list(
                    UW.objects.filter(count__gt=0)
                    .order_by("-count")
                    .values("user_id", "count")
                )
                result = []
                for r in rows:
                    u = (
                        TU.objects.filter(user_id=r["user_id"])
                        .values("first_name", "username")
                        .first()
                    )
                    result.append({
                        "user_id":    r["user_id"],
                        "count":      r["count"],
                        "first_name": (u["first_name"] if u else None) or "Noma'lum",
                        "username":   (u["username"]   if u else None),
                    })
                return result

            warnings = await _fetch()
        except Exception as e:
            return await message.reply(f"❌ Ma'lumot olishda xatolik: {e}")

        if not warnings:
            return await message.reply(
                f"✅ <b>Hozircha hech kim ogohlantirish olmagan.</b>",
                parse_mode="HTML"
            )

        lines = [
            f"📋 <b>OGOHLANTIRISH JADVALI</b>  ({len(warnings)} kishi)",
            _divider(),
        ]
        for i, w in enumerate(warnings, 1):
            bar   = _warn_bar(w["count"])
            upart = f"  |  @{w['username']}" if w["username"] else ""
            lines.append(
                f"{i}. {bar} <b>{w['count']}/3</b>\n"
                f"   👤 <b>{w['first_name']}</b>{upart}\n"
                f"   🆔 <code>{w['user_id']}</code>"
            )
        lines.append(_divider())
        await message.reply("\n".join(lines), parse_mode="HTML")

    # ─── /ban ────────────────────────────────────────────────
    async def _cmd_ban(self, message: types.Message):
        if not await self._is_admin(self.main_chat, message.from_user.id):
            return

        if self._check_bot_perm and not await self._check_bot_perm(self.main_chat, "can_restrict_members"):
            return await message.reply(
                "⚠️ <b>Botda 'Foydalanuvchilarni cheklash' huquqi yo'q!</b>\n"
                "Guruh sozlamalarida botga ushbu huquqni bering.",
                parse_mode="HTML"
            )

        uid, fname, uname = await self._get_target(message)
        if not uid:
            return await message.reply(
                "❗ <b>Ishlatish:</b> <code>/ban</code> + reply yoki <code>/ban @username sabab</code>",
                parse_mode="HTML"
            )

        if await self._is_admin(self.main_chat, uid):
            return await message.reply("⛔ Adminni ban qilib bo'lmaydi!")

        admin  = message.from_user.first_name or "Admin"
        reason = self._get_reason(message)

        try:
            await self.bot.ban_chat_member(chat_id=self.main_chat, user_id=uid)
            await self._set_warn(uid, 0)
            if self._inc_blocked:
                await self._inc_blocked()

            await message.reply(
                _action_card("🚫", "BAN", fname, uid, admin, reason),
                parse_mode="HTML",
                reply_markup=self._unban_only_kb(uid)
            )
            await self._log(
                _log_card("🚫", "BAN", fname, uname, uid, admin, reason),
                user_id=uid, unblock=True
            )
        except Exception as e:
            await message.reply(f"❌ Ban qilishda xatolik: {e}")

    # ─── /unban ──────────────────────────────────────────────
    async def _cmd_unban(self, message: types.Message):
        if not await self._is_admin(self.main_chat, message.from_user.id):
            return

        uid, fname, uname = await self._get_target(message)
        if not uid:
            return await message.reply(
                "❗ <b>Ishlatish:</b> <code>/unban</code> + reply yoki <code>/unban @username</code>",
                parse_mode="HTML"
            )

        admin = message.from_user.first_name or "Admin"
        try:
            try:
                await self.bot.unban_chat_member(
                    chat_id=self.main_chat, user_id=uid, only_if_banned=False
                )
            except Exception as ue:
                if "PARTICIPANT_ID_INVALID" not in str(ue):
                    raise

            await message.reply(
                f"✅ <b>UNBAN</b>\n"
                f"{_divider()}\n"
                f"👤 <b>Foydalanuvchi:</b> {fname}\n"
                f"🆔 <b>ID:</b> <code>{uid}</code>\n"
                f"👮 <b>Admin:</b> {admin}\n"
                f"⏰ <b>Vaqt:</b> {_now()}\n"
                f"{_divider()}\n"
                f"✅ Foydalanuvchi guruhga qaytishi mumkin.",
                parse_mode="HTML"
            )
            await self._log(
                _log_card("✅", "UNBAN", fname, uname, uid, admin)
            )
        except Exception as e:
            await message.reply(f"❌ Unban xatolik: {e}")

    # ─── /mute ───────────────────────────────────────────────
    async def _cmd_mute(self, message: types.Message):
        if not await self._is_admin(self.main_chat, message.from_user.id):
            return

        if self._check_bot_perm and not await self._check_bot_perm(self.main_chat, "can_restrict_members"):
            return await message.reply(
                "⚠️ <b>Botda 'Cheklash' huquqi yo'q!</b>",
                parse_mode="HTML"
            )

        uid, fname, uname = await self._get_target(message)
        if not uid:
            return await message.reply(
                "❗ <b>Ishlatish:</b> <code>/mute</code> + reply yoki <code>/mute @username sabab</code>",
                parse_mode="HTML"
            )

        if await self._is_admin(self.main_chat, uid):
            return await message.reply("⛔ Adminni mute qilib bo'lmaydi!")

        admin  = message.from_user.first_name or "Admin"
        reason = self._get_reason(message)

        try:
            await self.bot.restrict_chat_member(
                chat_id=self.main_chat,
                user_id=uid,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await message.reply(
                _action_card("🔇", "MUTE", fname, uid, admin, reason,
                             extra="🔕 Foydalanuvchi xabar yoza olmaydi."),
                parse_mode="HTML",
                reply_markup=self._unmute_only_kb(uid)
            )
            await self._log(
                _log_card("🔇", "MUTE", fname, uname, uid, admin, reason)
            )
        except Exception as e:
            await message.reply(f"❌ Mute xatolik: {e}")

    # ─── /unmute ─────────────────────────────────────────────
    async def _cmd_unmute(self, message: types.Message):
        if not await self._is_admin(self.main_chat, message.from_user.id):
            return

        uid, fname, uname = await self._get_target(message)
        if not uid:
            return await message.reply(
                "❗ <b>Ishlatish:</b> <code>/unmute</code> + reply yoki <code>/unmute @username</code>",
                parse_mode="HTML"
            )

        admin = message.from_user.first_name or "Admin"
        try:
            await self.bot.restrict_chat_member(
                chat_id=self.main_chat,
                user_id=uid,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                )
            )
            await message.reply(
                f"🔊 <b>UNMUTE</b>\n"
                f"{_divider()}\n"
                f"👤 <b>Foydalanuvchi:</b> {fname}\n"
                f"🆔 <b>ID:</b> <code>{uid}</code>\n"
                f"👮 <b>Admin:</b> {admin}\n"
                f"⏰ <b>Vaqt:</b> {_now()}\n"
                f"{_divider()}\n"
                f"✅ Xabar yozish huquqi tiklandi.",
                parse_mode="HTML"
            )
            await self._log(
                _log_card("🔊", "UNMUTE", fname, uname, uid, admin)
            )
        except Exception as e:
            await message.reply(f"❌ Unmute xatolik: {e}")

    # ─── /info ───────────────────────────────────────────────
    async def _cmd_info(self, message: types.Message):
        if not await self._is_admin(self.main_chat, message.from_user.id):
            return

        uid, _, uname = await self._get_target(message)
        if not uid:
            return await message.reply(
                "❗ <b>Ishlatish:</b> <code>/info</code> + reply yoki <code>/info @username</code>",
                parse_mode="HTML"
            )

        try:
            from asgiref.sync import sync_to_async
            from __main__ import TelegramUser as TU, UserWarning as UW, BannedUser as BU

            @sync_to_async
            def _fetch(uid):
                try:
                    u  = TU.objects.get(user_id=uid)
                    w  = UW.objects.filter(user_id=uid).first()
                    b  = BU.objects.filter(user_id=uid).exists()
                    return {
                        "found":      True,
                        "first_name": u.first_name or "Noma'lum",
                        "username":   u.username,
                        "joined_at":  u.joined_at.strftime("%d.%m.%Y %H:%M"),
                        "warnings":   w.count if w else 0,
                        "perm_ban":   b,
                    }
                except TU.DoesNotExist:
                    return {"found": False}

            info = await _fetch(uid)
        except Exception:
            info = {"found": False}

        warn_count  = info.get("warnings", 0) if info.get("found") else 0
        bar         = _warn_bar(warn_count)
        is_tg_admin = await self._is_admin(self.main_chat, uid)
        status = (
            "👑 Admin"        if is_tg_admin else
            "🔒 Perm. banlangan" if info.get("perm_ban") else
            "👤 A'zo"
        )
        un_text = f"@{info['username']}" if info.get("username") else uname

        if not info.get("found"):
            text = (
                f"🪪 <b>FOYDALANUVCHI MA'LUMOTLARI</b>\n"
                f"{_divider()}\n"
                f"🔖 <b>Username:</b> {un_text}\n"
                f"🆔 <b>ID:</b> <code>{uid}</code>\n"
                f"📌 <b>Holat:</b> {status}\n"
                f"📊 <b>Ogohlantirishlar:</b> {bar}  {warn_count}/3\n"
                f"{_divider()}\n"
                f"⚠️ Bazada topilmadi (bot ishlatmagan)"
            )
        else:
            text = (
                f"🪪 <b>FOYDALANUVCHI MA'LUMOTLARI</b>\n"
                f"{_divider()}\n"
                f"📛 <b>Ismi:</b> {info['first_name']}\n"
                f"🔖 <b>Username:</b> {un_text}\n"
                f"🆔 <b>ID:</b> <code>{uid}</code>\n"
                f"📌 <b>Holat:</b> {status}\n"
                f"📅 <b>Bot ishlatgan:</b> {info['joined_at']}\n"
                f"📊 <b>Ogohlantirishlar:</b> {bar}  <b>{warn_count}/3</b>\n"
                f"{_divider()}"
            )

        await message.reply(
            text, parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=self._mod_kb(uid, warn_count)
        )

    # ─── /id ─────────────────────────────────────────────────
    async def _cmd_id(self, message: types.Message):
        if not await self._is_admin(self.main_chat, message.from_user.id):
            return

        uid, fname, uname = await self._get_target(message)
        if not uid:
            uid   = message.from_user.id
            fname = message.from_user.first_name or "Siz"
            uname = f"@{message.from_user.username}" if message.from_user.username else "—"

        warn_count  = await self._get_warn(uid)
        bar         = _warn_bar(warn_count)
        is_tg_admin = await self._is_admin(self.main_chat, uid)
        status      = "👑 Admin" if is_tg_admin else "👤 A'zo"
        un_link = (
            f"<a href='https://t.me/{uname[1:]}'>{uname}</a>"
            if uname.startswith("@") else uname
        )

        await message.reply(
            f"🪪 <b>SHAXS KARTOCHKASI</b>\n"
            f"{_divider()}\n"
            f"📛 <b>Ismi:</b> {fname}\n"
            f"🔖 <b>Username:</b> {un_link}\n"
            f"🆔 <b>ID:</b> <code>{uid}</code>\n"
            f"📌 <b>Holat:</b> {status}\n"
            f"📊 <b>Ogohlantirishlar:</b> {bar}  <b>{warn_count}/3</b>\n"
            f"{_divider()}",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=self._mod_kb(uid, warn_count)
        )

    # ─── /admin ──────────────────────────────────────────────
    async def _cmd_admin(self, message: types.Message):
        if not (self._is_bot_admin and await self._is_bot_admin(message.from_user.id)):
            return await message.reply("❌ Sizda bunday huquq yo'q!")

        if self._check_bot_perm and not await self._check_bot_perm(self.main_chat, "can_promote_members"):
            return await message.reply(
                "⚠️ <b>Botda 'Admin boshqarish' huquqi yo'q!</b>",
                parse_mode="HTML"
            )

        uid, fname, uname = await self._get_target(message)
        if not uid:
            return await message.reply(
                "❗ <b>Ishlatish:</b> <code>/admin</code> + reply yoki <code>/admin @username</code>",
                parse_mode="HTML"
            )

        admin = message.from_user.first_name or "Admin"
        try:
            await self.bot.promote_chat_member(
                chat_id=self.main_chat, user_id=uid,
                can_delete_messages  = True,
                can_restrict_members = True,
                can_pin_messages     = True,
                can_invite_users     = True,
            )
            await message.reply(
                _action_card("👑", "ADMIN QO'SHILDI", fname, uid, admin),
                parse_mode="HTML"
            )
            await self._log(
                _log_card("👑", "ADMIN QO'SHILDI", fname, uname, uid, admin)
            )
        except Exception as e:
            await message.reply(f"❌ Admin qilishda xatolik: {e}")

    # ─── /unadmin ────────────────────────────────────────────
    async def _cmd_unadmin(self, message: types.Message):
        if not (self._is_bot_admin and await self._is_bot_admin(message.from_user.id)):
            return await message.reply("❌ Sizda bunday huquq yo'q!")

        uid, fname, uname = await self._get_target(message)
        if not uid:
            return await message.reply(
                "❗ <b>Ishlatish:</b> <code>/unadmin</code> + reply yoki <code>/unadmin @username</code>",
                parse_mode="HTML"
            )

        admin = message.from_user.first_name or "Admin"
        try:
            await self.bot.promote_chat_member(
                chat_id=self.main_chat, user_id=uid,
                can_delete_messages  = False,
                can_restrict_members = False,
                can_pin_messages     = False,
                can_invite_users     = False,
                can_manage_chat      = False,
            )
            await message.reply(
                _action_card("❌", "ADMIN OLIB TASHLANDI", fname, uid, admin),
                parse_mode="HTML"
            )
            await self._log(
                _log_card("❌", "UNADMIN", fname, uname, uid, admin)
            )
        except Exception as e:
            await message.reply(f"❌ Unadmin xatolik: {e}")

    # ══════════════════════════════════════════════════════════
    # 🔘  INLINE TUGMA CALLBACKLARI  (prefiksi: "m_")
    # ══════════════════════════════════════════════════════════

    async def _mod_cb(self, callback: CallbackQuery):
        if not await self._is_admin(self.main_chat, callback.from_user.id):
            return await callback.answer("❌ Faqat adminlar!", show_alert=True)

        # m_ACTION_UID
        parts  = callback.data.split("_", 2)  # ['m', 'action', 'uid']
        action = parts[1]
        uid    = int(parts[2])
        admin  = callback.from_user.first_name or "Admin"

        # Nishon ma'lumotlarini olish
        try:
            m     = await self.bot.get_chat_member(self.main_chat, uid)
            fname = m.user.first_name or f"ID:{uid}"
            uname = f"@{m.user.username}" if m.user.username else "—"
        except Exception:
            fname, uname = f"ID:{uid}", "—"

        # Tugma klaviaturasini yangilash yordamchisi
        async def _refresh_kb():
            wc = await self._get_warn(uid)
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=self._mod_kb(uid, wc)
                )
            except Exception:
                pass

        # ─── WARN ────────────────────────────────────────────
        if action == "warn":
            if await self._is_admin(self.main_chat, uid):
                return await callback.answer("⛔ Adminni warn qilib bo'lmaydi!", show_alert=True)

            count = await self._get_warn(uid) + 1
            await self._set_warn(uid, count)

            # Kunlik warn statistikasini oshiramiz
            try:
                from __main__ import increment_daily_warn as _idw
                await _idw()
            except Exception:
                pass

            if count >= 3:
                await self.bot.ban_chat_member(chat_id=self.main_chat, user_id=uid)
                await self._set_warn(uid, 0)
                if self._inc_blocked:
                    await self._inc_blocked()
                try:
                    await callback.message.edit_text(
                        _action_card(
                            "🚫", "BAN (3/3 warn)", fname, uid, admin,
                            extra="🟥🟥🟥  3/3 warn → Avtomatik ban!"
                        ),
                        parse_mode="HTML",
                        reply_markup=self._unban_only_kb(uid)
                    )
                except Exception:
                    pass
                await self._log(
                    _log_card("🚫", "BAN (warn to'ldi)", fname, uname, uid, admin,
                               extra="🟥🟥🟥  3/3 → avtomatik ban"),
                    user_id=uid, unblock=True
                )
                await callback.answer("🚫 Ban qilindi!", show_alert=True)
            else:
                await _refresh_kb()
                await self._log(
                    _log_card("⚠️", "WARN (tugma)", fname, uname, uid, admin,
                               extra=f"{_warn_bar(count)}  {count}/3")
                )
                await callback.answer(f"⚠️ Warn: {count}/3")

        # ─── UNWARN ──────────────────────────────────────────
        elif action == "unwarn":
            count = await self._get_warn(uid)
            if count <= 0:
                return await callback.answer("ℹ️ Ogohlantirish yo'q.", show_alert=True)
            new_c = count - 1
            await self._set_warn(uid, new_c)
            await _refresh_kb()
            await self._log(
                _log_card("✅", "UNWARN (tugma)", fname, uname, uid, admin,
                           extra=f"{_warn_bar(new_c)}  {new_c}/3 qoldi")
            )
            await callback.answer(f"✅ Unwarn qilindi. Qoldi: {new_c}/3")

        # ─── MUTE ────────────────────────────────────────────
        elif action == "mute":
            if await self._is_admin(self.main_chat, uid):
                return await callback.answer("⛔ Adminni mute qilib bo'lmaydi!", show_alert=True)
            if self._check_bot_perm and not await self._check_bot_perm(self.main_chat, "can_restrict_members"):
                return await callback.answer("⚠️ Bot huquqi yo'q!", show_alert=True)
            await self.bot.restrict_chat_member(
                chat_id=self.main_chat, user_id=uid,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await self._log(_log_card("🔇", "MUTE (tugma)", fname, uname, uid, admin))
            await callback.answer(f"🔇 {fname} mute qilindi!")

        # ─── UNMUTE ──────────────────────────────────────────
        elif action == "unmute":
            await self.bot.restrict_chat_member(
                chat_id=self.main_chat, user_id=uid,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                )
            )
            await self._log(_log_card("🔊", "UNMUTE (tugma)", fname, uname, uid, admin))
            await callback.answer(f"🔊 {fname} unmute qilindi!")

        # ─── BAN ─────────────────────────────────────────────
        elif action == "ban":
            if await self._is_admin(self.main_chat, uid):
                return await callback.answer("⛔ Adminni ban qilib bo'lmaydi!", show_alert=True)
            if self._check_bot_perm and not await self._check_bot_perm(self.main_chat, "can_restrict_members"):
                return await callback.answer("⚠️ Bot huquqi yo'q!", show_alert=True)

            await self.bot.ban_chat_member(chat_id=self.main_chat, user_id=uid)
            await self._set_warn(uid, 0)
            if self._inc_blocked:
                await self._inc_blocked()
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=self._unban_only_kb(uid)
                )
            except Exception:
                pass
            await self._log(
                _log_card("🚫", "BAN (tugma)", fname, uname, uid, admin),
                user_id=uid, unblock=True
            )
            await callback.answer(f"🚫 {fname} banlandi!", show_alert=True)

        # ─── UNBAN ───────────────────────────────────────────
        elif action == "unban":
            try:
                await self.bot.unban_chat_member(
                    chat_id=self.main_chat, user_id=uid, only_if_banned=False
                )
            except Exception as ue:
                if "PARTICIPANT_ID_INVALID" not in str(ue):
                    log.warning(f"Unban tugma muammo: {ue}")
            await _refresh_kb()
            await self._log(_log_card("✅", "UNBAN (tugma)", fname, uname, uid, admin))
            await callback.answer(f"✅ {fname} unban qilindi!")

        # ─── ADMIN QO'SHISH ──────────────────────────────────
        elif action == "mkadm":
            if not (self._is_bot_admin and await self._is_bot_admin(callback.from_user.id)):
                return await callback.answer("❌ Sizda bunday huquq yo'q!", show_alert=True)
            if self._check_bot_perm and not await self._check_bot_perm(self.main_chat, "can_promote_members"):
                return await callback.answer("⚠️ Bot huquqi yo'q!", show_alert=True)

            await self.bot.promote_chat_member(
                chat_id=self.main_chat, user_id=uid,
                can_delete_messages  = True,
                can_restrict_members = True,
                can_pin_messages     = True,
                can_invite_users     = True,
            )
            await self._log(
                _log_card("👑", "ADMIN QO'SHILDI (tugma)", fname, uname, uid, admin)
            )
            await callback.answer(f"👑 {fname} admin qilindi!")

        # ─── ADMIN OLIB TASHLASH ─────────────────────────────
        elif action == "rmadm":
            if not (self._is_bot_admin and await self._is_bot_admin(callback.from_user.id)):
                return await callback.answer("❌ Sizda bunday huquq yo'q!", show_alert=True)

            await self.bot.promote_chat_member(
                chat_id=self.main_chat, user_id=uid,
                can_delete_messages  = False,
                can_restrict_members = False,
                can_pin_messages     = False,
                can_invite_users     = False,
                can_manage_chat      = False,
            )
            await self._log(
                _log_card("❌", "UNADMIN (tugma)", fname, uname, uid, admin)
            )
            await callback.answer(f"❌ {fname} admin emas!")

        else:
            await callback.answer("❓ Noma'lum amal.", show_alert=True)


# ══════════════════════════════════════════════════════════════
# 🌐  GLOBAL OBYEKT — main.py da shu bilan ishlang
# ══════════════════════════════════════════════════════════════
MOD = Moderator()


# ══════════════════════════════════════════════════════════════
# 📖  KOMANDALAR QO'LLANMASI
# ══════════════════════════════════════════════════════════════
HELP_TEXT = """
⚜ <b>MODERATSIYA KOMANDALARI</b>
{div}
⚠️ <b>WARN tizimi</b>
/warn  + reply | @user sabab  — ogohlantirish berish
/unwarn + reply | @user       — ogohlantirish olib tashlash
/warns                        — barcha warn'lar ro'yxati
{div}
🔇 <b>MUTE / UNMUTE</b>
/mute  + reply | @user sabab  — xabar yozishni bloklash
/unmute + reply | @user       — blokni olib tashlash
{div}
🚫 <b>BAN / UNBAN</b>
/ban  + reply | @user sabab   — guruhdan chiqarish
/unban + reply | @user        — guruhga qaytarish
{div}
👑 <b>ADMIN (faqat bot-adminlar)</b>
/admin  + reply | @user       — admin qilish
/unadmin + reply | @user      — admin olib tashlash
{div}
🪪 <b>MA'LUMOT</b>
/info + reply | @user         — to'liq profil + tugmalar
/id   + reply | @user         — tezkor kartochka
{div}
💡 Barcha amallar log kanalga yuboriladi.
""".format(div="━" * 24)