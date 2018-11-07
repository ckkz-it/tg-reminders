from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


class TelegramBot(object):

    def __init__(self, token):
        self.updater = Updater(token=token)
        handler = MessageHandler(Filters.text | Filters.command, self.handle_message)
        self.updater.dispatcher.add_handler(handler)
        self.start()

    def start(self):
        self.updater.start_polling()

    def stop(self):
        self.updater.stop()

    @staticmethod
    def unknown(bot, update):
        bot.send_message(chat_id=update.message.chat_id, text='Sorry, I didn\'t understand that command.')

    def handle_message(self, bot, update):
        print('Received', update.message)
        chat_id = update.message.chat_id
        if update.message.text == '/start':
            self.unknown(bot, update)
        elif update.message.text == '/stop':
            self.stop()
