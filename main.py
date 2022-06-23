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


# {12345: {'action': Action.LOGIN_ENTERING, 'cache': dict()}}
users = dict()

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

    if update.message.text == Action.VIEW_AD.value:
        keyboard = [
            [
                InlineKeyboardButton("Свої", callback_data=Action.GET_LIST_OF_CREATED_ADVERTISEMENTS.value),
                InlineKeyboardButton("Інші", callback_data=Action.GET_LIST_OF_ADVERTISEMENTS.value),
            ],
            [
                InlineKeyboardButton("На головну", callback_data=Action.MAIN.value),
                InlineKeyboardButton("Назад", callback_data=Action.BACK.value),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.editMessageText(chat_id=chat_id,
                                    message_id=u.msg_id,
                                    text="Я отримав твій логін. Чекаю на пароль",
                                    reply_markup=reply_markup)
        return

    if update.message.text == Action.GET_LIST_OF_ADVERTISEMENTS.value:
        api: PetHome = users[user['id']]['cache']['api']
        # TODO page is hardcoded
        ads = api.get_other_advertisements(1)
        resp = ""
        for ad in ads:
            info = f"""
Pet name: {ad['pet-name']}
Signs: {ad['signs']}
Age: {ad['age']}
Location: {ad['location']['city']}, {ad['location']['district']}, {ad['location']['street']}
Date: {ad['date']['day']}.{ad['date']['month']}.{ad['date']['year']}

"""
            resp = f"{resp}{info}"
        update.message.reply_text(resp)
        return

    if update.message.text == Action.GET_LIST_OF_CREATED_ADVERTISEMENTS.value:
        api: PetHome = users[user['id']]['cache']['api']
        # TODO page is hardcoded
        ads = api.get_own_advertisements(1)
        resp = ""
        for ad in ads:
            info = f"""
ID: {ad['id']}
Pet name: {ad['pet-name']}
Signs: {ad['signs']}
Age: {ad['age']}
Location: {ad['location']['city']}, {ad['location']['district']}, {ad['location']['street']}
Date: {ad['date']['day']}.{ad['date']['month']}.{ad['date']['year']}

"""
            resp = f"{resp}{info}"
        update.message.reply_text(resp)
        return

    if update.message.text == Action.CREATE_AD.value:
        update.message.reply_text('Send info using JSON format')
        users[user['id']]['action'] = Action.WAITING_FOR_AD_INFO
        return

    if update.message.text == Action.DEL_AD.value:
        update.message.reply_text('Send advertisement ID')
        users[user['id']]['action'] = Action.WAITING_FOR_AD_ID
        return

    if users[user['id']]['action'] == Action.WAITING_FOR_AD_INFO:
        users[user['id']]['action'] = Action.MAIN
        api: PetHome = users[user['id']]['cache']['api']
        # TODO we get in JSON format; we need to do it more easier for users (filling date step by step)
        ad_info = update.message.text
        api.create_ad(ad_info)
        update.message.reply_text('Advertisement has been created')
        return

    if users[user['id']]['action'] == Action.WAITING_FOR_AD_ID:
        users[user['id']]['action'] = Action.MAIN
        api: PetHome = users[user['id']]['cache']['api']
        # TODO we get in JSON format; we need to do it more easier for users (filling date step by step)
        ad_id = update.message.text
        api.delete_ad(ad_id)
        update.message.reply_text('Advertisement has been deleted')
        return


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
        user_id = query.from_user['id']
        u: User = users[user_id]
        u.current_action = Action.LOGIN_ENTERING
        chat_id = query.message.chat.id
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


def view_ad(update, context):
    query = update.callback_query
    query.answer()

    if Action.VIEW_AD.value == query.data:
        user_id = query.from_user['id']
        u: User = users[user_id]
        u.current_action = Action.LOGIN_ENTERING
        chat_id = query.message.chat.id
        keyboard = [
            [
                InlineKeyboardButton("Свої", callback_data=Action.GET_LIST_OF_CREATED_ADVERTISEMENTS.value),
                InlineKeyboardButton("Інші", callback_data=Action.GET_LIST_OF_ADVERTISEMENTS.value),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.editMessageText(chat_id=chat_id,
                                    message_id=u.msg_id,
                                    text="Чиї оголошення хочете подивитись?",
                                    reply_markup=reply_markup)

def _display_ad(update,context):
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
                                text= msg_txt,
                                reply_markup=reply_markup)

def view_created_ads(update, context):
    query = update.callback_query
    query.answer()

    if Action.GET_LIST_OF_CREATED_ADVERTISEMENTS.value == query.data: #or query.data == "next_ad":
       _display_ad(update,context)


def iterate_on_ads(update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user['id']
    u: User = users[user_id]
    u.current_action = Action.LOGIN_ENTERING

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
        _display_ad(update,context)
        return

    if 'prev_ad' == query.data:
        paged = u.cache['paged']
        i = paged['current_ad']

        if i - 1 >= 0:
            u.cache['paged']['current_ad'] = i - 1
        else:
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
    u.current_action = Action.LOGIN_ENTERING

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

        _display_ad(update,context)

def call_query_handler(update, context):
    for f in [authorization, view_ad, view_created_ads, iterate_on_ads, delete_ad]:
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
