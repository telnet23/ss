import aiohttp_jinja2
import aiomysql
import jinja2
import asyncio
import json
import os
import random
import re

from aiohttp import web
from datetime import datetime
from warnings import filterwarnings

import common

filterwarnings('ignore', category=aiomysql.Warning)

routes = web.RouteTableDef()

@routes.get('/db')
async def get_db(request):
    pool = request.app['db']
    connection = await pool.acquire()
    cursor = await connection.cursor()

    await cursor.execute('''
            SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = "ss"
        ''')

    for table_name, in await cursor.fetchall():
        #await cursor.execute('ANALYZE TABLE ?', table_name)
        await cursor.execute(f'ANALYZE TABLE {table_name}')

    await cursor.execute('''
            SELECT  TABLE_NAME as table_name,
                    TABLE_ROWS as table_rows,
                    DATA_LENGTH as data_length,
                    CONCAT(update_time, " ", "UTC") as update_time
                FROM information_schema.tables
                WHERE table_schema = "ss"
                ORDER BY data_length DESC
        ''')

    text = ''
    text += '<html>'
    text += '<body>'
    text += '<table border="1">'
    text += '<tr><th>' + '</th><th>'.join(d[0] for d in cursor.description) + '</th></tr>'
    for row in await cursor.fetchall():
        text += '<tr><td>' + '</td><td>'.join(map(str, row)) + '</td></tr>'
    text += '</table>'
    text += '</body>'
    text += '</html>'

    await cursor.close()
    pool.release(connection)

    response = web.Response(text=text, content_type='text/html')
    return response

@routes.get('/')
@routes.get('/{qid}')
@aiohttp_jinja2.template('main.html')
async def get_main(request):
    return {'now': datetime.now()}

@routes.get('/static/main.css')
@routes.get('/static/main.js')
async def get_static(request):
    path = request.path.split('/')[-1]
    response = web.FileResponse(path)
    response.headers['Cache-Control'] = 'no-cache'
    return response

@routes.post('/query')
async def post_query(request):
    def query_id(seed):
        alphabet = []
        alphabet += [chr(k) for k in range(ord('0'), ord('9') + 1)]
        alphabet += [chr(k) for k in range(ord('A'), ord('Z') + 1)]
        alphabet += [chr(k) for k in range(ord('a'), ord('z') + 1)]
        random.seed(json.dumps(seed, sort_keys=True) + 'MyXW7MYGlRBhnJzkgRAq0FReWpZeeWuj')
        return 'q' + ''.join(random.choice(alphabet) for _ in range(11))

    pool = request.app['db']
    connection = await pool.acquire()
    cursor = await connection.cursor()

    query = await request.json()
    qid = query_id(query)
    await cursor.execute('INSERT IGNORE INTO query (id, query) VALUES (%s, %s)', (qid, json.dumps(query)))
    await connection.commit()

    await cursor.close()
    pool.release(connection)

    if type(query) is str:
        symbols = await symbols_explicit(request, query)

    return web.json_response({'id': qid, 'symbols': symbols})

async def symbols_implicit(request, query):
    pool = request.app['safe_db']
    connection = await pool.acquire()
    cursor = await connection.cursor()

    symbols = []

    await cursor.close()
    pool.release(connection)

    return symbols

async def symbols_explicit(request, query):
    pool = request.app['db']
    connection = await pool.acquire()
    cursor = await connection.cursor()

    symbols = []

    for symbol in re.split(r'[\s,]+', re.sub(r'^[\s,]+|[\s,]+$', '', query)):
        symbol = symbol.upper()
        if symbol == '' or symbol in symbols:
            continue

        await cursor.execute('SELECT symbol FROM daily WHERE symbol = %s', symbol)
        if await cursor.fetchone() is None:
            await common.update_symbol(connection, symbol)

        await cursor.execute('SELECT symbol FROM daily WHERE symbol = %s', symbol)
        if await cursor.fetchone() is None:
            continue

        symbols.append(symbol)

    await cursor.close()
    pool.release(connection)

    return symbols

@routes.get('/query/{qid}')
@routes.get('/query/{qid}.js')  # .js so that Cloudflare will cache it
async def get_query(request):
    pool = request.app['db']
    connection = await pool.acquire()
    cursor = await connection.cursor()

    qid = request.match_info.get('qid')
    await cursor.execute('SELECT query FROM query WHERE id = %s', qid)
    row = await cursor.fetchone()

    await cursor.close()
    pool.release(connection)

    if row is None:
        response = web.json_response({}, status=404)
        return response

    query, = row
    response = web.json_response(json.loads(query))
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

@routes.get('/chart/{symbol}')
@routes.get('/chart/{symbol}.js')  # .js so that Cloudflare will cache it
async def get_chart(request):
    pool = request.app['db']
    connection = await pool.acquire()
    cursor = await connection.cursor()

    symbol = request.match_info.get('symbol')
    await cursor.execute('SELECT timestamp, open, high, low, close FROM daily WHERE symbol = %s', symbol)
    rows = await cursor.fetchall()

    await cursor.close()
    pool.release(connection)

    if rows is None:
        response = web.json_response([], status=404)
        return response

    rowsT = list(list(v) for v in zip(*rows))
    response = web.json_response(rowsT)
    # Cloudflare uses max{this max-age, the default in the dashboard}
    # The default in the dashboard is 12 hours
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

async def create_db(app):
    app['db'] = await aiomysql.create_pool(
        db=os.environ['MYSQL_DATABASE'],
        host=os.environ['MYSQL_HOST'],
        user='root',
        password=os.environ['MYSQL_ROOT_PASSWORD'],
        loop=asyncio.get_event_loop()
    )

async def create_safe_db(app):
    app['safe_db'] = await aiomysql.create_pool(
        db=os.environ['MYSQL_DATABASE'],
        host=os.environ['MYSQL_HOST'],
        user=os.environ['MYSQL_USER'],
        password=os.environ['MYSQL_PASSWORD'],
        loop=asyncio.get_event_loop()
    )

routes.static('/static', 'static')
app = web.Application()
app.add_routes(routes)
app.on_startup.append(create_db)
app.on_startup.append(create_safe_db)
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('.'))
web.run_app(app)
