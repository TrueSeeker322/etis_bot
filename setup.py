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
            chat_dict[update.message.from_user.id] = update.message.chat_id
        else:
            del session_dict[update.message.from_user.id]
            update.message.reply_text('Неверный логин или пароль. Пожалуйста, повторите ввод /login. Для '
                                      'просмотра введённых данных нажмите /user_data')
            auth_dict[update.message.from_user.id] = False
            chat_dict[update.message.from_user.id] = update.message.chat_id


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


auth_dict = {}  # словарь с подключениями для пользователей
chat_dict = {}  # словарь с id чатов
login_flag_dict = {}
password_flag_dict = {}
session_dict = {}  # словарь всех подключений
login_dict = {}  # словарь логинов
pass_dict = {}  # словарь паролей

if __name__ == '__main__':
    updater = Updater(TOKEN)

    updater.dispatcher.add_handler(CommandHandler("start", start_handler))
    updater.dispatcher.add_handler(CommandHandler("login", login_handler))
    updater.dispatcher.add_handler(CommandHandler("user_data", user_data_handler))
    updater.dispatcher.add_handler(CommandHandler("authorize", auth_handler))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), text_handler))

    run(updater)
    while True:
        for user_auth in auth_dict:
            if auth_dict.get(user_auth):
                print('проверяю юзера ', user_auth)
                quarry_array = '{'  # строка для вывода информации об оценках в бд
                names_array = '{'  # строка для вывода информации об предметах в бд
                table_array, table_names = info_scrapping(session_dict.get(user_auth))
                for i in table_array:  # формирование строки querry_array
                    quarry_array += '{'
                    for j in i:
                        j = j.replace('"', '*')
                        quarry_array += '"' + j + '", '
                    quarry_array = quarry_array[:len(quarry_array) - 1]
                    quarry_array = quarry_array[:len(quarry_array) - 1]
                    quarry_array += '}, '
                quarry_array = quarry_array[:len(quarry_array) - 1]
                quarry_array = quarry_array[:len(quarry_array) - 1]
                quarry_array += '}'
                for i in table_names:  # формирование строки names_array
                    i = i.replace('"', '*')
                    i = i.replace("'", '*')
                    names_array += '"' + i + '", '
                names_array = names_array[:len(names_array) - 1]
                names_array = names_array[:len(names_array) - 1]
                names_array += '}'
                with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Обновление БД
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT table_array, table_names FROM user_tables WHERE tg_id = %(tg_id)s",
                                       {'tg_id': str(user_auth)})
                        if not cursor.fetchone():  # если в бд еще нет такой записи
                            cursor.execute("DELETE FROM user_tables WHERE tg_id = %(tg_id)s",
                                           {'tg_id': str(user_auth)})
                            cursor.execute(
                                "INSERT INTO user_tables(tg_id,table_array,table_names) VALUES (%(tg_id)s,%(table_array)s,%(table_names)s)",
                                {'tg_id': str(user_auth), 'table_array': quarry_array,
                                 'table_names': names_array})
                            conn.commit()
                        else:  # если в бд есть такая запись, то проверим на сходство данных
                            cursor.execute("SELECT table_array, table_names FROM user_tables WHERE tg_id = %(tg_id)s",
                                           {'tg_id': str(user_auth)})
                            temp_counter = 0
                            fetch = cursor.fetchone()
                            temp_tables = fetch[0]
                            temp_names = fetch[1]
                            is_new_trimester = False
                            for i in table_names:
                                if i != temp_names[temp_counter]:  # если собранная информация по предметам не совпадает с текущей
                                    is_new_trimester = True  # флаг нового триместра, если True значит только обновляем инфу о новых предметах и не проверяем на совпадение
                                temp_counter += 1
                            if not is_new_trimester:  # если триместр не новый то проверка на совпадение
                                temp_counter = 0
                                is_DB_update_needed = False  # нужно ли обновить БД с новыми оценками
                                for i in table_array:  # проверям сохраненную информацию и ту, которую спарсили только что, на совпадение
                                    if i[3] != temp_tables[temp_counter][3]:
                                        new_mark_message = 'У вас новая оценка!\nПредмет: {0}\nКонтрольная точка: {1}\nОценка: {2}\nПроходной балл: {3}\nМаксимальный балл: {4}'.format(
                                            temp_names[int(i[0])], i[2], i[3], i[4], i[5])
                                        is_DB_update_needed = True
                                        updater.bot.send_message(chat_dict[user_auth], new_mark_message)
                                    temp_counter += 1
                                if is_DB_update_needed:
                                    cursor.execute(
                                        "UPDATE user_tables SET table_array = %(quarry_array)s WHERE tg_id = %(tg_id)s",
                                        {'quarry_array': quarry_array,
                                         'tg_id': str(user_auth)})
                                    conn.commit()
                            else:  # если триместр новый то удалим старую информацию и вставим новую
                                cursor.execute("DELETE FROM user_tables WHERE tg_id = %(tg_id)s",
                                               {'tg_id': str(user_auth)})
                                cursor.execute(
                                    "INSERT INTO user_tables(tg_id,table_array,table_names) VALUES (%(tg_id)s,%(table_array)s,%(table_names)s)",
                                    {'tg_id': str(user_auth), 'table_array': quarry_array,
                                     'table_names': names_array})
                                conn.commit()
        time.sleep(6)
