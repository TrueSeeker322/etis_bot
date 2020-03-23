import telebot
import time
from etis import *
import psycopg2
from contextlib import closing
import uuid
import hashlib

DATABASE_URL = os.environ['DATABASE_URL']
bot = telebot.TeleBot('997665653:AAGq43XKERQVcskXrxkMNBeLwkpZAoIDfKs')


def hash_pass(password):
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет! Нажмите /login для ввода логина и пароля')


@bot.message_handler(commands=['login'])
def start_message(message):
    login_dict[message.from_user.id] = 'Не введён'
    pass_dict[message.from_user.id] = 'Не введён'
    bot.send_message(message.chat.id, 'Введите логин:')
    login_flag_dict[message.from_user.id] = True


@bot.message_handler(commands=['user_data'])
def user_data_message(message):
    mes = bot.send_message(message.chat.id, (
            'Логин: ' + login_dict[message.from_user.id] + '\n Пароль: ' + pass_dict[message.from_user.id]))
    time.sleep(6)
    bot.delete_message(message.chat.id, mes.message_id)


@bot.message_handler(commands=['authorize'])
def auth(message):
    try:
        if login_dict[message.from_user.id] == 'Не введён' or pass_dict[message.from_user.id] == 'Не введён':
            bot.send_message(message.chat.id, 'Не ввёден логин или пароль. /login')
        else:
            auth_data = {'p_redirect'.encode('cp1251'): 'stu.timetable'.encode('cp1251'),
                         'p_username'.encode('cp1251'): login_dict[message.from_user.id].encode('cp1251'),
                         'p_password'.encode('cp1251'): pass_dict[message.from_user.id].encode('cp1251')}
            session_dict[message.from_user.id] = requests.Session()  # добавление подключения в словарь
            if authentication(auth_data, session_dict[message.from_user.id]):
                bot.send_message(message.chat.id, 'Вход успешен. Для запуска работы бота нажмите /bot_start: ')
                with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Обновление БД
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT * FROM tg_user_data WHERE tg_id = %(tg_id)s;",
                                       {'tg_id': str(message.from_user.id)})
                        if not cursor.fetchall():
                            cursor.execute(
                                "INSERT INTO tg_user_data(tg_id, etis_login, etis_pass) VALUES (%(tg_id)s,%(etis_login)s,%(etis_pass)s);",
                                {'tg_id': str(message.from_user.id), 'etis_login': login_dict[message.from_user.id],
                                 'etis_pass': pass_dict[message.from_user.id]})
                            cursor.execute('SELECT * FROM tg_user_data;')
                        else:
                            cursor.execute(
                                "UPDATE tg_user_data SET etis_login = %(etis_login)s, etis_pass = %(etis_pass)s WHERE tg_id= %(tg_id)s;",
                                {'tg_id': str(message.from_user.id), 'etis_login': login_dict[message.from_user.id],
                                 'etis_pass': pass_dict[message.from_user.id]})
                        conn.commit()
                auth_dict[message.from_user.id] = True
            else:
                del session_dict[message.from_user.id]
                bot.send_message(message.chat.id, 'Неверный логин или пароль. Пожалуйста, повторите ввод /login. Для '
                                                  'просмотра введённых данных нажмите /user_data')
                auth_dict[message.from_user.id] = False
    except:
        bot.send_message(message.chat.id, 'Не ввёден логин или пароль. /login')


@bot.message_handler(commands=['bot_start'])
def bot_start(message):
    try:
        if auth_dict[message.from_user.id]:
            quarry_array = '{'  # строка для вывода информации об оценках в бд
            names_array = '{'  # строка для вывода информации об предметах в бд
            table_array, table_names = info_scrapping(session_dict[message.from_user.id])
            print (table_array)
            print('__________________________')
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
            #print(quarry_array)
            #print(names_array)
            with closing(psycopg2.connect(DATABASE_URL, sslmode='require')) as conn:  # Обновление БД
                with conn.cursor() as cursor:
                    cursor.execute("SELECT table_array, table_names FROM user_tables WHERE tg_id = %(tg_id)s",
                                   {'tg_id': str(message.from_user.id)})
                    if not cursor.fetchone():  # если в бд еще нет такой записи
                        cursor.execute("DELETE FROM user_tables WHERE tg_id = %(tg_id)s",
                                       {'tg_id': str(message.from_user.id)})
                        cursor.execute(
                            "INSERT INTO user_tables(tg_id,table_array,table_names) VALUES (%(tg_id)s,%(table_array)s,%(table_names)s)",
                            {'tg_id': str(message.from_user.id), 'table_array': quarry_array,
                             'table_names': names_array})
                        conn.commit()
                    else:  # если в бд есть такая запись, то проверим на сходство данных
                        cursor.execute("SELECT table_array, table_names FROM user_tables WHERE tg_id = %(tg_id)s",
                                       {'tg_id': str(message.from_user.id)})
                        temp_counter = 0
                        fetch = cursor.fetchone()
                        temp_tables = fetch[0]
                        temp_names = fetch[1]
                        for i in table_names:
                            i = i.replace('"', '*')
                            if i != temp_names[temp_counter]:  # если собранная информация по предметам не совпадает с текущей
                                print(i)
                                break  # тут вставить сбор информации заново 
                            else:
                                print('clear')  # temp
                            temp_names += 1

                        # TODO
        else:
            bot.send_message(message.chat.id, 'Авторизация не пройдена. /authorize')
    except:
        bot.send_message(message.chat.id, 'Авторизация не пройдена. /authorize')


@bot.message_handler(content_types=['text'])
def text_message(message):
    if login_flag_dict[message.from_user.id]:
        login_dict[message.from_user.id] = message.text
        login_flag_dict[message.from_user.id] = False
        bot.send_message(message.chat.id, 'Введите пароль: ')
        password_flag_dict[message.from_user.id] = True
    elif password_flag_dict[message.from_user.id]:
        pass_dict[message.from_user.id] = message.text
        password_flag_dict[message.from_user.id] = False
        bot.send_message(message.chat.id, 'Для просмотра введённых данных нажмите /user_data')
        bot.send_message(message.chat.id, 'Для повторного ввода данных нажмите /login')
        bot.send_message(message.chat.id, 'Для авторизации нажмите /authorize')


auth_dict = {}
login_flag_dict = {}
password_flag_dict = {}
session_dict = {}  # словарь всех подключений
login_dict = {}  # словарь логинов
pass_dict = {}  # словарь паролей

bot.polling()
