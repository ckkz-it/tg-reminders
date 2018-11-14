from telegram.ext import CommandHandler, MessageHandler, Filters

import logging
import arrow
import collections

from .models import TelegramChat, Reminder

logger = logging.getLogger(__name__)


def remind_month_and_day(now):
    answer = yield 'Which day to set reminder? Type "-" to set today!'
    month = now.month
    if answer.text == '-':
        return month, now.day
    else:
        while True:
            if answer.text == '-':
                return month, now.day
            try:
                day = int(answer.text)
                if day < 1 or day > 31:
                    answer = yield 'Day should be from 1 to 31'
                    continue
                break
            except ValueError:
                answer = yield 'Day should be a number'

        if now.day > day:
            answer = yield (f'Day {day} is already passed. Did you mean other month?\nIf so, '
                            f'specify which one, type "-" to choose day again')
            while True:
                if answer.text == '-':
                    # Restart
                    yield None
                try:
                    month = int(answer.text)
                    if month < 1 or month > 12:
                        answer = yield 'Month should be from 1 to 12'
                        continue
                    break
                except ValueError:
                    answer = yield 'Month should be a number'
        return month, day


def remind_hour(now, month, day):
    if month != now.month:
        answer = yield f'Ok, day set to {day} of {month} month, which hour?'
    else:
        answer = yield f'Ok, day set to {day}, which hour?'
    return answer.text


def remind_minute(hour):
    answer = yield f'Hour is {hour}, what about minutes?'
    while True:
        try:
            minute = int(answer.text)
            if minute < 0 or minute > 59:
                answer = yield 'Minute should be a number'
                continue
            break
        except ValueError:
            answer = yield 'Minute should be a number'
    return minute


def remind_message(minute):
    answer = yield f'Minute is {minute}. Any message? "-" for empty'
    if answer.text == '-':
        return answer, ''
    else:
        return answer, answer.text


def remind_dialog():
    now = arrow.now('Europe/Moscow')
    year = now.year

    month, day = yield from remind_month_and_day(now)
    if month < now.month:
        year += 1
    hour = yield from remind_hour(now, month, day)
    minute = yield from remind_minute(hour)
    answer, message = yield from remind_message(minute)

    date = arrow.get(
        f'{year} {month} {day} {hour} {minute} Europe/Moscow', [
            'YYYY MM D HH m ZZZ',
            'YYYY M D HH m ZZZ',
            'YYYY M D H m ZZZ',
            'YYYY MM D HH m ZZZ',
            'YYYY MM DD HH m ZZZ',
            'YYYY M DD H m ZZZ',
            'YYYY M DD HH m ZZZ'
        ]
    )

    if date < now:
        yield 'Date must be in future'
        return

    chat = TelegramChat.objects.get(telegram_id=answer.chat_id)
    reminder = Reminder.objects.create(
        telegram_chat=chat, date=date.datetime, message=message
    )

    text = f'Will remind you {date.humanize()} ({date.format("HH:mm, D MMMM, dddd, YYYY")})'
    if message:
        text += f'\nReminder: {message}'
    yield text


class TelegramHandlers(object):
    def __init__(self):
        self.help_text = '/remind  -  type this command to start setting reminder'
        self.start_text = 'This is a simple reminder, type /help to see how to use it. Basic command is /remind'
        self.remind_dialog = collections.defaultdict(remind_dialog)

    @staticmethod
    def unknown(bot, update):
        bot.send_message(chat_id=update.message.chat_id, text='Sorry, I didn\'t understand that command.')

    def help(self, bot, update):
        bot.send_message(chat_id=update.message.chat_id, text=self.help_text)

    def start(self, bot, update):
        tg_user = update.message.from_user
        user, created = TelegramChat.objects.get_or_create(telegram_id=tg_user.id)
        user.telegram_username = tg_user.username
        user.full_name = tg_user.full_name
        user.save()

        self.remind_dialog.pop(update.message.chat_id, None)

        message = self.start_text
        if not created:
            message = f'Hello, {user.full_name}'

        bot.send_message(chat_id=update.message.chat_id, text=message)

    def remind(self, bot, update):
        logger.info(f'Received: {update.message}')
        chat_id = update.message.chat_id
        if update.message.text == '/remind':
            # Start new
            self.remind_dialog.pop(chat_id, None)
        if update.message.text == '/cancel':
            self.remind_dialog.pop(chat_id, None)
            bot.sendMessage(chat_id=chat_id, text='Canceled')
            return
        if chat_id in self.remind_dialog:
            try:
                answer = self.remind_dialog[chat_id].send(update.message)
                if answer is None:
                    # Restart
                    raise StopIteration
            except StopIteration:
                del self.remind_dialog[chat_id]
                return self.remind(bot, update)
        else:
            answer = next(self.remind_dialog[chat_id])
        logger.info(f'Answer: {answer}')
        bot.sendMessage(chat_id=chat_id, text=answer)

    @staticmethod
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

    def get_handlers(self):
        return [
            CommandHandler('start', self.start),
            CommandHandler('help', self.help),
            CommandHandler('remindi', self.remindi, pass_args=True),
            MessageHandler(Filters.text | Filters.command, self.remind),
            MessageHandler(Filters.text, self.unknown)
        ]
