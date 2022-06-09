#!/usr/bin python3
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

import logging
import os
from enum import Enum

import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from api import PetHome
from api.v1 import PetHomeImpl

PET_HOME_TOKEN = os.environ['PET_HOME_TOKEN']
PET_HOME_ADDR = os.environ['PET_HOME_ADDR']
PET_HOME_PORT = os.environ['PET_HOME_PORT']


class Action(Enum):
    LOGIN_ENTERING = 'login_entering'
    PASSWORD_ENTERING = 'password_entering'
    MAIN = 'main'
    GET_LIST_OF_ADVERTISEMENTS = 'get_list_of_advertisements'
    GET_LIST_OF_CREATED_ADVERTISEMENTS = 'get_list_of_created_advertisements'
    CREATE_AD = 'create_advertisement'
    DEL_AD = 'delete_advertisement'
    WAITING_FOR_AD_INFO = 'waiting_for_add_info'
    WAITING_FOR_AD_ID = 'waiting_for_add_id'


# {12345: {'action': Action.LOGIN_ENTERING, 'cache': dict()}}
users = dict()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def msg_handler(update, context):
    user = update.message.from_user
    action = users[user['id']]['action']

    if action == Action.LOGIN_ENTERING:
        username = update.message.text
        users[user['id']]['cache']['username'] = username
        # context.bot.send_message(chat_id, 'I have got your login. Please, send me your password')
        update.message.reply_text('I have got your login. Please, send me your password')
        users[user['id']]['action'] = Action.PASSWORD_ENTERING
        return

    if action == Action.PASSWORD_ENTERING:
        password = update.message.text
        users[user['id']]['cache']['password'] = password

        try:
            api: PetHome = PetHomeImpl(
                users[user['id']]['cache']['username'],
                users[user['id']]['cache']['password'],
                PET_HOME_ADDR,
                PET_HOME_PORT
            )
        except Exception:
            users[user['id']]['action'] = Action.LOGIN_ENTERING
            update.message.reply_text(f"Authorization is failed. Your login or password is incorrect. Try again.")
            return

        del users[user['id']]['cache']['username']
        del users[user['id']]['cache']['password']

        users[user['id']]['cache']['api'] = api
        users[user['id']]['action'] = Action.MAIN
        update.message.reply_text(f"Send command: {Action.GET_LIST_OF_ADVERTISEMENTS.value}; "
                                  f"{Action.GET_LIST_OF_CREATED_ADVERTISEMENTS.value}; "
                                  f"{Action.CREATE_AD.value}; {Action.DEL_AD.value}")
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
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id, 'Hi! Send your login')
    user = update.message.from_user
    users[user['id']] = {'action': Action.LOGIN_ENTERING, 'cache': dict()}


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


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
