import telegram
from Funcs import *
from datetime import datetime
from setup import login_dict, pass_dict, report_flag_dict, login_flag_dict, auth_dict, password_flag_dict, mail, session_dict, mail_all


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
    print(Colors.YELLOW + 'Выключаю бот ' + Colors.DROP, update.message.from_user.id)
    with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn1:  # Удаляем запись из БД
        with conn1.cursor() as cursor1:
            cursor1.execute("SELECT tg_id FROM  tg_user_data WHERE tg_id= %(tg_id)s;",
                            {'tg_id': str(update.message.from_user.id)})
            fetch1 = cursor1.fetchone()
            if fetch1 is not None:
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
            print(Colors.GREEN + 'успешная авторизация ' + Colors.DROP, update.message.from_user.id, login_dict.get(update.message.from_user.id))
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
            print(Colors.MAGENTA + 'провальная авторизация' + Colors.DROP, update.message.from_user.id)
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
        print(Colors.BLUE + 'Отправляю репорт' + Colors.DROP)
        with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn_local:  # Обновление БД
            with conn_local.cursor() as cursor_local:
                cursor_local.execute(
                    "INSERT INTO reports(tg_id, report, date) VALUES (%(tg_id)s, %(rep)s, %(date)s);",
                    {'tg_id': str(update.message.from_user.id),
                     'rep': rep,
                     'date': date})
                conn_local.commit()
        update.message.reply_text('Ваш отчет об ошибке успешно отправлен ')
    elif mail.get(update.message.from_user.id):
        mail[update.message.from_user.id] = False
        msg = update.message.text.rsplit('_')
        tg_id = msg[0]
        message = msg[1]
        bot.send_message(chat_id=tg_id,
                         text=message)
    elif mail_all.get(update.message.from_user.id):
        mail_all[update.message.from_user.id] = False
        message = update.message.text
        with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn_local:  # Обновление БД
            with conn_local.cursor() as cursor_local:
                cursor_local.execute("SELECT tg_id FROM tg_user_data;")
                for i in cursor_local:
                    try:
                        bot.send_message(chat_id=i[0],
                                         text=message)
                        print(Colors.BLUE + 'Отправляю рассылку ', i[0])
                        time.sleep(1)
                    except:
                        pass


def report_handler(bot, update):
    password_flag_dict[update.message.from_user.id] = False
    login_flag_dict[update.message.from_user.id] = False
    report_flag_dict[update.message.from_user.id] = True
    update.message.reply_text(
        'Чтобы отправить сообщение о проблеме (или отзыв), подробно опишите ошибку в своем следующем сообщении. Для отмены нажмите /cancel_report')


def cancel_report_handler(bot, update):
    report_flag_dict[update.message.from_user.id] = False
    update.message.reply_text('Отправка успешно отменена')


def mail_handler(bot, update):
    if str(update.message.from_user.id) == ADMIN_ID:
        mail[update.message.from_user.id] = True


def mail_all_handler(bot, update):
    if str(update.message.from_user.id) == ADMIN_ID:
        mail_all[update.message.from_user.id] = True