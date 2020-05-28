from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from Handlers import *
from Funcs import *


def run(updater_local):
    PORT = int(os.environ.get("PORT", "8443"))
    updater_local.start_webhook(listen="0.0.0.0",
                                port=PORT,
                                url_path=TOKEN)
    updater_local.bot.set_webhook(APP_NAME + TOKEN)


auth_dict = {}  # словарь с подключениями для пользователей
login_flag_dict = {}
password_flag_dict = {}
report_flag_dict = {}
session_dict = {}  # словарь всех подключений
login_dict = {}  # словарь логинов
pass_dict = {}  # словарь паролей
mail = {}

if __name__ == '__main__':
    updater = Updater(TOKEN)

    updater.dispatcher.add_handler(CommandHandler("start", start_handler))
    updater.dispatcher.add_handler(CommandHandler("login", login_handler))
    updater.dispatcher.add_handler(CommandHandler("user_data", user_data_handler))
    updater.dispatcher.add_handler(CommandHandler("authorize", auth_handler))
    updater.dispatcher.add_handler(CommandHandler("stop", stop_handler))
    updater.dispatcher.add_handler(CommandHandler("help", help_handler))
    updater.dispatcher.add_handler(CommandHandler("report", report_handler))
    updater.dispatcher.add_handler(CommandHandler("cancel_report", cancel_report_handler))
    updater.dispatcher.add_handler(CommandHandler("mail", mail_handler))

    updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), text_handler))
    run(updater)

    restart_auth_dict()
    
    main_loop(updater)
