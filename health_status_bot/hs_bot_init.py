import os
import telebot
from dotenv import load_dotenv
from hs_bot_actions import *

load_dotenv()

bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))
register_handlers(bot)

if __name__ == "__main__":
    print("bot_running.")
    bot.polling(none_stop=True, interval=0)
