from telegram.ext import CommandHandler, MessageHandler, Filters

import logging
import arrow

from .models import TelegramChat, Reminder

help_text = '/remindi `day` `hour` `:minute` `:message` - set reminder, ":" are optional arguments'
start_text = 'This is a simple reminder, type /help to see how to use it.'


# message = ('Use this syntax /remind `day` `hour` `minute` `:message` :`repeat` :`repeat_times` -
# ":" are optional arguments. '
#            'Use /help for more information')

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


def remindi(bot, update, args):
    if len(args) == 0:
        bot.send_message(chat_id=update.message.chat_id, text='Provide args')
        return
    now = arrow.now('Europe/Moscow')  # TODO: set timezone
    year = now.year
    month = now.month

    message = ''
    if len(args) > 3:
        for i in range(3, len(args)):
            message += f'{args[i]} '

    minute = args[2] if len(args) > 2 else 0
    day, hour, minute = args[0], args[1], minute
    date = arrow.get(
        f'{year} {month} {day} {hour} {minute} Europe/Moscow', 'YYYY MM D HH m ZZZ'
    )  # TODO: set timezone

    if date < now:
        bot.send_message(chat_id=update.message.chat_id, text='Date must be in future')
        return

    chat = TelegramChat.objects.get(telegram_id=update.message.chat_id)
    reminder = Reminder.objects.create(
        telegram_chat=chat, date=date.datetime, message=message
    )
    text = f'Will remind you {date.humanize()} ({date.format("HH:mm, D MMMM, dddd, YYYY")})'
    if message:
        text += f'\nReminder: {message}'
    bot.send_message(chat_id=update.message.chat_id, text=text)


HANDLERS = [
    CommandHandler('start', start),
    CommandHandler('help', help),
    CommandHandler('remindi', remindi, pass_args=True),
    MessageHandler(Filters.text, unknown)
]
