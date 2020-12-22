import aiohttp
import aiohttp_socks

async def update_symbol(connection, symbol):
    cursor = await connection.cursor()

    connector = aiohttp_socks.ProxyConnector.from_url('socks5://tor:9050')
    headers = {
        'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    timeout = aiohttp.ClientTimeout(total=90)

    url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + symbol
    params = {
        'interval': '1d',
        'period1': -2147483647,
        'period2': 2147483647,
        'events': 'div,split',
    }

    await cursor.execute('SELECT MAX(timestamp) FROM daily WHERE symbol = %s', symbol)
    max_timestamp, = await cursor.fetchone()
    if max_timestamp:
        params['period1'] = max_timestamp

    async with aiohttp.ClientSession(connector=connector, headers=headers, timeout=timeout) as session:
        async with session.get(url, params=params) as response:
            data = await response.json()

            try:
                result = data['chart']['result'][0]
                symbol = result['meta']['symbol']
                timestamps = result['timestamp']
                opens = result['indicators']['quote'][0]['open']
                highs = result['indicators']['quote'][0]['high']
                lows = result['indicators']['quote'][0]['low']
                closes = result['indicators']['quote'][0]['close']
            except (IndexError, KeyError, TypeError):
                pass
            else:
                rows = []
                for i in range(len(timestamps)):
                    row = (symbol, timestamps[i], opens[i], highs[i], lows[i], closes[i])
                    print(row)
                    rows.append(row)
                await cursor.executemany('''
                    INSERT IGNORE INTO daily (symbol, timestamp, open, high, low, close)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', rows)
                await connection.commit()

    await cursor.close()
