# Libraries
## System
import json

## External
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor


# Params
with open('keys.json', 'r') as file:
	keys = json.loads(file.read())
	TOKEN = keys['tg']['token']


# Global variables
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


# Telegram handlers
## Callback handlers
### Entry point
@dp.message_handler(commands=['start', 'help'])
async def handler_start(msg: types.Message):
	await bot.send_message(msg.from_user.id, 'Привет! Это бот программы Шагов.\n\nДавай быть продуктивными вместе!')

### Text
@dp.message_handler()
async def handler_text(msg: types.Message):
	await bot.send_message(msg.from_user.id, msg.text)


if __name__ == '__main__':
    executor.start_polling(dp)