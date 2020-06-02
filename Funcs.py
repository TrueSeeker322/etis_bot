import psycopg2
import time
import requests
import sys
import traceback
from cryptography.fernet import Fernet
from contextlib import closing
from Config import *
from Etis import *
from Colors import *
from setup import session_dict, auth_dict


def pass_encrypt(password):  # шифрование пароля
    f = Fernet(PASSKEY)
    encrypted = f.encrypt(password.encode())
    return encrypted


def pass_decrypt(encrypted):  # дешифрование пароля
    f = Fernet(PASSKEY)
    decrypted = f.decrypt(encrypted)
    return decrypted.decode('utf-8')


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
                        print(Colors.CYAN + 'Отправляю новую оценку' + Colors.DROP, user_auth_local)
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
            if fetch_local is not None:
                for trim_to_verify in fetch_local:
                    if int(trim) > int(trim_to_verify):
                        trim_to_delete = trim_to_verify
                    elif int(trim) < int(trim_to_verify):
                        trim_to_delete = trim
                    else:
                        trim_to_delete = None
                    if trim_to_delete is not None:
                        print(Colors.YELLOW + 'Удаляю записи от триместре ' + Colors.DROP, trim_to_delete)
                        cursor_local.execute(
                            "DELETE FROM user_tables WHERE tg_id = %(tg_id)s AND trim = %(trim)s",
                            {'tg_id': str(user_auth_local),
                             'trim': trim_to_delete})
                        conn_local.commit()


def restart_auth_dict():
    with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # При старте бота, добавляем в словарь аутентификации всех, кто включил бота
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


def main_loop(updater):
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
                        print(Colors.YELLOW + 'Данные пользователя ', user_auth, ' устарели')
                        updater.bot.send_message(int(user_auth),
                                                 'Данные для входа в ЕТИС устарели, пожалуйста, введите обновленные данные /login'
                                                 '\nЕсли Вы видите это сообщение, но логин и пароль не изменялись - сообщите об ошибке /report')
                        print('Выключаю бот ' + Colors.DROP, user_auth)
                        del auth_dict[user_auth]
                        with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Удаляем запись из БД
                            with conn.cursor() as cursor:
                                cursor.execute("UPDATE tg_user_data SET auth = false WHERE tg_id= %(tg_id)s;",
                                               {'tg_id': str(user_auth)})
                                conn.commit()
                        continue
                    else:
                        print(Colors.RED + 'Серверы ЕТИС недоступны' + Colors.DROP)
                        time.sleep(RECHECK_TIME)
                        continue
                print('проверяю пользователя ', user_auth)
                info_processing(user_auth, updater.bot)
                time.sleep(3)
            except Exception as ex:
                for frame in traceback.extract_tb(sys.exc_info()[2]):
                    fname, lineno, fn, text = frame
                    print(Colors.RED + '-------------------------ОШБИКА ' + str(user_auth) + '-------------------------')
                    print(ex)
                    print("Ошибка в  %s в строке %d" % (fname, lineno))
                    print(text)
                    print(sys.exc_info()[0])
                    print(Colors.RED + '-------------------------КОНЕЦ ОШИБКИ-------------------------')
                continue
        ss = requests.Session()
        ss.get(APP_NAME)
        end_time = time.time()
        if end_time - start_time < RECHECK_TIME:
            print('___________Жду ', RECHECK_TIME - end_time + start_time, '___________')
            time.sleep(RECHECK_TIME - end_time + start_time)
