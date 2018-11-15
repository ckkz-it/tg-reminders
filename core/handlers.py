from telegram.ext import CommandHandler, MessageHandler, Filters

import logging
import arrow
import collections

from .models import TelegramChat, Reminder
from .generators import remind_dialog

logger = logging.getLogger(__name__)


class TelegramHandlers(object):
    def __init__(self):
        self.help_text = '/remind  -  type this command to start setting reminder'
        self.start_text = 'This is a simple reminder, type /help to see how to use it. Basic command is /remind'
        self.remind_dialog = collections.defaultdict(remind_dialog)
        self.current_command = None
        self.function_commands_map = {
            'remind': self.remind,
            'todo': self.todo
        }

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

    def handle_message(self, bot, update):
        if '/' not in update.message.text:
            if self.current_command is not None:
                return self.function_commands_map[self.current_command](bot, update)
            else:
                return self.unknown(bot, update)
    
    def remind(self, bot, update):
        logger.info(f'Received: {update.message}')
        chat_id = update.message.chat_id

        if update.message.text == '/remind':
            # Start new
            self.remind_dialog.pop(chat_id, None)
            answer = next(self.remind_dialog[chat_id])
            logger.info(f'Answer: {answer}')
            bot.sendMessage(chat_id=chat_id, text=answer)
            return
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
            MessageHandler(Filters.text | Filters.command, self.handle_message),
            MessageHandler(Filters.text, self.unknown)
        ]
