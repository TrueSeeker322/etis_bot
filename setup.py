from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from colors import *
from etis import *

WEBHOOK_HOST = f'https://{APP_NAME}.herokuapp.com'
WEBHOOK_PATH = "/webhook/" + TOKEN
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.environ.get("PORT", "8443"))


class States(StatesGroup):
    LOGIN_STATE = State()
    PASSWORD_STATE = State()
    REPORT_STATE = State()


bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


@dp.message_handler(commands=['start'], state='*')
async def process_start_command(message: types.Message):
    user_insert(message.from_user.id)
    await bot.send_message(message.from_user.id, 'Привет!Я помогу тебе не пропустить новые оценки в ЕТИСе!\nНажми /login чтобы начать\nИли /help для просмотра справки.')


@dp.message_handler(commands=['help'], state='*')
async def process_help_command(message: types.Message):
    await bot.send_message(message.from_user.id, 'Бот призван помочь студентам вовремя узнавать об оценках в их личном кабинете.\n'
                                                 'Чтобы бот начал работу, введи или нажми /login и следуй инструкциям бота.\n\n'
                                                 'Чтобы перестать получать уведомления и удалить всю информацию о себе из бота, введите /stop.\n\n'
                                                 'Бот не хранит твой логин и пароль на своих серверах. Вместо этого при каждой проверке оценок он каждый раз смотрит на твои сообщения, в которых указаны эти данные.\n'
                                                 'Поэтому важно, чтобы эти сообщения не удалялись.\n'
                                                 'Внимание! Бот не несет ответственность за сохранность вводимых данных.\n'
                                                 'Пользователь добровольно передаёт данные от личного кабинета ЕТИС для использования внутри бота.\n'
                                                 'Данные не передаются третьим лицам.\n\n'
                                                 'Бот находится в стадии разработки, потому возможны ошибки и некорректное поведенеие.\n'
                                                 'Если обнаружилась ошибка или ты просто хочешь отправить отзыв о работе - введи или нажми /report и следуй инструкциям бота')


@dp.message_handler(commands=['stop'], state='*')
async def process_help_command(message: types.Message):
    delete_msg_ids(message.from_user.id)
    delete_from_control_points(message.from_user.id)
    await bot.send_message(message.from_user.id, 'Бот успешно выключен')


@dp.message_handler(commands=['report'], state='*')
async def process_report_command(message: types.Message):
    await bot.send_message(message.from_user.id, 'В следующем сообщении отправь свой отзыв о работе бота. \n\nСпасибо за обратную связь :)')
    await States.REPORT_STATE.set()


@dp.message_handler(state=States.REPORT_STATE)
async def login_state_case_met(message: types.Message, state: FSMContext):
    await bot.send_message(ADMIN_ID, f'Новый репорт:\n\n{message.text}')
    await bot.send_message(message.from_user.id, 'Отзыв успешно отправлен')
    await state.finish()


@dp.message_handler(commands=['login'], state='*')
async def login_command(message: types.Message):
    user_insert(message.from_user.id)
    await bot.send_message(message.from_user.id, 'Введи логин ЕТИС: ')
    await States.LOGIN_STATE.set()


@dp.message_handler(state=States.LOGIN_STATE)
async def login_state_case_met(message: types.Message, state: FSMContext):
    await bot.send_message(message.from_user.id, 'Введите пароль: ')
    await state.update_data(login=message.text.lower())
    await state.update_data(login_msg_id=message.message_id)
    await States.PASSWORD_STATE.set()


@dp.message_handler(state=States.PASSWORD_STATE)
async def password_state_case_met(message: types.Message, state: FSMContext):
    await state.update_data(password=message.text)
    await state.update_data(password_msg_id=message.message_id)
    await bot.send_message(message.from_user.id, 'Проверяю твои данные')
    data = await state.get_data()
    print(f'{Colors.BLUE} data: {data} {Colors.DROP}')
    if check_auth(message.from_user.id, data['login'], data['password']):
        await bot.send_message(message.from_user.id, 'Авторизация успешно пройдена.\n\nПожалуйста, не удаляй сообщения с логином и паролем. Я не храню твои персональные данные, поэтому мне приходится каждый раз заглядывать на эти сообщения, чтобы держать тебя в курсе твоих оценок:) ')
        set_msg_ids(message.from_user.id, data['login_msg_id'], data['password_msg_id'])
    else:
        await bot.send_message(message.from_user.id, 'Что-то пошло не так во время авторизации.\nПерепроверь введённые данные и попробуй снова. /login')
        await state.finish()


@dp.message_handler()
async def messages_handler(message: types.Message):
    await bot.send_message(message.from_user.id, 'Я тебя не понимаю.\nВведи /help для просмотра справки')


async def on_startup(dispatcher):
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(dispatcher):
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()


async def set_hook():
    await bot.set_webhook(WEBHOOK_URL)
    print(await bot.get_webhook_info())


print(f'{Colors.GREEN}Bot starts {Colors.DROP}')
# set_hook()
executor.start_webhook(
    dispatcher=dp,
    webhook_path=WEBHOOK_PATH,
    on_startup=on_startup,
    on_shutdown=on_shutdown,
    skip_updates=True,
    host=WEBAPP_HOST,
    port=WEBAPP_PORT)
