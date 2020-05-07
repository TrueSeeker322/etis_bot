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
SESSION_TIMEOUT = int(os.environ['SESSION_TIMEOUT'])


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
    time.sleep(5)
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
            info_processing(update.message.from_user.id, bot)
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


def info_processing(user_auth_local, bot_local):
    table_array = info_scrapping(session_dict.get(user_auth_local))
    trim = ''
    for i in table_array:
        subject = i[0]
        control_point = i[1]
        current_mark = i[2]
        passing_mark = i[3]
        max_mark = i[4]
        date = i[5]
        trim = i[6]
        with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn_local:  # Обновление БД
            with conn_local.cursor() as cursor_local:
                cursor_local.execute(
                    "SELECT current_mark, date FROM user_tables WHERE tg_id = %(tg_id)s AND subject = %(subject)s AND control_point = %(control_point)s",
                    {'tg_id': str(user_auth_local),
                     'subject': subject,
                     'control_point': control_point})
                fetch_local = cursor_local.fetchone()
                if fetch_local is None:  # если в бд еще нет такой записи
                    cursor_local.execute(
                        "INSERT INTO user_tables(tg_id, subject, control_point, current_mark, passing_mark, max_mark, date, trim) VALUES (%(tg_id)s,%(subject)s,%(control_point)s,%(current_mark)s,%(passing_mark)s,%(max_mark)s, %(date)s, %(trim)s)",
                        {'tg_id': str(user_auth_local),
                         'subject': subject,
                         'control_point': control_point,
                         'current_mark': current_mark,
                         'passing_mark': passing_mark,
                         'max_mark': max_mark,
                         'date': date,
                         'trim': trim})
                    conn_local.commit()
                else:  # если в бд есть такая запись, то проверим на сходство данных
                    current_mark_to_verify = fetch_local[0]
                    date_to_verify = fetch_local[1]
                    if (current_mark != current_mark_to_verify) or (date != str(date_to_verify)):
                        print('Отправляю новую оценку', user_auth_local)
                        new_mark_message = 'У вас новая оценка!\nПредмет: {0}\nКонтрольная точка: {1}\nОценка: {2}\nПроходной балл: {3}\nМаксимальный балл: {4}'.format(
                            subject, control_point, current_mark, passing_mark, max_mark)
                        bot_local.send_message(int(user_auth_local), new_mark_message)
                        cursor_local.execute(
                            "UPDATE user_tables SET current_mark = %(current_mark)s, date = %(date)s WHERE tg_id = %(tg_id)s AND subject = %(subject)s AND control_point = %(control_point)s",
                            {'tg_id': str(user_auth_local),
                             'subject': subject,
                             'control_point': control_point,
                             'current_mark': current_mark,
                             'date': date})
                        conn_local.commit()
    with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn_local:  # удаляем записи о старых триместрах
        with conn_local.cursor() as cursor_local:
            cursor_local.execute(
                "SELECT DISTINCT trim FROM user_tables WHERE tg_id = %(tg_id)s",
                {'tg_id': str(user_auth_local)})
            fetch_local = cursor_local.fetchone()
            if fetch_local[0] is not None:
                for trim_to_verify in fetch_local:
                    if int(trim) > int(trim_to_verify):
                        trim_to_delete = trim_to_verify
                    elif int(trim) < int(trim_to_verify):
                        trim_to_delete = trim
                    else:
                        trim_to_delete = None
                    if trim_to_delete is not None:
                        print('удаляю ', trim_to_delete)
                        cursor_local.execute(
                            "DELETE FROM user_tables WHERE tg_id = %(tg_id)s AND trim = %(trim)s",
                            {'tg_id': str(user_auth_local),
                             'trim': trim_to_delete})
                        conn_local.commit()


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
                if auth_dict.get(user_auth):  # если у него включен бот
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
                    info_processing(user_auth, updater.bot)
        except RuntimeError:
            print('RuntimeError')
        print('Жду')
        print('____________________________________________________')
        ss = requests.Session()
        ss.get(APP_NAME)
        time.sleep(RECHECK_TIME)
