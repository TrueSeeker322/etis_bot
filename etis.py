import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from data_base_funcs import *


def get_driver():
    """Получение драйвера"""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
    return driver


def get_marks_page(driver, login, password):
    """Получение страницы с оценками"""
    driver.get("https://student.psu.ru/pls/stu_cus_et/stu.signs?p_mode=current")
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'login')))
    except:
        print(driver.page_source)
    id_field = driver.find_element_by_id('login')
    pass_field = driver.find_element_by_id('password')
    button = driver.find_element_by_id('sbmt')

    id_field.send_keys(login)
    time.sleep(0.5)
    pass_field.send_keys(password)
    time.sleep(0.5)

    button.click()
    return driver


def check_auth(user_id, login, password):
    """Провекра авторизации, при вводе логина и пароля в чате с ботом"""
    driver = get_driver()
    driver = get_marks_page(driver, login, password)
    try:
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'common')))
    except:
        print('woto ne tak')
        print(driver.page_source)
        return False
    driver.get("https://student.psu.ru/pls/stu_cus_et/stu.signs?p_mode=current")
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'common')))

    upload_table(user_id, driver)
    driver.quit()
    return True


def get_table(driver):
    """Парсинг таблицы оценок"""
    table_dict = {}
    table_names = []

    submenu = driver.find_elements_by_class_name('submenu')[1]
    submenu_items = submenu.find_elements_by_class_name('submenu-item')
    trimester = None
    for item in submenu_items:
        try:
            item.find_element_by_tag_name('a')
        except NoSuchElementException:
            trimester = item.text.split(' триместр')[0]

    span9 = driver.find_element_by_class_name('span9')
    h3 = span9.find_elements_by_tag_name('h3')
    for i in h3:
        table_names.append(i.text)
    tables = span9.find_elements_by_tag_name('table')
    table_counter = 0
    for table in tables:
        trs = table.find_elements_by_tag_name('tr')[2:-1]  # обрезаем первые две и последнюю строки потому что там хедеры и футер таблицы
        table_list = []
        repeat_list = []  # список чтобы исключать повторяющиеся кт по одному и тому же предмету
        for tr in trs:
            tds = tr.find_elements_by_tag_name('td')

            control_point = tds[0].text
            if control_point in repeat_list:
                original_control_point_name = control_point
                control_point += f' {repeat_list.count(control_point)}'
                repeat_list.append(original_control_point_name)
            else:
                repeat_list.append(control_point)

            current_mark = tds[3].text
            passing_mark = tds[4].text
            max_mark = tds[6].text
            date = tds[8].get_attribute('title')
            table_list.append({'control_point': control_point,
                               'current_mark': current_mark,
                               'passing_mark': passing_mark,
                               'max_mark': max_mark,
                               'date': date})
        table_dict[table_names[table_counter]] = table_list
        table_counter += 1
    return table_dict, trimester


def upload_table(user_id, driver):
    tables, trimester = get_table(driver)
    delete_from_control_points(user_id)
    insert_new_control_points(user_id, tables, trimester)
    print(f'New user data {user_id}')


def is_etis_down(driver: webdriver.Chrome):
    driver.delete_all_cookies()
    driver.get('https://student.psu.ru/pls/stu_cus_et/stu.teach_plan')
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'sbmt')))
    except:
        return True
    else:
        return False
