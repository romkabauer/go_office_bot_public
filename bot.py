# %%
# import nest_asyncio
# nest_asyncio.apply()

import logging
import datetime
from datetime import timedelta
from typing import Text
import boto3

import aiohttp
import aioschedule

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from asyncio import AbstractEventLoop
import asyncio

from os import environ
from pool_settings import pool_options

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

loop: AbstractEventLoop = asyncio.new_event_loop()
asyncio.set_event_loop(loop=loop)

# Bot initialization
bot = Bot(token=environ['BOT_TOKEN'], loop=loop)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

session: aiohttp.ClientSession = aiohttp.ClientSession()

chat_id_storage_path = 'chats_to_handle.txt'

async def update_s3_storage_file(content):
    client = boto3.client(
        's3',
        aws_access_key_id = environ["AWS_ACCESS_KEY"],
        aws_secret_access_key = environ["AWS_SECRET_KEY"],
        region_name = 'eu-west-2'
    )
    client.put_object(
        Bucket = 'goofficebot',
        Key = chat_id_storage_path,
        Body = content
    )

@dp.message_handler(commands='settime')
async def start_command(message: types.Message):
    is_changed = False
    with open(chat_id_storage_path, 'r') as chats:
        if all(str(message.chat.id) not in x for x in chats.readlines()):
            is_changed = True
    if is_changed:
        with open(chat_id_storage_path, 'a+') as chats:
            chats.write(str(message.chat.id) + '\n')
        with open(chat_id_storage_path, 'r') as chats:
            await update_s3_storage_file(chats.read())
        logger.debug(f"{datetime.datetime.now()}: " + \
                    f"Chat with ID: {message.chat.id}" + \
                    f" was added to the list.")
    await message.reply("Буду постить опрос в 21:00 с вс по чт.")

@dp.message_handler(commands='stop')
async def start_command(message: types.Message):
    is_changed = False
    with open(chat_id_storage_path, 'r') as chats:
        if any(str(message.chat.id) in x for x in chats.readlines()):
            is_changed = True
    logger.debug(str(is_changed))
    if is_changed:
        chats_list = []
        with open(chat_id_storage_path, 'r') as chats:
            chats_list = chats.readlines()
            logger.debug("Debug: " + str(chats_list))
        try:
            logger.debug(chats_list)
            chats_list.remove(str(message.chat.id) + "\n")
            with open(chat_id_storage_path, 'w') as chats:
                for chat_id in chats_list:
                    chats.write(chat_id + '\n')
            with open(chat_id_storage_path, 'r') as chats:
                await update_s3_storage_file(chats.read())
                logger.debug(f"{datetime.datetime.now()}: " + \
                            f"Chat with ID: {message.chat.id}" + \
                            f" was removed from the list.")
            await message.reply("Больше постить опросы не буду. Чтобы возобновить, вызови /settime.",
                                reply=False)
        except ValueError:
            await message.reply("Чтобы начать постить опрос, вызови /settime.",
                            reply=False)
    else:
        await message.reply("Чтобы начать постить опрос, вызови /settime!",
                            reply=False)

@dp.message_handler(commands='zubeki')
async def zubeki_command(message: types.Message):
    await message.reply(f"*{message.from_user.full_name} приглашает съездить на обед к Зубекам!*" + \
                            f"\n\n*Что:* Вкусная узбекская кухня (лагман, самса, плов, манты)" + \
                            f"\n*Где:* Нарвский проспект, 18" + \
                            f"\n*Оплата только наличными*",
                        reply=False,
                        parse_mode='Markdown')

async def create_pool():
    if not (datetime.date.today().weekday() == 4 \
       or datetime.date.today().weekday() == 5):
        logger.debug("Posting pool!")
        with open(chat_id_storage_path, 'r') as chats_file:
            for chat in chats_file.readlines():
                try:
                    await bot.send_poll(chat_id=int(chat.strip()), \
                                    question = (datetime.date.today() + 
                                               timedelta(days=1)) \
                                               .strftime("%A, %d %B") \
                                               + ' 🏢🚶‍♂️?', \
                                    options=pool_options, \
                                    is_anonymous=False, \
                                    allows_multiple_answers=False, \
                                    disable_notification=True)
                except Exception as e:
                    logger.error(e.args)
                    pass
    else:
        logger.debug("Go get some rest! Weekend is here!")

async def scheduler():
    # aioschedule.every().minute.do(create_pool)
    aioschedule.every().day \
                       .at("18:00") \
                       .do(create_pool)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(120)

async def load_storage_from_s3(chat_id_storage_path):
    client = boto3.client(
        's3',
        aws_access_key_id = environ["AWS_ACCESS_KEY"],
        aws_secret_access_key = environ["AWS_SECRET_KEY"],
        region_name = 'eu-west-2'
    )
    obj = client.get_object(
        Bucket = 'goofficebot',
        Key = chat_id_storage_path
    )
    storage_data = obj['Body'].read().decode('utf-8')
    with open(chat_id_storage_path, "w") as f:
        f.write(storage_data)
    

async def on_startup(_):
    asyncio.create_task(load_storage_from_s3(chat_id_storage_path))
    asyncio.create_task(scheduler())

async def shutdown(dp):
    await dp.storage.close()
    await dp.storage.wait_closed()
    await session.close()

if __name__ == '__main__':
    logger.debug(f"Started: {datetime.datetime.now()}")
    executor.start_polling(dp, \
                          loop=loop, \
                          on_shutdown=shutdown, \
                          skip_updates=False, \
                          on_startup=on_startup)
