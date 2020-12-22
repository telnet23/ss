import asyncio
import aiomysql
import json
import os
import time

from datetime import datetime
from warnings import filterwarnings

import common

filterwarnings('ignore', category=aiomysql.Warning)

async def main():
    pending = set()
    for symbol in await symbols():
        if len(pending) >= 64:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        pending.add(asyncio.create_task(update(symbol)))
    await asyncio.wait(pending)

async def symbols():
    connection = await connect()
    cursor = await connection.cursor()
    await cursor.execute('SELECT DISTINCT symbol FROM daily')
    symbols = {symbol for symbol, in await cursor.fetchall()}
    connection.close()

    with open('us.json') as fp:
        symbols |= {entry['ticker'] for entry in json.load(fp)}

    print(len(symbols), 'symbols')
    return symbols

async def update(symbol):
    connection = await connect()
    await common.update_symbol(connection, symbol)
    connection.close()

async def connect():
    loop = asyncio.get_event_loop()
    return await aiomysql.connect(
        loop=loop,
        host=os.environ['MYSQL_HOST'],
        db=os.environ['MYSQL_DATABASE'],
        user='root',
        password=os.environ['MYSQL_ROOT_PASSWORD']
    )

last = None
while True:
    now = datetime.now()
    if not last or (now.hour > 16 and (now - last).seconds > 43200):
        last = now
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    time.sleep(60)
