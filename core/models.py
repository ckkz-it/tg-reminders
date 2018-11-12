from django.db import models

import arrow


def get_default_remind_date():
    return arrow.now('Europe/Moscow').shift(minutes=10).datetime


class TelegramChat(models.Model):
    telegram_id = models.TextField(unique=True)
    full_name = models.TextField(blank=True)
    telegram_username = models.TextField()
    date_joined = models.DateTimeField(auto_now_add=True)


class Reminder(models.Model):
    telegram_chat = models.ForeignKey('TelegramChat', on_delete=models.CASCADE)
    date = models.DateTimeField(default=get_default_remind_date)
    message = models.TextField(blank=True)
    repeat_count = models.IntegerField(default=0)
    repeat_period = models.IntegerField(default=10)
    done = models.BooleanField(default=False)
    processing = models.BooleanField(default=False)
