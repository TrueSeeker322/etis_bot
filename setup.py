import os
import time
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from etis import *
import psycopg2
from contextlib import closing
from cryptography.fernet import Fernet
import requests

DATABASE_URL = os.environ['DATABASE_URL']
TOKEN = os.environ['BOT_TOKEN']
PASSKEY = os.environ["PASS_KEY"].encode()
APP_NAME = os.environ['APP_NAME']
RECHECK_TIME = int(os.environ['RECHECK_TIME'])
SESSION_TIMEOUT = int(os.environ['SESSION_TIMEOUT'])  # время сброса сессии


def pass_encrypt(password):  # шифрование пароля
    f = Fernet(PASSKEY)
    encrypted = f.encrypt(password.encode())
    return encrypted


def pass_decrypt(encrypted):  # дешифрование пароля
    f = Fernet(PASSKEY)
    decrypted = f.decrypt(encrypted)
    return decrypted.decode('utf-8')


def run(updater_local):
    PORT = int(os.environ.get("PORT", "8443"))
    updater_local.start_webhook(listen="0.0.0.0",
                                port=PORT,
                                url_path=TOKEN)
    updater_local.bot.set_webhook(APP_NAME + TOKEN)


def start_handler(bot, update):
    custom_keyboard = [['/login', '/help']]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard=custom_keyboard, resize_keyboard=True)
    bot.send_message(chat_id=update.message.from_user.id,
                     text='Привет! Этот бот поможет тебе не пропустить новые оценки в ЕТИСе!\nНажмите /login для ввода логина и пароля\nНажми /help для вывода справки',
                     reply_markup=reply_markup)


def login_handler(bot, update):
    login_dict[update.message.from_user.id] = 'Не введён'
    pass_dict[update.message.from_user.id] = 'Не введён'
    update.message.reply_text('Введите логин:')
    login_flag_dict[update.message.from_user.id] = True


def user_data_handler(bot, update):
    mes = update.message.reply_text(
        'Сообщение удалится через 5 секунд\nЛогин: ' + login_dict.get(
            update.message.from_user.id) + '\nПароль: ' + pass_decrypt(pass_dict.get(update.message.from_user.id)))
    time.sleep(6)
    bot.delete_message(chat_id=update.message.chat.id, message_id=mes.message_id)


def stop_handler(bot, update):
    auth_dict[update.message.from_user.id] = False
    with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn_local:  # Проверям время последней сессии
        with conn_local.cursor() as cursor_local:
            cursor_local.execute("UPDATE tg_user_data SET auth = %(auth)s WHERE tg_id= %(tg_id)s;",
                                 {'tg_id': str(update.message.from_user.id),
                                  'auth': 'False'})
            conn_local.commit()
    update.message.reply_text('Вы успешно отписались от уведомлений\nЧтобы включить бота заново, введите /login')


def help_handler(bot, update):
    update.message.reply_text('Бот призван помочь студентам вовремя узнавать об оценках в их личном кабинете. '
                              'Чтобы бот начал работу, введите /login. После этого введи логин от личного кабинета.'
                              'Затем введи свой пароль. Не переживай, пароли хранятся в зашифрованном виде.'
                              'Если всё в порядке и данные введены верно, то бот оповестит тебя о начале работы.'
                              'Чтобы перестать получать уведомления введи /stop')


