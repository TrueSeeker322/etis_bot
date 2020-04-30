import os
import time
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from etis import *
import psycopg2
from contextlib import closing

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
        'Логин: ' + login_dict.get(update.message.from_user.id) + '\n Пароль: ' + pass_dict.get(
            update.message.from_user.id))
    time.sleep(6)
    bot.delete_message(chat_id=update.message.chat.id, message_id=mes.message_id)


def auth_handler(bot, update):
    if login_dict.get(update.message.from_user.id) == 'Не введён' or \
            login_dict.get(update.message.from_user.id) is None or \
            pass_dict.get(update.message.from_user.id) == 'Не введён' or \
            pass_dict.get(update.message.from_user.id) is None:
        bot.send_message(update.message.chat.id, 'Не ввёден логин или пароль. /login')
    else:
        auth_data = {'p_redirect'.encode('cp1251'): 'stu.timetable'.encode('cp1251'),
                     'p_username'.encode('cp1251'): login_dict[update.message.from_user.id].encode('cp1251'),
                     'p_password'.encode('cp1251'): pass_dict[update.message.from_user.id].encode('cp1251')}
        session_dict[update.message.from_user.id] = requests.Session()  # добавление подключения в словарь
        if authentication(auth_data, session_dict[update.message.from_user.id]):
            with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Обновление БД
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM tg_user_data WHERE tg_id = %(tg_id)s;",
                                   {'tg_id': str(update.message.from_user.id)})
                    if not cursor.fetchall():
                        cursor.execute(
                            "INSERT INTO tg_user_data(tg_id, etis_login, etis_pass) VALUES (%(tg_id)s,%(etis_login)s,%(etis_pass)s);",
                            {'tg_id': str(update.message.from_user.id),
                             'etis_login': login_dict[update.message.from_user.id],
                             'etis_pass': pass_dict[update.message.from_user.id]})
                        cursor.execute('SELECT * FROM tg_user_data;')
                    else:
                        cursor.execute(
                            "UPDATE tg_user_data SET etis_login = %(etis_login)s, etis_pass = %(etis_pass)s WHERE tg_id= %(tg_id)s;",
                            {'tg_id': str(update.message.from_user.id),
                             'etis_login': login_dict[update.message.from_user.id],
                             'etis_pass': pass_dict[update.message.from_user.id]})
                    conn.commit()
            update.message.reply_text('Вход успешен. Для запуска работы бота нажмите /bot_start: ')
            auth_dict[update.message.from_user.id] = True
        else:
            del session_dict[update.message.from_user.id]
            update.message.reply_text('Неверный логин или пароль. Пожалуйста, повторите ввод /login. Для '
                                      'просмотра введённых данных нажмите /user_data')
            auth_dict[update.message.from_user.id] = False


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
    updater.dispatcher.add_handler(CommandHandler("authorize", auth_handler))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), text_handler))

    run(updater)

auth_dict = {}
login_flag_dict = {}
password_flag_dict = {}
session_dict = {}  # словарь всех подключений
login_dict = {}  # словарь логинов
pass_dict = {}  # словарь паролей

while True:
    print('Тупа работаю')
    time.sleep(6)
