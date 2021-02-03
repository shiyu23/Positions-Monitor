import threading
import time

from ..base import pf_global as gl


lock = threading.RLock()

def order_api(target: str, price: str, num: int, strategy: str, source: str):

    lock.acquire()

    if num == 0:
        lock.release()
        return

    side = '1' if num > 0 else '2'

    if price == 'HIT':
        Price = 'ASK+0' if side == '1' else 'BID+0'
    elif price == 'MID':
        Price = 'MID+0'
    else:
        lock.release()
        return

    if target[:10] in ['TC.F.CFFEX', 'TC.O.CFFEX']:
        mkt = 'cffex'
    elif target[:8] == 'TC.O.SSE':
        mkt = 'sse'
    elif target[:9] == 'TC.O.SZSE':
        mkt = 'szse'
    else:
        lock.release()
        return

    ot = '2'
    if source == 'hedge':
        tif = '2'
        if mkt in ['sse', 'szse']:
            ot = '1'
    elif source == 'build':
        tif = '1'
    else:
        lock.release()
        return

    g_TradeZMQ = gl.get_value('g_TradeZMQ')
    g_TradeSession = gl.get_value('g_TradeSession')
    account = gl.get_value('account')

    account_used = None
    if not account['sim'] == None:
        account_used = account['sim']
    elif mkt == 'cffex':
        account_used = account['index']
    elif mkt in ['sse', 'szse']:
        account_used = account['stock']

    if account_used == None:
        lock.release()
        return

    Param = {

    'BrokerID':account_used['BrokerID'],
    'Account':account_used['Account'],
    'Symbol':target,
    'Side':side,
    'Price':Price,
    'TimeInForce':tif,# 1 : ROD Day order | 2 : IOC | FAK | 3 : FOK   Fill or Kill
    'OrderType':ot,# 1 : Market order | 2 : Limit order
    'OrderQty':str(abs(num)),
    'PositionEffect':'4',
    'UserKey1': strategy,
    'UserKey2': source,

    }

    if mkt in ['sse', 'szse']:
        per = 50 if ot == '2' else 10
    elif mkt == 'cffex':
        per = 20

    total_num = abs(num)
    while total_num > 0:
        n = per if total_num >= per else total_num
        Param['OrderQty'] = str(n)
        g_TradeZMQ.new_order(g_TradeSession,Param)
        total_num -= n
        time.sleep(0.2) # 每秒5笔下单限制

    lock.release()


def order_cancel(reportID: str):

    g_TradeZMQ = gl.get_value('g_TradeZMQ')
    g_TradeSession = gl.get_value('g_TradeSession')

    canorders_obj = {"ReportID":reportID,}
    g_TradeZMQ.cancel_order(g_TradeSession,canorders_obj)