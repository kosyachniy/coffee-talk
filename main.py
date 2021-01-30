# TODO: история пар + вывод статы за месяц
# TODO: сохранение фидбека
# TODO: сохранение рейтинга
# TODO: запрос указания логина
# TODO: инструкция

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
	DELAY = sets['delay']
	ADMINS = sets['admins']


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
		login = msg.from_user.username if msg.from_user.username else ''
		if login and (('login' in user and user['login'] != login) or 'login' not in user):
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
# {"id": "586534174085442072", "from": {"id": 136563129, "is_bot": false, "first_name": "Alexey", "last_name": "Poloz", "username": "kosyachniy", "language_code": "ru"}, "message": {"message_id": 41, "from": {"id": 1540757891, "is_bot": true, "first_name": "Coffee Talk", "username": "coffee_talk_bot"}, "chat": {"id": 136563129, "first_name": "Alexey", "last_name": "Poloz", "username": "kosyachniy", "type": "private"}, "date": 1611942216, "text": "Хочешь поработать с партнёром в ближайшие дни?", "reply_markup": {"inline_keyboard": [[{"text": "Да", "callback_data": "y"}, {"text": "Нет", "callback_data": "n"}]]}}, "chat_instance": "-2955349629926715065", "data": "y"}

### Yes
@dp.callback_query_handler(lambda call: call.data == 'y')
async def handler_yes(call):
	await bot.answer_callback_query(call.id)

	if call.message.text[:8] != 'Напарник':
		try:
			await bot.delete_message(call.from_user.id, call.message.message_id)
		except Exception as e:
			print('ERROR `delete_message` in `handler_yes`', e)

	user = db['users'].find_one({
		'id': {'$ne': call.from_user.id},
		'waiting': {'$exists': True},
		'match': {'$ne': call.from_user.id},
	}, {'_id': False, 'id': True, 'login': True})

	if user:
		await send(
			call.from_user.id,
			'Напарник найден!\nСвяжись с ним: @{}'.format(user['login']),
			[[
				{'name': 'Нужен ещё один напарник?', 'type': 'callback', 'data': 'y'},
			]],
			True,
		)
		db['users'].update_one({'id': call.from_user.id}, {
			'$push': {'match': user['id']},
			'$unset': {'waiting': ''},
		})

		await send(
			user['id'],
			'Напарник найден!\nСвяжись с ним: @{}'.format(call.from_user.username),
			[[
				{'name': 'Нужен ещё один напарник?', 'type': 'callback', 'data': 'y'},
			]],
			True,
		)
		db['users'].update_one({'id': user['id']}, {
			'$push': {'match': call.from_user.id},
			'$unset': {'waiting': ''},
		})

		# Save match

		db['match'].insert_one({
			'user1': user['id'],
			'user2': call.from_user.id,
			'time': time.time(),
		})

	else:
		await send(
			call.from_user.id,
			'Вы будете соединены со следующим присоединившимся участником!',
			[[
				{'name': 'Я передумал 😕', 'type': 'callback', 'data': 'n'},
			]],
			True,
		)

		db['users'].update_one({'id': call.from_user.id}, {'$set': {'waiting': True}})

### No
@dp.callback_query_handler(lambda call: call.data == 'n')
async def handler_no(call):
	await bot.answer_callback_query(call.id)

	try:
		await bot.delete_message(call.from_user.id, call.message.message_id)
	except Exception as e:
		print('ERROR `delete_message` in `handler_no`', e)

	await send(
		call.from_user.id,
		'Хорошего дня ;)',
		[[
			{'name': 'Я передумал!', 'type': 'callback', 'data': 'y'},
		]],
		True,
	)

	user = db['users'].find_one({'id': call.from_user.id, 'waiting': {'$exists': True}}, {'_id': True})
	if user:
		db['users'].update_one({'id': call.from_user.id}, {'$unset': {'waiting': ''}})

### No
@dp.callback_query_handler(lambda call: call.data[0] == 'r')
async def handler_rating(call):
	await bot.answer_callback_query(call.id)
	await send(call.from_user.id, 'Спасибо за оценку!\nЕсли у Вас остались какие-либо замечания или предложения, просто отправьте их в этот чат.')

	try:
		await bot.delete_message(call.from_user.id, call.message.message_id)
	except Exception as e:
		print('ERROR `delete_message` in `handler_rating`', e)

	# Save rating

	db['rating'].insert_one({
		'user': call.from_user.id,
		'score': int(call.data[1]),
		'time': time.time(),
	})

