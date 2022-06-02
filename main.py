#!/usr/bin python3
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

import logging
import os
from enum import Enum, auto

import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

PET_HOME_TOKEN = os.environ['PET_HOME_TOKEN']
PET_HOME_ADDR = os.environ['PET_HOME_ADDR']
PET_HOME_PORT = os.environ['PET_HOME_PORT']


class Action(Enum):
    LOGIN_ENTERING = auto()
    PASSWORD_ENTERING = auto()
    MAIN = auto()

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
        payload = {
            "username": users[user['id']]['cache']['username'],
            "password": users[user['id']]['cache']['password']
        }
        req = requests.post(f"http://{PET_HOME_ADDR}:{PET_HOME_PORT}/v1/users/auth", json=payload)
        resp = req.json()
        # context.bot.send_message(chat_id, f"Your token is {resp['token']}")
        update.message.reply_text(f"Your token is {resp['token']}")
        users[user['id']]['action'] = Action.MAIN
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
