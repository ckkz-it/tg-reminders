from telegram.ext import CommandHandler, MessageHandler, Filters

import logging
import datetime
import arrow

from .models import TelegramChat, Reminder

logger = logging.getLogger('MAIN')

help_text = '/remind `date` `:message` :`repeat` :`repeat_times` - set reminder, ":" are optional arguments'
start_text = 'This is a simple reminder, type /help to see how to use it.'


def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='Sorry, I didn\'t understand that command.')


def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=help_text)


def start(bot, update):
    tg_user = update.message.from_user
    user, created = TelegramChat.objects.get_or_create(telegram_id=tg_user.id)
    user.telegram_username = tg_user.username
    user.full_name = tg_user.full_name
    user.save()

    message = start_text
    if not created:
        message = f'Hello, {user.full_name}'

    bot.send_message(chat_id=update.message.chat_id, text=message)


def remind(bot, update, args):
    date = args[0]
    day, hm = date.split('-')
    hour, minute = hm.split(':')
    # message = ('Use this syntax /remind `date` `:message` :`repeat` :`repeat_times` - ":" are optional arguments. '
    #            'Use /help for more information')
    # date = arrow.get(2018, 11, int(day), int(hour), int(minute))
    date = arrow.get(f'2018 11 {date}', 'YYYY MM D-HH:mm')
    chat = TelegramChat.objects.get(telegram_id=update.message.chat_id)
    reminder = Reminder.objects.create(telegram_chat=chat, date=date.datetime)
    message = f'Will remind you {date.humanize()} ({date.format("DD-MM-YYYY HH:mm")})'
    bot.send_message(chat_id=update.message.chat_id, text=message)


HANDLERS = [
    CommandHandler('start', start),
    CommandHandler('help', help),
    CommandHandler('remind', remind, pass_args=True),
    MessageHandler(Filters.text, unknown)
]