## Entry point
@dp.message_handler(commands=['start', 'help'])
async def handler_start(msg: aiogram.types.Message):
	if not auth(msg):
		await send(msg.from_user.id, 'Необходимо указать никнейм в Telegram!')
		return

	await send(
		msg.from_user.id,
		'Привет! Это бот программы Шагов.\n\nДавай быть продуктивными вместе!',
		['Статистика', 'Отзывы'] if msg.from_user.id in ADMINS else None,
	)

	# await send(
	# 	msg.from_user.id,
	# 	'Хочешь поработать с партнёром в ближайшие дни?',
	# 	[[
	# 		{'name': 'Да', 'type': 'callback', 'data': 'y'},
	# 		{'name': 'Нет', 'type': 'callback', 'data': 'n'},
	# 	]],
	# 	True,
	# )

## Buttons
@dp.message_handler(lambda msg: msg.text == 'Статистика')
async def handler_text(msg: aiogram.types.Message):
	if msg.from_user.id not in ADMINS:
		await send(msg.from_user.id, 'У Вас нет доступа!')
		return

	rating_all = [i['score'] for i in db['rating'].find({}, {'_id': False, 'score': True})]
	rating_all = round(sum(rating_all) / len(rating_all), 2) if len(rating_all) else 0

	rating_month = [i['score'] for i in db['rating'].find({'time': {'$gte': time.time() - 2592000}}, {'_id': False, 'score': True})]
	rating_month = round(sum(rating_month) / len(rating_month), 2) if len(rating_month) else 0

	match_all = db['match'].find({}, {'_id': False, 'score': True}).count()
	match_month = db['match'].find({'time': {'$gte': time.time() - 2592000}}, {'_id': False, 'score': True}).count()

	await send(
		msg.from_user.id,
		'Средняя оценка: {} ({} за месяц)\nВсего метчей: {} ({} за месяц)'.format(
			rating_all, rating_month, match_all, match_month,
		),
	)

## Main handler
@dp.message_handler()
async def handler_text(msg: aiogram.types.Message):
	if not auth(msg):
		await send(msg.from_user.id, 'Необходимо указать никнейм в Telegram!')
		return

	await send(msg.from_user.id, 'Ваш отзыв сохранён!')

	# Save feedback

	db['feedback'].insert_one({
		'user': msg.from_user.id,
		'text': msg.text,
		'time': time.time(),
	})

# Background process
async def background_process():
	notify_start = db['system'].find_one({'name': 'notify_start'}, {'_id': False, 'cont': True})['cont']
	notify_stop = db['system'].find_one({'name': 'notify_stop'}, {'_id': False, 'cont': True})['cont']

	if get_wday() in DAYS_START and get_day() != notify_start and get_hour() >= HOUR_START:
		for user in db['users'].find({'login': {'$exists': True}}, {'_id': False, 'id': True}):
			await send(
				user['id'],
				'Хочешь поработать с партнёром в ближайшие дни?',
				[[
					{'name': 'Да', 'type': 'callback', 'data': 'y'},
					{'name': 'Нет', 'type': 'callback', 'data': 'n'},
				]],
				True,
			)

		db['system'].update_one({'name': 'notify_start'}, {'$set': {'cont': get_day()}})

	if get_wday() in DAYS_STOP and get_hour() >= HOUR_STOP and get_day() != notify_stop and notify_start:
		for user in db['users'].find({'match': {'$exists': True}}, {'_id': False, 'id': True}):
			await send(
				user['id'],
				'Как поработали?',
				[[
					{'name': '★', 'type': 'callback', 'data': 'r1'},
					{'name': '★★', 'type': 'callback', 'data': 'r2'},
					{'name': '★★★', 'type': 'callback', 'data': 'r3'},
					{'name': '★★★★', 'type': 'callback', 'data': 'r4'},
					{'name': '★★★★★', 'type': 'callback', 'data': 'r5'},
				]],
				True,
			)

			db['users'].update_one({'id': user['id']}, {'$unset': {'match': ''}})

		db['system'].update_one({'name': 'notify_stop'}, {'$set': {'cont': get_day()}})


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
	def repeat(coro, loop):
		asyncio.ensure_future(coro(), loop=loop)
		loop.call_later(DELAY, repeat, coro, loop)

	loop = asyncio.get_event_loop()
	loop.call_later(0, repeat, background_process, loop)

	# Telegram process
	executor.start_polling(dp, skip_updates=True, loop=loop)