def auth_handler(bot, update):
    if login_dict.get(update.message.from_user.id) == 'Не введён' or \
            login_dict.get(update.message.from_user.id) is None or \
            pass_dict.get(update.message.from_user.id) == 'Не введён' or \
            pass_dict.get(update.message.from_user.id) is None:
        bot.send_message(update.message.chat.id, 'Не ввёден логин или пароль. /login')
    else:
        auth_data_local = {'p_redirect'.encode('cp1251'): 'stu.timetable'.encode('cp1251'),
                           'p_username'.encode('cp1251'): login_dict[update.message.from_user.id].encode('cp1251'),
                           'p_password'.encode('cp1251'): pass_decrypt(pass_dict[update.message.from_user.id]).encode(
                               'cp1251')}
        session_dict[update.message.from_user.id] = requests.Session()  # добавление подключения в словарь
        auth_result_local = authentication(auth_data_local, session_dict[update.message.from_user.id])
        if auth_result_local == 1:
            print('успешная авторизация ', update.message.from_user.id)
            with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn_local:  # Обновление БД
                with conn_local.cursor() as cursor_local:
                    cursor_local.execute("SELECT * FROM tg_user_data WHERE tg_id = %(tg_id)s;",
                                         {'tg_id': str(update.message.from_user.id)})
                    if not cursor_local.fetchall():
                        cursor_local.execute(
                            "INSERT INTO tg_user_data(tg_id, etis_login, etis_pass, auth, session_time) VALUES (%(tg_id)s,%(etis_login)s,%(etis_pass)s,%(auth)s, %(session_time)s);",
                            {'tg_id': str(update.message.from_user.id),
                             'etis_login': login_dict[update.message.from_user.id],
                             'etis_pass': pass_dict[update.message.from_user.id].decode('utf-8'),
                             'auth': 'True',
                             'session_time': str(time.time())})
                        cursor_local.execute('SELECT * FROM tg_user_data;')
                    else:
                        cursor_local.execute(
                            "UPDATE tg_user_data SET etis_login = %(etis_login)s, etis_pass = %(etis_pass)s, auth = %(auth)s, session_time = %(session_time)s WHERE tg_id= %(tg_id)s;",
                            {'tg_id': str(update.message.from_user.id),
                             'etis_login': login_dict[update.message.from_user.id],
                             'etis_pass': pass_dict[update.message.from_user.id].decode('utf-8'),
                             'auth': 'True',
                             'session_time': str(time.time())})
                    conn_local.commit()
            update.message.reply_text('Вход успешен.\nБот начал свою работу. Для отключения бота введите /stop')
            auth_dict[update.message.from_user.id] = True
        elif auth_result_local == 0:
            print('провальная авторизация', update.message.from_user.id)
            del session_dict[update.message.from_user.id]
            update.message.reply_text('Неверный логин или пароль. Пожалуйста, повторите ввод /login. Для '
                                      'просмотра введённых данных нажмите /user_data')
            auth_dict[update.message.from_user.id] = False
        else:
            update.message.reply_text('Серверы ЕТИС в данный момент недоступны, попробуйте позже')


def text_handler(bot, update):
    if login_flag_dict.get(update.message.from_user.id):
        login_dict[update.message.from_user.id] = update.message.text
        login_flag_dict[update.message.from_user.id] = False
        bot.send_message(update.message.chat.id, 'Введите пароль: ')
        password_flag_dict[update.message.from_user.id] = True
    elif password_flag_dict.get(update.message.from_user.id):
        pass_dict[update.message.from_user.id] = pass_encrypt(update.message.text)
        password_flag_dict[update.message.from_user.id] = False
        update.message.reply_text('Для просмотра введённых данных нажмите /user_data')
        update.message.reply_text('Для повторного ввода данных нажмите /login')
        update.message.reply_text('Для авторизации нажмите /authorize')


