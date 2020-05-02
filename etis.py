import requests
import os
from fake_useragent import UserAgent
from bs4 import BeautifulSoup


url = 'https://student.psu.ru/pls/stu_cus_et/stu.signs?p_mode=current'
url_login = 'https://student.psu.ru/pls/stu_cus_et/stu.login'

headers = {
    'User-Agent': UserAgent().chrome
}


def authentication(auth, sess):  # функция аутентификации
    code = sess.post(url_login, data=auth, headers=headers)  # Пост запрос на авторизацию, вернет код ответа сервера
    if str(code) != '<Response [200]>':
        return 2
    r = sess.get(url, headers=headers)  # получение страницы
    soup = BeautifulSoup(r.content, 'html.parser')
    if soup.text.find('2396870', 0, len(soup.text)) == -1:
        return 1
    else:
        return 0


def info_scrapping(sess):  # сборка информации на странице
    table_array = []  # массив веб данных
    count_rows = 0  # сквозной id строки
    count_tables = 0  # id таблицы
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
            table_array[count_rows].append(i.contents[row_id].contents[9].text)  # проходной балл
            table_array[count_rows].append(i.contents[row_id].contents[13].text)  # максимальный балл
            count_rows += 1
            row_id += 2
        count_tables += 1
    return table_array, table_names
