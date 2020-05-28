import os
DATABASE_URL = os.environ['DATABASE_URL']
TOKEN = os.environ['BOT_TOKEN']
PASSKEY = os.environ["PASS_KEY"].encode()
APP_NAME = os.environ['APP_NAME']
RECHECK_TIME = int(os.environ['RECHECK_TIME'])
SESSION_TIMEOUT = int(os.environ['SESSION_TIMEOUT'])
ADMIN_ID = os.environ['ADMIN_ID']
