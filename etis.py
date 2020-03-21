
import requests
import os
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

url = 'https://student.psu.ru/pls/stu_cus_et/stu.signs?p_mode=current'
url_login = 'https://student.psu.ru/pls/stu_cus_et/stu.login'
saved_data_file = 'Z:\True Seeker\Рабочий стол\\and\\saved_data.txt'

headers = {
    'User-Agent': UserAgent().chrome
}

auth = {'p_redirect'.encode('cp1251'): 'stu.timetable'.encode('cp1251'),
        'p_username'.encode('cp1251'): 'Мурзин'.encode('cp1251'),
        'p_password'.encode('cp1251'): '568219'.encode('cp1251')}
'''auth = {'p_redirect': 'stu.timetable',
        'p_username': 'Мурзин',
        'p_password': '568219'}'''
r = ''
soup = ''
s = ''
response = ''
table_names = ''
tables = ''
table_array = []  # массив веб данных
file_array = []  # массив оффлайн данных
count_tables = 0  # id таблицы
count_rows = 0  # сквозной id строки


def authentication(auth,sess):  # функция аутентификации
    global s, response, r
    response = sess.post(url_login, data=auth, headers=headers)  # Пост запрос на авторизацию
    r = sess.get(url, headers=headers)  # получение страницы
    soup = BeautifulSoup(r.content, 'html.parser')
    #print(soup.text)
    if soup.text.find('2396870'.encode('cp1251'), 0, len(soup)) == -1:
        print('успешная авторизхация')
        print (soup.text.find('2396870'.encode('cp1251'), 0, len(soup)))
        return True
    else:
        print('провальная авторизхация')
        print (soup.text.find('2396870'.encode('cp1251'), 0, len(soup)))
        return False


def info_scrapping(sess):  # сборка информации на странице
    global soup, table_names, tables, table_array, file_array, count_rows, count_tables
    r = sess.get(url, headers=headers)  # получение страницы
    soup = BeautifulSoup(r.content, 'html.parser')  # парсинг страницы
    table_names = soup.findAll('h3')  # выделение имен всех таблиц
    table_names = [head.get_text() for head in table_names]  # выделение имен всех таблиц
    tables = soup.findAll('table', attrs={'class': 'common'})  # выделение всех таблиц
    for i in tables:  # формирование массива со строками таблицы оценок
        rows_max = (len(i) - 3) // 2
        row_id = 4
        for j in range(rows_max - 1):
            table_array.append([])
            table_array[count_rows].append(str(count_tables))  # id таблицы
            table_array[count_rows].append(str(count_rows))  # id строки таблицы
            table_array[count_rows].append(i.contents[row_id].contents[1].text)  # название работы
            table_array[count_rows].append(i.contents[row_id].contents[7].text)  # текущий балл
            if type(i.contents[row_id].contents[9].text) is not type(1):
                table_array[count_rows].append('0')
            else:
                table_array[count_rows].append(i.contents[row_id].contents[9].text)  # проходной балл
            table_array[count_rows].append(i.contents[row_id].contents[13].text)  # максимальный балл
            count_rows += 1
            row_id += 2
        count_tables += 1
    print(table_array)
    print(type(table_array))
    return table_array


def new_info_processing():
    global table_array
    f = open(saved_data_file, 'w')
    for i in table_array:
        for j in i:
            f.write(str(j) + '|')
        f.write('\n')
    f.close()


def file_processing():
    global file_array
    is_first_log = False  # маркер первого захода
    try:
        f = open(saved_data_file, 'r')
    except FileNotFoundError:
        is_first_log = True
    if is_first_log:  # еслии первый логин
        new_info_processing()
    else:  # если логин не первый, то делаем проверку на новые данные
        f = open(saved_data_file, 'r')
        data = f.readlines()
        f.close()
        file_array = [line.rstrip() for line in data]
        for i in range(len(file_array)):  # это всё - чтение файла и унификация данных для последующей проверки
            file_array[i] = file_array[i].split('|')
            file_array[i].pop()
        print(file_array)
        print(table_array)


def data_matching():
    global file_array, table_array
    new_data_marker = False  # флаг, что данные не совпадают
    is_reassemble_needed = False  # если данные не совпадают, то активируем флаг и пересобираем файл
    for i in range(len(file_array)):  # проверка на различие данных в массивах
        for j in range(len(file_array[i])):
            if file_array[i][j] != table_array[i][j]:
                new_data_marker = True
            if new_data_marker:
                is_reassemble_needed = True
                print('Несовпадение данных в таблице: ', file_array[i][0], ', в строке: ', file_array[i][1])
                new_data_marker = False
    if is_reassemble_needed:  # если найдено несовпадение, то заново собираем информацию с сайта и заносим в файл
        os.remove(saved_data_file)
        new_info_processing()


'''authentication(auth)
info_scrapping()
file_processing()
data_matching()'''
