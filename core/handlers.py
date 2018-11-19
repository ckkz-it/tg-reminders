import logging
import arrow
import collections
from telegram.ext import CommandHandler, MessageHandler, Filters

from .models import TelegramChat, Reminder, Todo
from .generators import remind_dialog, todo_dialog
from .telegram_api import Message, Markdown

logger = logging.getLogger(__name__)


class TelegramHandlers(object):
    def __init__(self):
        self.help_text = '/remind  -  type this command to start setting reminder'
        self.start_text = 'This is a simple reminder, type /help to see how to use it. Basic command is /remind'
        self.remind_dialog = collections.defaultdict(remind_dialog)
        self.todo_dialog = collections.defaultdict(todo_dialog)
        self.current_command = None
        self.function_commands_map = {
            'remind': self.remind,
            'addtodo': self.addtodo,
            'todos': self.todos,
        }

    @staticmethod
    def send_message(bot, chat_id, text):
        if isinstance(text, str):
            text = Message(text)
        bot.send_message(chat_id=chat_id, text=text.body, **text.options)

    def unknown(self, bot, update):
        self.send_message(bot, update.message.chat_id, 'Sorry, I did not understand that command.')

    def help(self, bot, update):
        self.send_message(bot, update.message.chat_id, self.help_text)

    def start(self, bot, update):
        tg_user = update.message.from_user
        user, created = TelegramChat.objects.get_or_create(telegram_id=tg_user.id)
        user.telegram_username = tg_user.username
        user.full_name = tg_user.full_name
        user.save()

        self.remind_dialog.pop(update.message.chat_id, None)

        if created:
            message = self.start_text
        else:
            message = f'Hello, *{user.full_name}*'

        self.send_message(bot, update.message.chat_id, Markdown(message))

    def handle_message(self, bot, update):
        """
        Function to handle commands, which have some processing time. To answer question etc.
        """
        if '/' not in update.message.text:
            if self.current_command is not None:
                return self.function_commands_map[self.current_command](bot, update)
        return self.unknown(bot, update)

    def addtodo(self, bot, update):
        logger.info(f'[addtodo]: Received: {update.message}')
        self.current_command = 'addtodo'
        chat_id = update.message.chat_id

        if update.message.text == '/addtodo':
            # Start new
            self.todo_dialog.pop(chat_id, None)
            answer = next(self.todo_dialog[chat_id])
            logger.info(f'[addtodo] Answer: {answer}')
            self.send_message(bot, chat_id, answer)
            return
        if update.message.text == '/cancel':
            self.todo_dialog.pop(chat_id, None)
            self.send_message(bot, chat_id, 'Canceled')
            return

        if chat_id in self.todo_dialog:
            try:
                answer = self.todo_dialog[chat_id].send(update.message)
            except StopIteration:
                del self.todo_dialog[chat_id]
                self.current_command = None
                return self.handle_message(bot, update)
        else:
            answer = next(self.todo_dialog[chat_id])
        logger.info(f'[addtodo] Answer: {answer}')
        self.send_message(bot, chat_id, answer)

    def addtodoi(self, bot, update, args):
        if not len(args):
            self.send_message(bot, update.message.chat_id, 'Specify a todo message')
            return

        message = ' '.join(map(str, args))
        todo = Todo.objects.create(message=message)
        text = f'Todo created\n*Message*: {todo.message}'

        self.send_message(bot, update.message.chat_id, Markdown(text))

    def todos(self, bot, update, args):
        """
        List all todos for current user. If category name is provided, list todos only
        related to this category. Category is provided in args
        """
        options = dict()

        if len(args):
            if len(args) > 1:
                self.send_message(bot, update.message.chat_id, Markdown('Category should contain only *one* word'))
                return
            else:
                options.update({'category': args[0]})

        todos = Todo.objects.filter(
            telegram_chat__telegram_id=update.message.chat_id, **options
        ).order_by('-date_created').order_by('category')

        text = ''
        if args and args[0]:  # category
            text += f'*{args[0]}*\n'
            for todo in todos:
                if todo.done:
                    text += f'`{todo.message} ({todo.id})`\n'
                else:
                    text += f'{todo.message} ({todo.id})\n'
        else:
            for todo in todos:
                if todo.done:
                    text += f'`{todo.category}: {todo.message} ({todo.id})`\n'
                else:
                    text += f'*{todo.category}:* {todo.message} ({todo.id})\n'

        if not text:
            text = 'You have no todos'

        self.send_message(bot, update.message.chat_id, Markdown(text))

    def marktodo(self, bot, update, args):
        """
        Mark tod0(s) with id(s) specified in args as done
        """
        if not len(args):
            self.send_message(bot, update.message.chat_id, 'Specify todo id(s)')
            return

        marked_ids = list()
        not_found_ids = list()
        for todo_id in args:
            try:
                todo = Todo.objects.get(id=todo_id)
                todo.done = True
                todo.save(update_fields=['done'])
                marked_ids.append(todo_id)
            except Todo.DoesNotExist:
                not_found_ids.append(todo_id)

        text = f'*Marked todos:* {", ".join(map(str, marked_ids))}'
        if not_found_ids:
            text += f'\n*Not found todos:* {", ".join(map(str, not_found_ids))}'

        self.send_message(bot, update.message.chat_id, Markdown(text))

    def removetodo(self, bot, update, args):
        """
        Remove tod0(s) with id(s) specified in args
        """
        if not len(args):
            self.send_message(bot, update.message.chat_id, 'Specify todo id(s)')
            return

        removed_ids = list()
        not_found_ids = list()
        for todo_id in args:
            try:
                todo = Todo.objects.get(id=todo_id)
                todo.delete()
                removed_ids.append(todo_id)
            except Todo.DoesNotExist:
                not_found_ids.append(todo_id)

        text = f'*Deleted todos:* {", ".join(map(str, removed_ids))}'
        if not_found_ids:
            text += f'\n*Not found todos:* {", ".join(map(str, not_found_ids))}'
        self.send_message(bot, update.message.chat_id, Markdown(text))

    def remind(self, bot, update):
        logger.info(f'[remind] Received: {update.message}')
        self.current_command = 'remind'
        chat_id = update.message.chat_id

        if update.message.text == '/remind':
            # Start new
            self.remind_dialog.pop(chat_id, None)
            answer = next(self.remind_dialog[chat_id])
            logger.info(f'Answer: {answer}')
            self.send_message(bot, chat_id, answer)
            return
        if update.message.text == '/cancel':
            self.remind_dialog.pop(chat_id, None)
            self.send_message(bot, chat_id, 'Canceled')
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
        self.send_message(bot, chat_id, answer)

    def remindi(self, bot, update, args):
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
            self.send_message(bot, update.message.chat_id, 'Date must be in future')
            return

        chat = TelegramChat.objects.get(telegram_id=update.message.chat_id)
        reminder = Reminder.objects.create(
            telegram_chat=chat, date=date.datetime, message=message
        )
        text = f'Will remind you *{date.humanize()}* ({date.format("HH:mm, D MMMM, dddd, YYYY")})'
        if message:
            text += f'\n*Reminder:* {message}'
        self.send_message(bot, update.message.chat_id, Markdown(text))

    def get_handlers(self):
        return [
            CommandHandler('start', self.start),
            CommandHandler('help', self.help),
            CommandHandler('remindi', self.remindi, pass_args=True),
            CommandHandler('remind', self.remind),
            CommandHandler('todos', self.todos, pass_args=True),
            CommandHandler('marktodo', self.marktodo, pass_args=True),
            CommandHandler('addtodoi', self.addtodoi, pass_args=True),
            CommandHandler('addtodo', self.addtodo),
            CommandHandler('removetodo', self.removetodo, pass_args=True),
            MessageHandler(Filters.text | Filters.command, self.handle_message),
            MessageHandler(Filters.text | Filters.command, self.unknown)
        ]
