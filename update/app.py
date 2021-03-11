import asyncio
import aiomysql
import json
import os
import time

from datetime import datetime, timedelta
from warnings import filterwarnings

import common

filterwarnings('ignore', category=aiomysql.Warning)

async def main():
    while True:
        pending = set()
        count = 1
        for symbol in await symbols():
            if len(pending) >= 64:
                try:
                    done, pending = await asyncio.wait(pending,
                        return_when=asyncio.FIRST_COMPLETED, timeout=300)
                except asyncio.TimeoutError as exception:
                    print(exception)
            pending.add(asyncio.create_task(update(symbol)))
            print('symbol', count)
            count += 1
        try:
            await asyncio.wait(pending, timeout=3600)
        except asyncio.TimeoutError as exception:
            print(exception)

        now = datetime.utcnow()
        if now.hour > 4 + 5 + 12:
            then = now + timedelta(days=1)
        else:
            then = now
        then.replace(hour=21, minute=5)
        delta = (then - now).total_seconds()
        print('sleeping for', delta, 'seconds')
        await asyncio.sleep(delta)

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

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
