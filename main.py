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
	CHAT = sets['chat']


# Global variables
bot = aiogram.Bot(token=TOKEN)
dp = Dispatcher(bot)
global_message = set()


# Funcs
## Check entry
async def check_entry(chat, user):
	try:
		user_type = await bot.get_chat_member(chat, user)
		print(user_type.status)
		if user_type.status in ('creator', 'administrator', 'member'):
			return True
		return False
	except:
		return False

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
async def send(user, text='', buttons=None, inline=False, image=None, preview=False, parse=True):
    while text:
        text_cur = text[:4096]
        text = text[4096:]

        try:
            if not image:
                await bot.send_message(
                    user,
                    text_cur,
                    reply_markup=keyboard(buttons, inline),
                    parse_mode='Markdown' if parse else None,
                    disable_web_page_preview=not preview,
                )

            else:
                await bot.send_photo(
                    user,
                    image,
                    text_cur,
                    reply_markup=keyboard(buttons, inline),
                    parse_mode='Markdown' if parse else None,
                )
        except Exception as e:
            print('ERROR `send` in `handler_text`', e)

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
	user = db['users'].find_one({'id': msg.from_user.id}, {
		'_id': False,
		'id': True, # ! Нужно чтобы если был пустой логин, не создавал новый акк
		'login': True,
	})

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
# {"id": "586534174085442072", "from": {"id": 136563129, "is_bot": false, "first_name": "Alexey", "last_name": "Poloz", "username": "kosyachniy", "language_code": "ru"}, "message": {"message_id": 41, "from": {"id": 1540757891, "is_bot": true, "first_name": "Coffee Talk", "username": "coffee_talk_bot"}, "chat": {"id": 136563129, "first_name": "Alexey", "last_name": "Poloz", "username": "kosyachniy", "type": "private"}, "date": 1611942216, "text": "Хочешь поработать на этой неделе? ☕️", "reply_markup": {"inline_keyboard": [[{"text": "Да", "callback_data": "y"}, {"text": "Нет", "callback_data": "n"}]]}}, "chat_instance": "-2955349629926715065", "data": "y"}

### Yes
@dp.callback_query_handler(lambda call: call.data == 'y')
async def handler_yes(call):
	await bot.answer_callback_query(call.id)

	if not await check_entry(CHAT, call.from_user.id):
		await send(call.from_user.id, 'Вы не состоите в чате!')
		return

	if call.message.text[:8] != 'Партнёр':
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
			'Ура, партнёр найден!\nСкорее свяжись с ним: @{}'.format(user['login'].replace('_', '\\_')),
			[[
				{'name': 'Нужен ещё один партнёр?', 'type': 'callback', 'data': 'y'},
			]],
			True,
		)
		db['users'].update_one({'id': call.from_user.id}, {
			'$push': {'match': user['id']},
			'$unset': {'waiting': ''},
		})

		await send(
			user['id'],
			'Ура, партнёр найден!\nСкорее свяжись с ним: @{}'.format(call.from_user.username.replace('_', '\\_')),
			[[
				{'name': 'Нужен ещё один партнёр?', 'type': 'callback', 'data': 'y'},
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
				{'name': 'Не получается.. Отменить ☔️', 'type': 'callback', 'data': 'n'},
			]],
			True,
		)

		db['users'].update_one({'id': call.from_user.id}, {'$set': {'waiting': True}})

