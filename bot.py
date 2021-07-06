# %%
# import nest_asyncio
# nest_asyncio.apply()

import logging
import datetime
from datetime import timedelta
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

chat_id_storage_path = 'chats_to_handle_test.txt'

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

@dp.message_handler(commands='set_time')
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
    await message.reply("Буду постить опрос в 18:00 по рабочим дням.")

async def create_pool():
    if datetime.date.today().weekday() != 4 \
       or datetime.date.today().weekday() != 5:
        logger.debug("Posting pool!")
        with open(chat_id_storage_path, 'r') as chats_file:
            for chat in chats_file.readlines():
                await bot.send_poll(chat_id=int(chat), \
                                    question = datetime.date.today() + 
                                               timedelta(days=1) \
                                               .strftime("%A, %d %B") \
                                               + '🏢🚶‍♂️?', \
                                    options=pool_options, \
                                    is_anonymous=False, \
                                    allows_multiple_answers=False, \
                                    disable_notification=True)
    else:
        logger.debug("Go get some rest! Weekend is here!")

async def scheduler():
    # aioschedule.every().minute.do(create_pool)
    aioschedule.every().day \
                       .at("15:32") \
                       .do(create_pool)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

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
