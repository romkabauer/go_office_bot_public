# %%
# import nest_asyncio
# nest_asyncio.apply()

import logging
import datetime
import boto3

import aiohttp
import aioschedule

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from asyncio import AbstractEventLoop
import asyncio

from os import environ
from pool_settings import pool_question, pool_options

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

output = './chats_to_handle.txt'

async def update_s3_storage_file(content):
    client = boto3.client(
        's3',
        aws_access_key_id = environ["AWS_ACCESS_KEY"],
        aws_secret_access_key = environ["AWS_SECRET_KEY"],
        region_name = 'eu-west-2'
    )
    client.put_object(
        Bucket = 'goofficebot',
        Key = 'chats_to_handle.txt',
        Body = content
    )

@dp.message_handler(commands='set_time')
async def start_command(message: types.Message):
    is_changed = False
    with open(output, 'r') as chats:
        if all(str(message.chat.id) not in x for x in chats.readlines()):
            is_changed = True
    if is_changed:
        with open(output, 'a+') as chats:
            chats.write(str(message.chat.id) + '\n')
        with open(output, 'r') as chats:
            await update_s3_storage_file(chats.read())
        logger.debug(f"{datetime.datetime.now()}: " + \
                    f"Chat with ID: {message.chat.id}" + \
                    f" was added to the list.")
    await message.reply("Буду постить опрос в 18:00 по рабочим дням.")

async def create_pool():
    if datetime.date.today().weekday() != 4 \
       or datetime.date.today().weekday() != 5:
        logger.debug("Posting pool!")
        with open('./chats_to_handle.txt', 'r') as chats_file:
            for chat in chats_file.readlines():
                await bot.send_poll(chat_id=int(chat), \
                                    question=pool_question, \
                                    options=pool_options, \
                                    is_anonymous=False, \
                                    allows_multiple_answers=False)
    else:
        logger.debug("Go get some rest! Weekend is here!")

async def scheduler():
    # aioschedule.every().minute.do(create_pool)
    aioschedule.every().day \
                       .at("11:38") \
                       .do(create_pool)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

async def load_store_from_s3(output):
    client = boto3.client(
        's3',
        aws_access_key_id = environ["AWS_ACCESS_KEY"],
        aws_secret_access_key = environ["AWS_SECRET_KEY"],
        region_name = 'eu-west-2'
    )
    obj = client.get_object(
        Bucket = 'goofficebot',
        Key = 'chats_to_handle.txt'
    )
    storage_data = obj['Body'].read().decode('utf-8')
    with open(output, "w") as f:
        f.write(storage_data)
    

async def on_startup(_):
    asyncio.create_task(load_store_from_s3(output))
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
