from django.db import models

import datetime


# Create your models here.

def get_default_remind_date():
    return datetime.datetime.utcnow() + datetime.timedelta(minutes=10)


class TelegramChat(models.Model):
    telegram_id = models.TextField(unique=True)
    full_name = models.TextField(blank=True)
    telegram_username = models.TextField()
    date_joined = models.DateTimeField(auto_now_add=True)


class Reminder(models.Model):
    telegram_chat = models.ForeignKey('TelegramChat', on_delete=models.CASCADE)
    date = models.DateTimeField(default=get_default_remind_date)
    message = models.TextField(blank=True)
    repeat = models.IntegerField(default=0)
    repeat_period = models.IntegerField(default=10)
