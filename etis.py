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
    r = sess.get(url, headers=headers)  # получение страницы
    soup = BeautifulSoup(r.content, 'html.parser')
    if soup.text.find('2396870', 0, len(soup.text)) != -1:
        return 0  # логин или пароль не верны
    elif soup.text.find('управление вузом', 0, len(soup.text)) != -1:
        return 1  # вход успешен
    else:
        return 2  # что-то с серверами


def info_scrapping(sess):  # сборка информации на странице
    table_array = []  # массив веб данных
    count_rows = 0  # сквозной id строки
    count_tables = 0  # id таблицы
    repeat_list = []  # список чтобы исключать повторяющиеся кт по одному и тому же предмету
    r = sess.get(url, headers=headers)  # получение страницы
    soup = BeautifulSoup(r.content, 'html.parser')  # парсинг страницы
    table_names = soup.findAll('h3')  # выделение имен всех таблиц
    a = soup.findAll('span', attrs={'class': 'submenu-item'})
    b = soup.findAll('a', attrs={'class': 'dashed'})
    trimester_names = []
    trimester = ''
    for i in b:  # циклы для выделения номера текущего триместра
        i = i.text.replace('\n', '')
        trimester_names.append(i)
    for i in a:
        i = i.text.replace('\n', '')
        if i not in trimester_names and i != 'оценки в триместре':
            for j in i:
                if j != ' ':
                    trimester += j
                else:
                    break
            if trimester != '':
                break
    table_names = [head.get_text() for head in table_names]  # выделение имен всех таблиц
    tables = soup.findAll('table', attrs={'class': 'common'})  # выделение всех таблиц
    for i in tables:  # формирование массива со строками таблицы оценок
        rows_max = (len(i) - 3) // 2
        row_id = 4
        for j in range(rows_max - 1):
            table_array.append([])

            subject = str(table_names[count_tables])
            control_point = i.contents[row_id].contents[1].text

            table_array[count_rows].append(subject)  # название предмета

            if repeat_list.count(subject+control_point) != 0:
                control_point += str(repeat_list.count(subject+control_point))
            repeat_list.append(subject+i.contents[row_id].contents[1].text)

            table_array[count_rows].append(control_point)  # название работы
            table_array[count_rows].append(i.contents[row_id].contents[7].text)  # текущий балл
            table_array[count_rows].append(i.contents[row_id].contents[9].text)  # проходной балл
            table_array[count_rows].append(i.contents[row_id].contents[13].text)  # максимальный балл
            table_array[count_rows].append(i.contents[row_id].contents[17]['title'])  # дата выставления оценки
            table_array[count_rows].append(trimester)  # номер триместра
            count_rows += 1
            row_id += 2
        count_tables += 1
    return table_array
