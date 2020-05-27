import time
import telegram
import psycopg2
import sys
import traceback
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from etis import *
from contextlib import closing
from cryptography.fernet import Fernet
from datetime import datetime

DATABASE_URL = os.environ['DATABASE_URL']
TOKEN = os.environ['BOT_TOKEN']
PASSKEY = os.environ["PASS_KEY"].encode()
APP_NAME = os.environ['APP_NAME']
RECHECK_TIME = int(os.environ['RECHECK_TIME'])
SESSION_TIMEOUT = int(os.environ['SESSION_TIMEOUT'])
ADMIN_ID = os.environ['ADMIN_ID']


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
                     text='Привет! Этот бот поможет Вам не пропустить новые оценки в ЕТИСе!\nНажмите /login чтобы начать\nИли /help для просмотра информации',
                     reply_markup=reply_markup)


def login_handler(bot, update):
    login_dict[update.message.from_user.id] = 'Не введён'
    pass_dict[update.message.from_user.id] = 'Не введён'
    report_flag_dict[update.message.from_user.id] = False
    update.message.reply_text('Введите логин:')
    login_flag_dict[update.message.from_user.id] = True


def user_data_handler(bot, update):
    if login_dict.get(update.message.from_user.id) is None:
        login_dict[update.message.from_user.id] = 'Не введён'
    if pass_dict.get(update.message.from_user.id) is None:
        pass_dict[update.message.from_user.id] = 'Не введён'
    passw = pass_dict.get(update.message.from_user.id)
    if passw != 'Не введён':
        passw = pass_decrypt(pass_dict.get(update.message.from_user.id))
    mes = update.message.reply_text(
        'Сообщение удалится через 5 секунд\nЛогин: ' + login_dict.get(
            update.message.from_user.id) + '\nПароль: ' + passw)
    time.sleep(5)
    bot.delete_message(chat_id=update.message.chat.id, message_id=mes.message_id)


def stop_handler(bot, update):
    print('Выключаю бот ', update.message.from_user.id)
    with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Удаляем запись из БД
        with conn.cursor() as cursor:
            cursor.execute("SELECT tg_id FROM  tg_user_data WHERE tg_id= %(tg_id)s;",
                           {'tg_id': str(update.message.from_user.id)})
            fetch = cursor.fetchone()
            if fetch is not None:
                del auth_dict[update.message.from_user.id]
                with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn_local:  # Удаляем запись из БД
                    with conn_local.cursor() as cursor_local:
                        cursor_local.execute("DELETE FROM  tg_user_data WHERE tg_id= %(tg_id)s;",
                                             {'tg_id': str(update.message.from_user.id)})
                        conn_local.commit()
    custom_keyboard = [['/login', '/help']]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard=custom_keyboard, resize_keyboard=True)
    bot.send_message(chat_id=update.message.from_user.id,
                     text='Вы успешно отписались от уведомлений\nЧтобы включить бота заново, введите /login',
                     reply_markup=reply_markup)