### No
@dp.callback_query_handler(lambda call: call.data == 'n')
async def handler_no(call):
	await bot.answer_callback_query(call.id)

	if not await check_entry(CHAT, call.from_user.id):
		await send(call.from_user.id, 'Вы не состоите в чате!')
		return

	try:
		await bot.delete_message(call.from_user.id, call.message.message_id)
	except Exception as e:
		print('ERROR `delete_message` in `handler_no`', e)

	await send(
		call.from_user.id,
		'Отменено! 😉\nХорошего дня и до скорой связи!',
		[[
			{'name': 'Я снова могу! Найти партнёра 😀', 'type': 'callback', 'data': 'y'},
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

	await send(call.from_user.id, 'Спасибо за оценку!\nЕсли у тебя есть обратная связь, замечания или предложения, просто напиши их в этот чат.')

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

### Check login
@dp.callback_query_handler(lambda call: call.data[0] == 'u')
async def handler_updated(call):
	await bot.answer_callback_query(call.id)

	if not await check_entry(CHAT, call.from_user.id):
		await send(call.from_user.id, 'Вы не состоите в чате!')
		return

	try:
		await bot.delete_message(call.from_user.id, call.message.message_id)
	except Exception as e:
		print('ERROR `delete_message` in `handler_updated`', e)

	if not auth(call):
		await send(
			call.from_user.id,
			'Никнейм Telegram не указан! Это можно сделать в настройках приложения.',
			[{'name': 'Указал', 'type': 'callback', 'data': 'u'}],
			True,
		)
		return

	await send(
		call.from_user.id,
		'Отлично! Хочешь поработать на этой неделе? ☕️',
		[[
			{'name': 'Да', 'type': 'callback', 'data': 'y'},
			{'name': 'Нет', 'type': 'callback', 'data': 'n'},
		]],
		True,
	)

### Start
@dp.callback_query_handler(lambda call: call.data[0] == 's')
async def handler_start(call):
	await bot.answer_callback_query(call.id)

	if not await check_entry(CHAT, call.from_user.id):
		await send(call.from_user.id, 'Вы не состоите в чате!')
		return

	await send(
		call.from_user.id,
		'Ура! 🎗\n\nТеперь ты с нами!\nКраткая инструкция:\n\n1) По понедельникам и четвергам я буду спрашивать, хочешь ли ты поработать с кем-то в ближайшие 3 дня. Если да - я буду присылать тебе пару сразу, как только она найдётся :)\n\nЧтобы договориться о звонке и выбрать время, напиши партнеру в Telegram.\n\n2) Я собираю пары по активности: чем быстрее твой ответ боту - тем активнее даётся партнёр.\n\n3) Если ты хочешь делать работу чаще 1 раза в 3-4 дня, нажимай кнопку «Нужен ещё один партнёр?»\n\n4) Если партнёр не отвечает, нажимай кнопку «Нужен ещё один партнёр?» и я подберу тебе нового\n\nПлодотворных работ!\n🌊',
		['Статистика', 'Отправить всем'] if call.from_user.id in ADMINS else None,
	)

	if not auth(call):
		await send(
			call.from_user.id,
			'Вам необходимо указать никнейм в Telegram, чтобы партнёр смог связаться с Вами!',
			[{'name': 'Указал', 'type': 'callback', 'data': 'u'}],
			True,
		)
		return

	await send(
		call.from_user.id,
		'Хочешь поработать на этой неделе? ☕️',
		[[
			{'name': 'Да', 'type': 'callback', 'data': 'y'},
			{'name': 'Нет', 'type': 'callback', 'data': 'n'},
		]],
		True,
	)

## Entry point
@dp.message_handler(commands=['start', 'help'])
async def handler_start(msg: aiogram.types.Message):
	await send(
		msg.from_user.id,
		'Привет! 🦚\n\nЯ бот поиска партнёра для совместной работы по Анкете Кристины Макаровой.\n\nДва раза в неделю я буду предлагать тебе поработать с одним из участников Программы Шагов.\n\nНажми «Начать» и прочитай короткую инструкцию.\n🌁',
		[{'name': 'Отлично, начинаем!', 'type': 'callback', 'data': 's'}],
		True,
	)

## Buttons
### Stats
@dp.message_handler(lambda msg: msg.text == 'Статистика')
async def handler_text(msg: aiogram.types.Message):
	print(ADMINS, msg.from_user.id)

	if msg.from_user.id not in ADMINS:
		await send(msg.from_user.id, 'У Вас нет доступа!')
		return

	timestamp = time.time()
	timestamp_month = timestamp - 2592000

	rating_all = [i['score'] for i in db['rating'].find({}, {'_id': False, 'score': True})]
	rating_all = round(sum(rating_all) / len(rating_all), 2) if len(rating_all) else 0

	rating_month = [i['score'] for i in db['rating'].find({'time': {'$gte': timestamp_month}}, {'_id': False, 'score': True})]
	rating_month = round(sum(rating_month) / len(rating_month), 2) if len(rating_month) else 0

	match_all = db['match'].find({}, {'_id': False, 'score': True}).count()
	match_month = db['match'].find({'time': {'$gte': timestamp_month}}, {'_id': False, 'score': True}).count()

	await send(
		msg.from_user.id,
		'Средняя оценка: {} ({} за месяц)\nВсего метчей: {} ({} за месяц)'.format(
			rating_all, rating_month, match_all, match_month,
		),
		['Статистика', 'Отправить всем'] if msg.from_user.id in ADMINS else None,
	)

	# Advanced

	text = 'Активность за последний месяц:\n\n'

	db_filter = {'_id': False, 'id': True, 'login': True}
	for user in db['users'].find({'login': {'$exists': True}}, db_filter):
		if not await check_entry(CHAT, user['id']):
			continue

		text += '@{} '.format(user['login'])
		partners = set()
		matches = 0

		try:
			rate = db['rating'].find({'user': user['id']}, {'_id': False}).sort('time', -1)[0]['score']
		except:
			pass
		else:
			text += '| {}★ '.format(rate)

		for match in db['match'].find({
			'time': {'$gte': timestamp_month},
			'$or': [{'user1': user['id']}, {'user2': user['id']}],
		}, {'_id': False}):
			matches += 1
			partner_id = (match['user1'], match['user2'])[match['user1'] == user['id']]
			partner = db['users'].find_one({'id': partner_id}, {'_id': False, 'login': True})
			partners.add(partner['login'])

		def ends(cont):
			if cont % 10 == 1 and cont % 100 != 11:
				return ''

			if cont % 10 in (2, 3, 4) and cont % 100 not in (12, 13, 14):
				return 'а'

			return 'ей'

		text += '| {} метч{}'.format(matches, ends(matches))

		if len(partners):
			text += '\nПары: '

			for partner in partners:
				text += '@{} '.format(partner)

		text += '\n\n'

	await send(
		msg.from_user.id,
		text.replace('_', '\\_'),
		['Статистика', 'Отправить всем'] if msg.from_user.id in ADMINS else None,
	)

### Send to all
@dp.message_handler(lambda msg: msg.text == 'Отправить всем')
async def handler_text(msg: aiogram.types.Message):
	if msg.from_user.id not in ADMINS:
		await send(msg.from_user.id, 'У Вас нет доступа!')
		return

	global_message.add(msg.from_user.id)

	await send(msg.from_user.id, 'Напишите сообщение, которое будет отправлено всем:')

## Main handler
@dp.message_handler()
async def handler_text(msg: aiogram.types.Message):
	if not await check_entry(CHAT, msg.from_user.id):
		await send(call.from_user.id, 'Вы не состоите в чате!')
		return

	if not auth(msg):
		await send(
			msg.from_user.id,
			'Никнейм Telegram не указан! Это можно сделать в настройках приложения.',
			[{'name': 'Указал', 'type': 'callback', 'data': 'u'}],
			True,
		)
		return

	# Send to all

	if msg.from_user.id in global_message:
		global_message.remove(msg.from_user.id)

		for user in db['users'].find({'login': {'$exists': True}}, {'_id': False, 'id': True}):
			if await check_entry(CHAT, user['id']):
				await send(user['id'], msg.text, parse=False)

		await send(msg.from_user.id, 'Отправлено всем!')
		return

	# Send feedback

	await send(msg.from_user.id, 'Передал обратную связь!')

	# Save feedback

	db['feedback'].insert_one({
		'user': msg.from_user.id,
		'text': msg.text,
		'time': time.time(),
	})

	for admin in ADMINS:
		try:
			await send(admin, 'Сообщение от @{}\n\n{}'.format(msg.from_user.username.replace('_', '\\_'), msg.text))
		except Exception as e:
			print('ERROR `send` in `handler_text`', e)

# Background process
async def background_process():
	notify_start = db['system'].find_one({'name': 'notify_start'}, {'_id': False, 'cont': True})['cont']
	notify_stop = db['system'].find_one({'name': 'notify_stop'}, {'_id': False, 'cont': True})['cont']

	if get_wday() in DAYS_START and get_day() != notify_start and get_hour() >= HOUR_START:
		for user in db['users'].find({'login': {'$exists': True}}, {'_id': False, 'id': True}):
			if not await check_entry(CHAT, user['id']):
				continue

			await send(
				user['id'],
				'Хочешь поработать на этой неделе? ☕️',
				[[
					{'name': 'Да', 'type': 'callback', 'data': 'y'},
					{'name': 'Нет', 'type': 'callback', 'data': 'n'},
				]],
				True,
			)

		db['system'].update_one({'name': 'notify_start'}, {'$set': {'cont': get_day()}})

	if get_wday() in DAYS_STOP and get_hour() >= HOUR_STOP and get_day() != notify_stop:
		for user in db['users'].find({'match': {'$exists': True}}, {'_id': False, 'id': True}):
			await send(
				user['id'],
				'Как поработали?',
				[
					[{'name': 'Отлично! 🔥', 'type': 'callback', 'data': 'r5'}],
					[{'name': 'Хорошо 🥰', 'type': 'callback', 'data': 'r4'}],
					[{'name': 'Нормально 😐', 'type': 'callback', 'data': 'r3'}],
					[{'name': 'Ну так 🥴', 'type': 'callback', 'data': 'r2'}],
				],
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