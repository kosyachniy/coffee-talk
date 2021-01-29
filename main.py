# Libraries
## System
import json
import time
from multiprocessing import Process

## External
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

## Local
from _func.mongodb import db


# Params
## Keys
with open('keys.json', 'r') as file:
	keys = json.loads(file.read())
	TOKEN = keys['tg']['token']

## Sets
with open('sets.json', 'r') as file:
	sets = json.loads(file.read())
	TIMEZONE = sets['timezone']


# Global variables
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


# Funcs
## Get current day
def get_day():
	return int((time.time() + TIMEZONE * 3600) // 86400)


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

## Background process
def background_process():
	while True:
		notify_start = db['system'].find_one({'name': 'notify_start'}, {'_id': False, 'cont': True})['cont']
		notify_stop = db['system'].find_one({'name': 'notify_stop'}, {'_id': False, 'cont': True})['cont']

		if time.gmtime().tm_wday in (0, 3) and get_day() != notify_start:
			print('OK start')
			db['system'].update_one({'name': 'notify_start'}, {'$set': {'cont': get_day()}})

		if time.gmtime().tm_wday in (2,) and get_day() != notify_stop and notify_start:
			print('OK stop')
			db['system'].update_one({'name': 'notify_stop'}, {'$set': {'cont': get_day()}})

		time.sleep(100)

if __name__ == '__main__':
	# First setup
	notify_start = db['system'].find_one({'name': 'notify_start'}, {'_id': True})
	if not notify_start:
		db['system'].insert_one({
			'name': 'notify_start',
			'cont': 0,
		})

	notify_stop = db['system'].find_one({'name': 'notify_stop'}, {'_id': True})
	if not notify_stop:
		db['system'].insert_one({
			'name': 'notify_stop',
			'cont': 0,
		})

	# Background process
	p = Process(target=background_process)
	p.start()

	# Telegram process
	executor.start_polling(dp)