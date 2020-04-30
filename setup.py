import telebot
import os
from flask import Flask, request
import time
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import random

DATABASE_URL = os.environ['DATABASE_URL']

'''TOKEN = '1239481186:AAGj2GoeUJHGVXYaYcXSUz4igo-4pT8As3M'
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)
URL = os.environ.get('URL')


@bot.message_handler(commands=['start'])
def bot_start(message):
    bot.send_message(message.chat.id, 'hi')


@bot.message_handler(content_types=['text'])
def text_message(message):
    bot.reply_to(message, message.text)
    print(message.text)


@server.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://test-etis.herokuapp.com/' + TOKEN)
    return "!", 200


if __name__ == "__main__":
    print('зачем-то зашел в иф')
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))


while True:
    print('Кэжуально делаю дела, пока принимаю сообщения')
    bot.send_message(473056406,'99')
    time.sleep(6)'''
TOKEN = os.environ.get('BOT_TOKEN')


def run(updater):
    PORT = int(os.environ.get("PORT", "8443"))
    HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN)
    updater.bot.set_webhook(os.environ.get('APP_NAME') + TOKEN)


def start_handler(bot, update):
    # Creating a handler-function for /start command
    update.message.reply_text('Привет! Нажмите /login для ввода логина и пароля')


def login_handler(bot, update):
    # Creating a handler-function for /random command
    login_dict[update.message.from_user.id] = 'Не введён'
    pass_dict[update.message.from_user.id] = 'Не введён'
    update.message.reply_text('Введите логин:')
    login_flag_dict[update.message.from_user.id] = True


def user_data_handler(bot, update):
    mes = update.message.reply_text(
        'Логин: ' + login_dict.get(update.message.from_user.id) + '\n Пароль: ' + pass_dict.get(update.message.from_user.id))
    time.sleep(6)
    bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)


def text_handler(bot, update):
    if login_flag_dict.get(update.message.from_user.id):
        login_dict[update.message.from_user.id] = update.message.text
        login_flag_dict[update.message.from_user.id] = False
        bot.send_message(update.message.chat.id, 'Введите пароль: ')
        password_flag_dict[update.message.from_user.id] = True
    elif password_flag_dict.get(update.message.from_user.id):
        pass_dict[update.message.from_user.id] = update.message.text
        password_flag_dict[update.message.from_user.id] = False
        update.message.reply_text('Для просмотра введённых данных нажмите /user_data')
        update.message.reply_text('Для повторного ввода данных нажмите /login')
        update.message.reply_text('Для авторизации нажмите /authorize')


if __name__ == '__main__':
    updater = Updater(TOKEN)

    updater.dispatcher.add_handler(CommandHandler("start", start_handler))
    updater.dispatcher.add_handler(CommandHandler("login", login_handler))
    updater.dispatcher.add_handler(CommandHandler("user_data", user_data_handler))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), text_handler))

    run(updater)

auth_dict = {}
login_flag_dict = {}
password_flag_dict = {}
session_dict = {}  # словарь всех подключений
login_dict = {}  # словарь логинов
pass_dict = {}  # словарь паролей

while True:
    print('Кэжуально делаю дела, пока принимаю сообщения')
    time.sleep(6)
