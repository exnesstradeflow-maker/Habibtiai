from django.db import models

class BadWord(models.Model):
    word = models.CharField(max_length=100, unique=True, verbose_name="Taqiqlangan so'z")

    def __str__(self):
        return self.word

    class Meta:
        verbose_name = "Taqiqlangan so'z"
        verbose_name_plural = "Taqiqlangan so'zlar"


class UserWarning(models.Model):
    user_id = models.BigIntegerField(primary_key=True, verbose_name="Foydalanuvchi ID")
    count = models.IntegerField(default=0, verbose_name="Ogohlantirishlar soni")

    def __str__(self):
        return f"ID: {self.user_id} - Ogohlantirishlar: {self.count}"

    class Meta:
        verbose_name = "Foydalanuvchi ogohlantirishi"
        verbose_name_plural = "Foydalanuvchilar ogohlantirishlari"


class AdminViolation(models.Model):
    user_id = models.BigIntegerField(primary_key=True, verbose_name="Admin ID")
    count = models.IntegerField(default=0, verbose_name="Qoida buzishlar soni")

    def __str__(self):
        return f"Admin: {self.user_id} - Buzishlar: {self.count}"


class UserLink(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    link = models.TextField()
    log_msg_id = models.BigIntegerField()


class InviteLink(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    link = models.TextField()


class GroupMessage(models.Model):
    text = models.TextField(verbose_name="Xabar matni")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Xabar: {self.text[:30]}..."

    class Meta:
        verbose_name = "Guruhga xabar yuborish"
        verbose_name_plural = "Guruhga xabar yuborish"