auth_dict = {}  # словарь с подключениями для пользователей
session_time_dict = {}  # словаь времени начала сессии
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
    updater.dispatcher.add_handler(CommandHandler("stop", stop_handler))
    updater.dispatcher.add_handler(CommandHandler("help", help_handler))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), text_handler))

    run(updater)

    with closing(psycopg2.connect(DATABASE_URL,
                                  sslmode='require')) as conn:  # При старте бота, добавляем в словарь аутентификации всех, кто включил бота
        with conn.cursor() as cursor:
            cursor.execute("SELECT tg_id, auth FROM tg_user_data")
            for line in cursor:
                if line[1]:
                    auth_dict[int(line[0])] = True
                    with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn2:
                        with conn2.cursor() as cursor2:
                            cursor2.execute(
                                "UPDATE tg_user_data SET session_time = %(session_time)s WHERE tg_id= %(tg_id)s;",
                                {'session_time': str(0),
                                 'tg_id': str(line[0])})
                            conn2.commit()

    while True:
        try:
            for user_auth in auth_dict:  # пробегаем всех пользователей
                if auth_dict.get(user_auth):  # если у  него включен бот
                    with closing(psycopg2.connect(DATABASE_URL,
                                                  sslmode='require')) as conn:  # Проверям время последней сессии
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT session_time FROM tg_user_data WHERE tg_id = %(tg_id)s",
                                           {'tg_id': str(user_auth)})
                            fetch = cursor.fetchone()
                    if time.time() - fetch[0] > SESSION_TIMEOUT:  # если последняя сессия была более 40 минут назад
                        print('Обновляю сессию', user_auth)
                        with closing(
                                psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # то аутентификация заново
                            with conn.cursor() as cursor:
                                cursor.execute("SELECT etis_login, etis_pass FROM tg_user_data WHERE tg_id = %(tg_id)s",
                                               {'tg_id': str(user_auth)})
                                fetch = cursor.fetchone()
                                auth_data = {'p_redirect'.encode('cp1251'): 'stu.timetable'.encode('cp1251'),
                                             'p_username'.encode('cp1251'): fetch[0].encode('cp1251'),
                                             'p_password'.encode('cp1251'): pass_decrypt(fetch[1].encode()).encode(
                                                 'cp1251')}
                                session_dict[user_auth] = requests.Session()  # добавление подключения в словарь
                        auth_result = authentication(auth_data, session_dict[user_auth])
                        if auth_result == 1:
                            with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Обновление БД
                                with conn.cursor() as cursor:
                                    cursor.execute(
                                        "UPDATE tg_user_data SET session_time = %(session_time)s WHERE tg_id= %(tg_id)s;",
                                        {'session_time': str(time.time()),
                                         'tg_id': str(user_auth)})
                                    conn.commit()
                        elif auth_result == 0:
                            print('Данные пользователя ', user_auth, ' устарели')
                            updater.bot.send_message(int(user_auth), 'Данные для входа в ЕТИС устарели, пожалуйста, введите обновленные данные /login')
                            with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Выключаем бота для этого пользователя
                                with conn.cursor() as cursor:
                                    cursor.execute(
                                        "UPDATE tg_user_data SET auth = %(auth)s WHERE tg_id= %(tg_id)s;",
                                        {'tg_id': str(user_auth),
                                         'auth': 'False'})
                                    conn.commit()
                            continue
                        else:
                            print('Сервера ЕТИС недоступны')
                            time.sleep(RECHECK_TIME)
                    print('проверяю юзера ', user_auth)
                    quarry_array = '{'  # строка для вывода информации об оценках в бд РАБОТАЕТ НЕ ТРОГАЙ
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
                                cursor.execute(
                                    "SELECT table_array, table_names FROM user_tables WHERE tg_id = %(tg_id)s",
                                    {'tg_id': str(user_auth)})
                                temp_counter = 0
                                fetch = cursor.fetchone()
                                temp_tables = fetch[0]
                                temp_names = fetch[1]
                                is_new_trimester = False
                                for i in table_names:  # если собранная информация по предметам не совпадает с текущей
                                    if i != temp_names[temp_counter]:
                                        is_new_trimester = True  # флаг нового триместра, если True значит только обновляем инфу о новых предметах и не проверяем на совпадение
                                    temp_counter += 1
                                if not is_new_trimester:  # если триместр не новый то проверка на совпадение
                                    temp_counter = 0
                                    is_DB_update_needed = False  # нужно ли обновить БД с новыми оценками
                                    for i in table_array:  # проверям сохраненную информацию и ту, которую спарсили только что, на совпадение
                                        if i[3] != temp_tables[temp_counter][3]:
                                            print('Отправляю новую оценку', user_auth)
                                            new_mark_message = 'У вас новая оценка!\nПредмет: {0}\nКонтрольная точка: {1}\nОценка: {2}\nПроходной балл: {3}\nМаксимальный балл: {4}'.format(
                                                temp_names[int(i[0])], i[2], i[3], i[4], i[5])
                                            is_DB_update_needed = True
                                            updater.bot.send_message(int(user_auth), new_mark_message)
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
        except RuntimeError:
            print('RuntimeError')
        print('Жду')
        print('____________________________________________________')
        ss = requests.Session()
        ss.get(APP_NAME)
        time.sleep(RECHECK_TIME)
