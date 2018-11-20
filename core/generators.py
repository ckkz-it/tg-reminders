import arrow
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from .models import TelegramChat, Reminder, Todo
from .telegram_api import Message, Markdown


def remind_dialog():
    now = arrow.now('Europe/Moscow')
    year = now.year
    options = dict()

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

    if date < arrow.now('Europe/Moscow'):
        yield 'Date must be in future'
        return

    repeat_count, repeat_period = yield from reminder_repeat()
    if repeat_count and repeat_period:
        if repeat_count == 1:
            repeat_count = 0
        options.update({'repeat_count': repeat_count, 'repeat_period': repeat_period})

    chat = TelegramChat.objects.get(telegram_id=answer.chat_id)
    reminder = Reminder.objects.create(
        telegram_chat=chat, date=date.datetime, message=message, **options
    )

    text = f'Will remind you {date.humanize()} ({date.format("HH:mm, D MMMM, dddd, YYYY")})'
    if message:
        text += f'\nReminder: {message}'
    yield text


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
                if 1 <= day <= 31:
                    break
                answer = yield 'Day should be from 1 to 31'
            except ValueError:
                answer = yield 'Day should be a number'

        if now.day > day:
            answer = yield (f'Day {day} is already passed. Did you mean other month?\nIf so, '
                            f'specify which one, type "-" to choose day again')
            month = yield from check_if_valid_date_piece(
                answer, 'Month should be from 1 to 12', 'Month should be a number',
                0, 13, with_default=True, default_value=None
            )
        return month, day


def remind_hour(now, month, day):
    if month != now.month:
        answer = yield f'Ok, day set to {day} of {month} month, which hour?'
    else:
        answer = yield f'Ok, day set to {day}, which hour?'
    return answer.text


def remind_minute(hour):
    answer = yield f'Hour is {hour}, what about minutes?'
    minute = yield from check_if_valid_date_piece(
        answer, 'Minute should be a number', 'Minute should be a number', -1, 60
    )
    return minute


def remind_message(minute):
    answer = yield f'Minute is {minute}. Any message? "-" for empty'
    if answer.text == '-':
        return answer, ''
    else:
        return answer, answer.text


def reminder_repeat():
    should_repeat = ask_yes_or_no('Should repeat reminder?')
    if should_repeat:
        answer = yield 'How many times?'
        repeat_count = yield from check_if_valid_date_piece(
            answer, 'Should be less than 100 and bigger than 0', 'It should be a number', -1, 100
        )
        answer = yield 'What period between reminds? In minutes.'

        repeat_period = yield from check_if_valid_date_piece(
            answer, 'Should be less than 100', 'It should be a number', 1, 100
        )

        return repeat_count, repeat_period
    else:
        return None, None


def todo_dialog(chat_id=213256634):
    answer = yield 'Write a new todo message'
    message = answer.text

    telegram_chat = TelegramChat.objects.get(telegram_id=chat_id)

    categories = list()
    categories_buttons = list()
    for todo in Todo.objects.filter(telegram_chat=telegram_chat, done=False):
        if todo.category not in categories:
            categories.append(todo.category)
            categories_buttons.append([KeyboardButton(todo.category)])

    reply_markup = ReplyKeyboardMarkup(categories_buttons, one_time_keyboard=True, resize_keyboard=True)
    answer = yield Message('Choose category or create new one', reply_markup=reply_markup)
    category = answer.text

    todo = Todo.objects.create(telegram_chat=telegram_chat, message=message, category=category)

    reply_markup = ReplyKeyboardRemove()
    yield Markdown(
        f'Todo created\n*Message:* {todo.message}\n*Category:* {todo.category}', reply_markup=reply_markup
    )


def ask_yes_or_no(question):
    answer = yield question
    while not (
            'yes' in answer.text.lower() or 'no' in answer.text.lower() or
            'y' in answer.text.lower() or 'n' in answer.text.lower()
    ):
        answer = yield '"yes" or "no?"'
    return 'yes' in answer.text.lower() or 'y' in answer.text.lower()


def check_if_valid_date_piece(answer, message1, message2, more_than, less_than, with_default=False,
                              default_value=None):
    while True:
        if with_default and answer.text == '-':
            if default_value is None:
                yield None
            else:
                return default_value
        try:
            value_to_check = int(answer.text)
            if more_than < value_to_check < less_than:
                break
            answer = yield message1
        except ValueError:
            answer = yield message2
    return value_to_check
