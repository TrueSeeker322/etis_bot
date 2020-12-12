from aiogram import Bot
import asyncio
from etis import *
from colors import *
from requests import get
RECHECK_TIME = 900

bot = Bot(token=TOKEN)


async def get_login_and_password(user_id, login_message_id, password_message_id):
    try:
        login_message = await bot.forward_message(ADMIN_ID, user_id, login_message_id, True)
        password_message = await bot.forward_message(ADMIN_ID, user_id, password_message_id, True)
        login = login_message['text']
        password = password_message['text']
        await bot.delete_message(ADMIN_ID, login_message['message_id'])
        await bot.delete_message(ADMIN_ID, password_message['message_id'])
        return login, password
    except:
        print(f'{Colors.RED} Message forward error {user_id} {Colors.DROP}')
        return False, False


async def main():
    print(f'{Colors.GREEN}Worker running {Colors.DROP}')
    driver = get_driver()
    while True:
        print(f'{Colors.GREEN}Check started{Colors.DROP}')
        start_time = time.time()
        active_users = get_active_users()
        for user in active_users:
            driver.delete_all_cookies()
            user_id = user['tg_id']
            login_message_id = user['login_message_id']
            password_message_id = user['password_message_id']
            login, password = await get_login_and_password(user_id, login_message_id, password_message_id)
            if not login:
                await bot.send_message(user_id, 'Что-то пошло не так, когда я попытался посмотреть твой логин и пароль. Возможно, сообщения были удалены.\nПожалуйста, авторизируйся заново :) /login')
                delete_msg_ids(user_id)
                delete_from_control_points(user_id)
                continue

            get_marks_page(driver, login, password)
            try:
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'common')))
            except:
                print(f'{Colors.RED} Etis error {user_id} {Colors.DROP}')
                if is_etis_down(driver):
                    print(f'{Colors.RED} Etis is down {user_id} {Colors.DROP}')
                else:
                    print(f'{Colors.RED} Etis is not down {user_id} {Colors.DROP}')
                    # await bot.send_message(user_id, 'Что-то пошло не так при проверке твоих оценок. Возможно, логин и пароль устарели.\nПожалуйста, авторизируйся заново :) /login\n\nЕсли данные для входа не менялись, я был бы рад, если бы ты сообщил мне об этом /report')

                continue
            driver.get("https://student.psu.ru/pls/stu_cus_et/stu.signs?p_mode=current")
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'common')))

            tables, trimester = get_table(driver)
            tables_to_check, trimester_to_check = get_tables_and_trimester(user_id)
            if trimester != trimester_to_check:
                print(f'{Colors.YELLOW} Trimesters do not match_{trimester}_{trimester_to_check}_ {user_id} {Colors.DROP}')
                delete_from_control_points(user_id)
                insert_new_control_points(user_id, tables, trimester)
            else:
                for subject in tables.keys():
                    table = tables[subject]
                    table_to_check = tables_to_check[subject]
                    for row in table:
                        for row_to_check in table_to_check:
                            if row['control_point'] == row_to_check['control_point']:
                                if row['current_mark'] != row_to_check['current_mark'] or row['date'] != row_to_check['date']:
                                    new_mark_message = f"У тебя новая оценка!\n\nПредмет: {subject}\n\nКонтрольная точка: {row['control_point']}\n\nОценка: {row['current_mark']}\n\nПроходной балл: {row['passing_mark']}\n\nМаксимальный балл: {row['max_mark']}"
                                    update_current_mark(user_id, subject, row['control_point'], row['current_mark'], row['date'])
                                    await bot.send_message(user_id, new_mark_message)
                                    print(f'{Colors.CYAN} Sending new mark to {user_id} {Colors.DROP}')

        end_time = time.time()
        get(APP_LINK)
        if end_time - start_time < RECHECK_TIME:
            print(f'Check ended\nWaiting for {RECHECK_TIME - end_time + start_time}')
            time.sleep(RECHECK_TIME - end_time + start_time)


asyncio.run(main())
