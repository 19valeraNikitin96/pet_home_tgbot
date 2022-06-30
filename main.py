#!/usr/bin python3
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.
import logging
import os
from enum import Enum

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from api import PetHome
from api.v1 import PetHomeImpl

PET_HOME_TOKEN = os.environ['PET_HOME_TOKEN']
PET_HOME_ADDR = os.environ['PET_HOME_ADDR']
PET_HOME_PORT = os.environ['PET_HOME_PORT']


class Action(Enum):
    WELCOME = 'welcome'
    REGISTRATION = 'registration'
    AUTHORIZATION = 'authorization'
    LOGIN_ENTERING = 'login_entering'
    PASSWORD_ENTERING = 'password_entering'
    MAIN = 'main'
    VIEW_AD = 'view_ad'
    VIEW_ACCOUNT = 'view_account'
    GET_LIST_OF_ADVERTISEMENTS = 'get_list_of_advertisements'
    GET_LIST_OF_CREATED_ADVERTISEMENTS = 'get_list_of_created_advertisements'
    CREATE_AD = 'create_advertisement'
    DEL_AD = 'delete_advertisement'
    WAITING_FOR_AD_INFO = 'waiting_for_add_info'
    WAITING_FOR_AD_ID = 'waiting_for_add_id'
    BACK = 'back'


class AdType(Enum):
    FOUND = 'знайшов'
    LOST = 'загубив'
    OBSERVED = 'спостерігаю'

    @staticmethod
    def get_by(ua_name: str):
        ua_name = ua_name.strip().lower()
        for t in AdType:
            if t.value == ua_name:
                return t

        raise Exception('Could not map from UA name to type')


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


class User(object):

    def __init__(self, msg_id):
        self.msg_id = msg_id
        self.cache = dict()
        self.api: PetHome = None
        self.current_action = Action.WELCOME


# {12345: {'action': Action.LOGIN_ENTERING, 'cache': dict()}}
users = dict()
# use next lines for debug
# _tg_number = <USER TG ID>
# _msg_id = 300
# _tmp_user = User(_msg_id)
# _tmp_user.api = PetHomeImpl('Bogdan1980', '12345', PET_HOME_ADDR, PET_HOME_PORT)
# _tmp_user.cache = dict()
# _tmp_user.current_action = Action.MAIN
# users[_tg_number] = _tmp_user

# button constans
_main = InlineKeyboardButton("На головну 🔙", callback_data=Action.MAIN.value)


