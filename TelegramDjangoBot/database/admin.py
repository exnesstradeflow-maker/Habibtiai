import asyncio
from django.contrib import admin
from .models import BadWord, UserWarning, GroupMessage
from aiogram import Bot
from tgbot.config import TELEGRAM_TOKEN, MAIN_CHAT_ID

@admin.register(BadWord)
class BadWordAdmin(admin.ModelAdmin):
    list_display = ('word',)
    search_fields = ('word',)

@admin.register(UserWarning)
class UserWarningAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'count')
    search_fields = ('user_id',)

@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ('text', 'created_at')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            async def send_to_group():
                bot = Bot(token=TELEGRAM_TOKEN)
                try:
                    await bot.send_message(chat_id=MAIN_CHAT_ID, text=obj.text, parse_mode="HTML")
                except Exception as e:
                    print(f"Xatolik: {e}")
                finally:
                    await bot.session.close()
            
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(send_to_group())
            except RuntimeError:
                asyncio.run(send_to_group())
