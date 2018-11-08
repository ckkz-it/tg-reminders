from django.db import models


# Create your models here.


class TelegramChat(models.Model):
    telegram_id = models.TextField()
    telegram_username = models.TextField()
    date_joined = models.DateTimeField(auto_now_add=True)