def help_handler(bot, update):
    update.message.reply_text('Бот призван помочь студентам вовремя узнавать об оценках в их личном кабинете. '
                              'Чтобы бот начал работу, нажмите /login. После этого введите логин от личного кабинета.'
                              'Затем введите свой пароль.'
                              'Если всё в порядке, и данные введены верно, то бот оповестит Вас о начале работы.'
                              'Чтобы перестать получать уведомления и удалить всю информацию о себе из бота, введите /stop.\n\n'
                              'Внимание! Бот не несет ответственность за сохранность вводимых данных. '
                              'Пользователь добровольно передаёт логин и пароль от личного кабинета ЕТИС для использования внутри бота. '
                              'Пароли хранятся в зашифрованном виде и не передаются третьим лицам.\n\n'
                              'Если Вы обнаружили ошибку, нажмите /report')


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
            print('успешная авторизация ', update.message.from_user.id, login_dict.get(update.message.from_user.id))
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
                        # cursor_local.execute('SELECT * FROM tg_user_data;')
                    else:
                        cursor_local.execute(
                            "UPDATE tg_user_data SET etis_login = %(etis_login)s, etis_pass = %(etis_pass)s, auth = %(auth)s, session_time = %(session_time)s WHERE tg_id= %(tg_id)s;",
                            {'tg_id': str(update.message.from_user.id),
                             'etis_login': login_dict[update.message.from_user.id],
                             'etis_pass': pass_dict[update.message.from_user.id].decode('utf-8'),
                             'auth': 'True',
                             'session_time': str(time.time())})
                    conn_local.commit()
            custom_keyboard = [['/stop', '/help']]
            reply_markup = telegram.ReplyKeyboardMarkup(keyboard=custom_keyboard, resize_keyboard=True)
            bot.send_message(chat_id=update.message.from_user.id,
                             text='Вход успешен.\nБот пришлёт уведомление, когда у Вас появится новая оценка. Для отключения бота нажмите /stop',
                             reply_markup=reply_markup)
            auth_dict[update.message.from_user.id] = True
            info_processing(update.message.from_user.id, bot)
        elif auth_result_local == 0:
            print('провальная авторизация', update.message.from_user.id)
            del session_dict[update.message.from_user.id]
            custom_keyboard = [['/login', '/help']]
            reply_markup = telegram.ReplyKeyboardMarkup(keyboard=custom_keyboard, resize_keyboard=True)
            bot.send_message(chat_id=update.message.from_user.id,
                             text='Неверный логин или пароль. Пожалуйста, повторите ввод /login. Для просмотра введённых данных нажмите /user_data',
                             reply_markup=reply_markup)
        else:
            custom_keyboard = [['/login', '/help']]
            reply_markup = telegram.ReplyKeyboardMarkup(keyboard=custom_keyboard, resize_keyboard=True)
            bot.send_message(chat_id=update.message.from_user.id,
                             text='Серверы ЕТИС в данный момент недоступны, повторите попытку позже',
                             reply_markup=reply_markup)


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
        update.message.reply_text('Для старта бота нажмите /authorize')
    elif report_flag_dict.get(update.message.from_user.id):
        rep = update.message.text
        dt = datetime.now().timetuple()
        date = str(dt[0]) + '-' + str(dt[1]) + '-' + str(dt[2]) + ' ' + str(dt[3]) + ':' + str(dt[4]) + ':' + str(dt[5])
        print('Отправляю репорт')
        with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn_local:  # Обновление БД
            with conn_local.cursor() as cursor_local:
                cursor_local.execute(
                    "INSERT INTO reports(tg_id, report, date) VALUES (%(tg_id)s, %(rep)s, %(date)s);",
                    {'tg_id': str(update.message.from_user.id),
                     'rep': rep,
                     'date': date})
                conn_local.commit()
        update.message.reply_text('Ваша отчет об ошибке успешно отправлен ')
    elif mail.get(update.message.from_user.id):
        mail[update.message.from_user.id] = False
        msg = update.message.text.rsplit('_')
        tg_id = msg[0]
        message = msg[1]
        bot.send_message(chat_id=tg_id,
                         text=message)


def report_handler(bot, update):
    password_flag_dict[update.message.from_user.id] = False
    login_flag_dict[update.message.from_user.id] = False
    report_flag_dict[update.message.from_user.id] = True
    update.message.reply_text(
        'Чтобы отправить сообщение о проблеме, подробно опишите ошибку в своем следующем сообщении. Для отмены нажмите /cancel_report')


def cancel_report_handler(bot, update):
    report_flag_dict[update.message.from_user.id] = False
    update.message.reply_text('Отправка успешно отменена')


