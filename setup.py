import telebot
import time
from etis import *
import psycopg2

DATABASE_URL = os.environ['postgres://rsyvvpoplwgisz:bd99ff7d23a9be1a646d97443ee7ce8c519737252864fa5e8f6d085475926fd3@ec2-46-137-177-160.eu-west-1.compute.amazonaws.com:5432/dm0kbu27emvc']

conn = psycopg2.connect(DATABASE_URL, sslmode='require')

bot = telebot.TeleBot('997665653:AAGq43XKERQVcskXrxkMNBeLwkpZAoIDfKs')


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет! Нажмите /login для ввода логина и пароля')


@bot.message_handler(commands=['login'])
def start_message(message):
    global login_flag
    bot.send_message(message.chat.id, 'Введите логин:')
    login_flag = True


@bot.message_handler(commands=['user_data'])
def user_data_message(message):
    global password_var, login_var
    mes = bot.send_message(message.chat.id, ('Логин: ' + login_var + '\n Пароль: ' + password_var))
    time.sleep(6)
    bot.delete_message(message.chat.id, mes.message_id)


@bot.message_handler(commands=['authorize'])
def auth(message):
    auth_data = {'p_redirect'.encode('cp1251'): 'stu.timetable'.encode('cp1251'),
                 'p_username'.encode('cp1251'): login_var.encode('cp1251'),
                 'p_password'.encode('cp1251'): password_var.encode('cp1251')}
    s = requests.Session()
    if authentication(auth_data, s):
        bot.send_message(message.chat.id, 'Вход успешен. Для запуска работы бота нажмите /bot_start: ')
        session_dict.update({message.from_user.id: s})
        user_tables_dict.update(
            {info_scrapping(session_dict[message.from_user.id])})  # добавление таблицы данных в словарь
    else:
        bot.send_message(message.chat.id, 'Неверный логин или пароль. Пожалуйста, повторите ввод /login. Для '
                                          'просмотра введённых данных нажмите /user_data')


@bot.message_handler(commands=['bot_start'])
def bot_start(message):
    a = message  # убрать


@bot.message_handler(content_types=['text'])
def text_message(message):
    global login_flag, password_flag, login_var, password_var
    if login_flag:
        login_var = message.text
        login_flag = False
        bot.send_message(message.chat.id, 'Введите пароль: ')
        password_flag = True
    elif password_flag:
        password_var = message.text
        password_flag = False
        bot.send_message(message.chat.id, 'Для просмотра введённых данных нажмите /user_data')
        bot.send_message(message.chat.id, 'Для повторного ввода данных нажмите /login')
        bot.send_message(message.chat.id, 'Для авторизации нажмите /authorize')


login_var = 'Не введён'
password_var = 'Не введён'
login_flag = False
password_flag = False

session_dict = {}  # словарь всех подключений
user_tables_dict = {}  # словарь всех таблиц данных

bot.polling()
