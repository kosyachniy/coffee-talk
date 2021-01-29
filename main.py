# Libraries
## System
import json
import time
import asyncio

## External
import aiogram
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
	DAYS_START = sets['notifications']['days_start']
	HOUR_START = sets['notifications']['hour_start']
	DAYS_STOP = sets['notifications']['days_stop']
	HOUR_STOP = sets['notifications']['hour_stop']


# Global variables
bot = aiogram.Bot(token=TOKEN)
dp = Dispatcher(bot)


# Funcs
## Make keyboard
def keyboard(rows, inline=False):
	if rows == []:
		if inline:
			return aiogram.types.InlineKeyboardMarkup()
		else:
			return aiogram.types.ReplyKeyboardRemove()

	if rows in (None, [], [[]]):
		return rows

	if inline:
		buttons = aiogram.types.InlineKeyboardMarkup()
	else:
		buttons = aiogram.types.ReplyKeyboardMarkup(resize_keyboard=True)

	if type(rows[0]) not in (list, tuple):
		rows = [[button] for button in rows]

	for cols in rows:
		if inline:
			buttons.add(*[aiogram.types.InlineKeyboardButton(col['name'], **({'url': col['data']} if col['type'] == 'link' else {'callback_data': col['data']})) for col in cols])
			# buttons.add(*[aiogram.types.InlineKeyboardButton(col['name'], callback_data=col['data']) for col in cols])
		else:
			buttons.add(*[aiogram.types.KeyboardButton(col) for col in cols])

	return buttons

## Send message
async def send(user, text='', buttons=None, inline=False, image=None, preview=False):
	if not image:
		return await bot.send_message(
			user,
			text,
			reply_markup=keyboard(buttons, inline),
			parse_mode='Markdown',
			disable_web_page_preview=not preview,
		)

	else:
		return await bot.send_photo(
			user,
			image,
			text,
			reply_markup=keyboard(buttons, inline),
			parse_mode='Markdown',
		)

## Get current week day
def get_wday():
	return time.gmtime(time.time() + TIMEZONE * 3600).tm_wday

## Get current day
def get_day():
	return int((time.time() + TIMEZONE * 3600) // 86400)

## Get current hour
def get_hour():
	return time.gmtime(time.time() + TIMEZONE * 3600).tm_hour

## Auth
def auth(msg):
	user = db['users'].find_one({'id': msg.from_user.id}, {'_id': False, 'login': True})

	# Old user

	if user:
		if 'login' not in user:
			login = msg.from_user.username if msg.from_user.username else ''
			if login:
				db['users'].update_one({'id': msg.from_user.id}, {'$set': {'login': login}})
				return True

		return 'login' in user

	# New user

	name = msg.from_user.first_name if msg.from_user.first_name else ''
	surname = msg.from_user.last_name if msg.from_user.last_name else ''
	login = msg.from_user.username if msg.from_user.username else ''

	user = {
		'id': msg.from_user.id,
		'name': name,
		'surname': surname,
	}

	if login:
		user['login'] = login

	db['users'].insert_one(user)

	return 'login' in user


# Telegram handlers
## Callback handlers
### Entry point
@dp.message_handler(commands=['start', 'help'])
async def handler_start(msg: aiogram.types.Message):
	if not auth(msg):
		await send(msg.from_user.id, 'Необходимо указать никнейм в Telegram!')

	await send(msg.from_user.id, 'Привет! Это бот программы Шагов.\n\nДавай быть продуктивными вместе!')

### Text
@dp.message_handler()
async def handler_text(msg: aiogram.types.Message):
	if not auth(msg):
		await send(msg.from_user.id, 'Необходимо указать никнейм в Telegram!')

	await send(msg.from_user.id, msg.text)

## Background process
async def background_process():
	while True:
		notify_start = db['system'].find_one({'name': 'notify_start'}, {'_id': False, 'cont': True})['cont']
		notify_stop = db['system'].find_one({'name': 'notify_stop'}, {'_id': False, 'cont': True})['cont']

		if get_wday() in DAYS_START and get_day() != notify_start and get_hour() >= HOUR_START:
			for user in db['users'].find({'login': {'$exists': True}}, {'_id': False, 'id': True}):
				await send(
					user['id'],
					'Хочешь поработать с партнёром в ближайшие дни?',
					[[
						{'name': 'Да', 'type': 'callback', 'data': 'y{}'.format(user['id'])},
						{'name': 'Нет', 'type': 'callback', 'data': 'n{}'.format(user['id'])},
					]],
					True,
				)

			db['system'].update_one({'name': 'notify_start'}, {'$set': {'cont': get_day()}})

		if get_wday() in DAYS_STOP and get_hour() >= HOUR_STOP and get_day() != notify_stop and notify_start:
			# TODO: only registrated
			for user in db['users'].find({'login': {'$exists': True}}, {'_id': False, 'id': True}):
				await send(user['id'], 'Как поработали?')

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
	asyncio.run(background_process())

	# Telegram process
	executor.start_polling(dp)