def _display_main_page(context, user_id, chat_id, text = "Головна"):
    u: User = users[user_id]
    u.current_action = Action.MAIN
    keyboard = [
        [
            InlineKeyboardButton("Створити", callback_data=Action.CREATE_AD.value),
            InlineKeyboardButton("Оголошення", callback_data=Action.VIEW_AD.value),
            InlineKeyboardButton("Акаунт", callback_data=Action.VIEW_ACCOUNT.value),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.editMessageText(chat_id=chat_id,
                                message_id=u.msg_id,
                                text=text,
                                reply_markup=reply_markup)


def msg_handler(update, context):
    user = update.message.from_user
    user_id = user['id']
    u: User = users[user_id]
    action = u.current_action
    chat_id = update.message.chat_id

    if action == Action.LOGIN_ENTERING:
        username = update.message.text
        u.cache['username'] = username
        context.bot.delete_message(chat_id=chat_id,
                                   message_id=update.message.message_id)
        context.bot.editMessageText(chat_id=chat_id,
                                    message_id=u.msg_id,
                                    text="Я отримав твій логін. Чекаю на пароль")
        u.current_action = Action.PASSWORD_ENTERING
        return

    if action == Action.PASSWORD_ENTERING:
        password = update.message.text
        context.bot.delete_message(chat_id=chat_id,
                                   message_id=update.message.message_id)
        u.cache['password'] = password

        try:
            api: PetHome = PetHomeImpl(
                u.cache['username'],
                u.cache['password'],
                PET_HOME_ADDR,
                PET_HOME_PORT
            )
        except Exception:
            u.current_action = Action.LOGIN_ENTERING
            context.bot.editMessageText(chat_id=chat_id,
                                        message_id=u.msg_id,
                                        text="Неправильний логін або пароль")
            return

        del u.cache['username']
        del u.cache['password']

        u.api = api
        u.current_action = Action.MAIN

        keyboard = [
            [
                InlineKeyboardButton("Створити", callback_data=Action.CREATE_AD.value),
                InlineKeyboardButton("Оголошення", callback_data=Action.VIEW_AD.value),
                InlineKeyboardButton("Акаунт", callback_data=Action.VIEW_ACCOUNT.value),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.editMessageText(chat_id=chat_id,
                                    message_id=u.msg_id,
                                    text="Головна",
                                    reply_markup=reply_markup)
        return

    if action == Action.CREATE_AD:
        '''
Джеррі
Сіре вушко, чорний носик
3
знайшов
Київ, Солом'янський, Берегівська
13.05.2021
        '''
        text = 'Оголошення успішно створено!'
        try:
            ad_data: str = update.message.text
            lines = ad_data.split('\n')
            pet_name = lines[0].strip()
            signs = [x.strip() for x in lines[1].split(',')]
            age = int(lines[2])
            ad_type = AdType.get_by(lines[3]).name
            split_location = lines[4].split(',')
            location = {
                "city": split_location[0].strip(),
                "district": split_location[1].strip(),
                "street": split_location[2].strip()
            }
            d_data = lines[5].split('.')
            d = {
                'day': int(d_data[0]),
                'month': int(d_data[1]),
                'year': int(d_data[2])
            }
            req_body = {
                "pet-name": pet_name,
                "signs": signs,
                "age": age,
                "type": ad_type,
                "location": location,
                "date": d
            }
            u.api.create_ad(req_body)
        except Exception:
            text = "Сталася помилка. Оголошення не створено"

        context.bot.delete_message(chat_id=chat_id,
                                   message_id=update.message.message_id)
        u.current_action = Action.MAIN
        _display_main_page(context, user_id, chat_id, text)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    keyboard = [
        [
            InlineKeyboardButton("Реєстрація", callback_data=Action.REGISTRATION.value),
            InlineKeyboardButton("Авторизація", callback_data=Action.AUTHORIZATION.value),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.message.chat_id
    msg = context.bot.send_message(chat_id, 'Привіт! Обери дію', reply_markup=reply_markup)

    main_id = msg.message_id
    u = User(main_id)
    user_id = update.message.from_user['id']
    users[user_id] = u


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def authorization(update, context):
    query = update.callback_query
    query.answer()

    if Action.AUTHORIZATION.value == query.data:
        user_id = query.from_user['id']
        u: User = users[user_id]
        u.current_action = Action.LOGIN_ENTERING
        chat_id = query.message.chat.id
        context.bot.editMessageText(chat_id=chat_id,
                                    message_id=u.msg_id,
                                    text="Пришліть логін")


def main_page(update, context):
    query = update.callback_query
    query.answer()

    if Action.MAIN.value == query.data:
        user_id = update.callback_query.from_user['id']
        chat_id = update.callback_query.message.chat.id
        _display_main_page(context, user_id, chat_id)


def view_ad(update, context):
    query = update.callback_query
    query.answer()

    if Action.VIEW_AD.value == query.data:
        user_id = query.from_user['id']
        u: User = users[user_id]
        chat_id = query.message.chat.id
        keyboard = [
            [
                InlineKeyboardButton("Свої", callback_data=Action.GET_LIST_OF_CREATED_ADVERTISEMENTS.value),
                InlineKeyboardButton("Інші", callback_data=Action.GET_LIST_OF_ADVERTISEMENTS.value),
            ],
            [
                _main
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.editMessageText(chat_id=chat_id,
                                    message_id=u.msg_id,
                                    text="Чиї оголошення хочете подивитись?",
                                    reply_markup=reply_markup)


def _display_ad(update, context):
    user_id = update.callback_query.from_user['id']
    u: User = users[user_id]
    chat_id = update.callback_query.message.chat.id

    if u.cache.get('paged', None) is None:
        u.cache['paged'] = {
            'page': 1,
            'current_ad': 0,
            'ads': u.api.get_own_advertisements(1)
        }
    keyboard = [
        [
            InlineKeyboardButton("<", callback_data='prev_ad'),
            InlineKeyboardButton("Редагувати", callback_data='null'),
            InlineKeyboardButton(">", callback_data='next_ad'),
        ],
        [
            InlineKeyboardButton("Видалити", callback_data='delete_ad'),
        ],
        [
            _main
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    paged = u.cache['paged']
    ads = paged['ads']
    if len(ads) == 0:
        msg_txt = "Пробач,я нічого не знайшов :("
    else:
        i = paged['current_ad']
        ad = ads[i]
        msg_txt = f'''
    Pet name: {ad['pet-name']}
    Signs: {ad['signs']}
    Age: {ad['age']}
    Location: {ad['location']['city']}, {ad['location']['district']}, {ad['location']['street']}
    Date: {ad['date']['day']}.{ad['date']['month']}.{ad['date']['year']}
    '''

    context.bot.editMessageText(chat_id=chat_id,
                                message_id=u.msg_id,
                                text=msg_txt,
                                reply_markup=reply_markup)


def view_created_ads(update, context):
    query = update.callback_query
    query.answer()

    if Action.GET_LIST_OF_CREATED_ADVERTISEMENTS.value == query.data:
        _display_ad(update, context)


def iterate_on_ads(update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user['id']
    u: User = users[user_id]

    if 'next_ad' == query.data:
        paged = u.cache['paged']
        ads = paged['ads']
        i = paged['current_ad']

        if i + 1 < len(ads):
            u.cache['paged']['current_ad'] = i + 1
        else:
            next_page = paged['page'] + 1
            next_ads = u.api.get_own_advertisements(next_page)

            if len(next_ads) != 0:
                u.cache['paged'] = {
                    'page': next_page,
                    'current_ad': 0,
                    'ads': next_ads
                }
        _display_ad(update, context)
        return

    if 'prev_ad' == query.data:
        paged = u.cache['paged']
        i = paged['current_ad']

        if i - 1 >= 0:
            u.cache['paged']['current_ad'] = i - 1
        else:
            if paged['page'] > 1:
                prev_page = paged['page'] - 1
                prev_ads = u.api.get_own_advertisements(prev_page)

                if prev_page >= 0:
                    u.cache['paged'] = {
                        'page': prev_page,
                        'current_ad': 0,
                        'ads': prev_ads
                    }
        _display_ad(update, context)
        return


def delete_ad(update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user['id']
    u: User = users[user_id]

    if 'delete_ad' == query.data:
        paged = u.cache['paged']
        ads = paged['ads']
        i = paged['current_ad']
        ad = ads[i]
        ad_id = ad['id']

        u.api.delete_ad(ad_id)
        u.cache['paged'] = {
            'page': 1,
            'current_ad': 0,
            'ads': u.api.get_own_advertisements(1)
        }

        _display_ad(update, context)


def create_ad(update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user['id']
    u: User = users[user_id]

    if Action.CREATE_AD.value == query.data:
        u.current_action = Action.CREATE_AD
        chat_id = query.message.chat.id
        text = '''
Надішліть необхідну інформацію згідно шаблону:
<Ім'я тварини>
<Ознаки тварини> (ознаки через кому)
<Приблизний вік> (тільки цілі числа)
<Тип оголошення> (знайшов, загубив, спостерігаю)
<Місце> (місто, район, вулиця)
<Дата> (день.місяць.рік)
Приклад:
Джеррі
Сіре вушко, чорний носик
3
знайшов
Київ, Солом'янський, Берегівська
13.05.2021
'''
        keyboard = [
            [
                _main
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.editMessageText(chat_id=chat_id,
                                    message_id=u.msg_id,
                                    text=text,
                                    reply_markup=reply_markup)


def call_query_handler(update, context):
    for f in [authorization, view_ad, view_created_ads, iterate_on_ads, delete_ad, main_page, create_ad]:
        f(update, context)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(PET_HOME_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    # dp.add_handler(MessageHandler(Filters.text & (~Filters.command), echo))
    dp.add_handler(CallbackQueryHandler(call_query_handler))
    # dp.add_handler(CallbackQueryHandler(authorization))
    # dp.add_handler(CallbackQueryHandler(view_ad))
    # dp.add_handler(CallbackQueryHandler(view_created_ads))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, msg_handler))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