def mail_handler(bot, update):
    if str(update.message.from_user.id) == ADMIN_ID:
        mail[update.message.from_user.id] = True


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
                        new_mark_message = 'У Вас новая оценка!\n\nПредмет: {0}\n\nКонтрольная точка: {1}\n\nОценка: {2}\n\nПроходной балл: {3}\n\nМаксимальный балл: {4}'.format(
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
                        print('Удаляю записи от триместре ', trim_to_delete)
                        cursor_local.execute(
                            "DELETE FROM user_tables WHERE tg_id = %(tg_id)s AND trim = %(trim)s",
                            {'tg_id': str(user_auth_local),
                             'trim': trim_to_delete})
                        conn_local.commit()


auth_dict = {}  # словарь с подключениями для пользователей
session_time_dict = {}  # словаь времени начала сессии
login_flag_dict = {}
password_flag_dict = {}
report_flag_dict = {}
session_dict = {}  # словарь всех подключений
login_dict = {}  # словарь логинов
pass_dict = {}  # словарь паролей
mail = {}

if __name__ == '__main__':
    updater = Updater(TOKEN)

    updater.dispatcher.add_handler(CommandHandler("start", start_handler))
    updater.dispatcher.add_handler(CommandHandler("login", login_handler))
    updater.dispatcher.add_handler(CommandHandler("user_data", user_data_handler))
    updater.dispatcher.add_handler(CommandHandler("authorize", auth_handler))
    updater.dispatcher.add_handler(CommandHandler("stop", stop_handler))
    updater.dispatcher.add_handler(CommandHandler("help", help_handler))
    updater.dispatcher.add_handler(CommandHandler("report", report_handler))
    updater.dispatcher.add_handler(CommandHandler("cancel_report", cancel_report_handler))
    updater.dispatcher.add_handler(CommandHandler("mail", mail_handler))

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
        start_time = time.time()
        auth_dict_stable = auth_dict.copy()
        for user_auth in auth_dict_stable:  # пробегаем всех пользователей
            try:
                with closing(
                        psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Проверям время последней сессии
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT session_time FROM tg_user_data WHERE tg_id = %(tg_id)s",
                                       {'tg_id': str(user_auth)})
                        fetch = cursor.fetchone()
                if time.time() - fetch[0] > SESSION_TIMEOUT:  # если последняя сессия была более 12 часов назад
                    print('Обновляю сессию', user_auth)
                    with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # то аутентификация заново
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
                        updater.bot.send_message(int(user_auth),
                                                 'Данные для входа в ЕТИС устарели, пожалуйста, введите обновленные данные /login'
                                                 '\nЕсли Вы видите это сообщение, но логин и пароль не изменялись - сообщите об ошибке /report')
                        print('Выключаю бот ', user_auth)
                        del auth_dict[user_auth]
                        with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Удаляем запись из БД
                            with conn.cursor() as cursor:
                                cursor.execute("DELETE FROM  tg_user_data WHERE tg_id= %(tg_id)s;",
                                               {'tg_id': str(user_auth)})
                                conn.commit()
                        continue
                    else:
                        print('Серверы ЕТИС недоступны')
                        time.sleep(RECHECK_TIME)
                        continue
                print('проверяю юзера ', user_auth)
                info_processing(user_auth, updater.bot)
                time.sleep(5)
            except:
                for frame in traceback.extract_tb(sys.exc_info()[2]):
                    fname, lineno, fn, text = frame
                    print('-------------------------ОШБИКА ' + str(user_auth) + '-------------------------')
                    print("Ошибка в  %s в строке %d" % (fname, lineno))
                    print(text)
                    print('-------------------------КОНЕЦ ОШИБКИ-------------------------')
                continue
        ss = requests.Session()
        ss.get(APP_NAME)
        end_time = time.time()
        if end_time - start_time < RECHECK_TIME:
            print('___________Жду ', RECHECK_TIME - end_time + start_time, '___________')
            time.sleep(RECHECK_TIME - end_time + start_time)
