from ..base import pf_global as gl


def order_api(target: str, price: str, num: int, strategy: str, source: str):

    if num == 0:
        return

    side = '1' if num > 0 else '2'

    if price == 'HIT':
        Price = 'ASK+0' if side == '1' else 'BID+0'
    elif price == 'MID':
        Price = 'MID+0'
    else:
        return

    if source == 'hedge':
        tif = '2'
    elif source == 'build':
        tif = '1'
    else:
        return

    g_TradeZMQ = gl.get_value('g_TradeZMQ')
    g_TradeSession = gl.get_value('g_TradeSession')
    account = gl.get_value('account')

    account_used = None
    if not account['sim'] == None:
        account_used = account['sim']
    elif target[:10] in ['TC.F.CFFEX', 'TC.O.CFFEX']:
        account_used = account['index']
    elif target[:8] == 'TC.O.SSE' or targer[:9] == 'TC.O.SZSE':
        account_used = account['stock']

    if account_used == None:
        return

    Param = {

    'BrokerID':account_used['BrokerID'],
    'Account':account_used['Account'],
    'Symbol':target,
    'Side':side,
    'Price':Price,
    'TimeInForce':tif,# 'ROD Day order' | 'IOC | FAK'
    'OrderType':'2',
    'OrderQty':str(abs(num)),
    'PositionEffect':'4',
    'UserKey1': strategy,
    'UserKey2': source,

    }
    g_TradeZMQ.new_order(g_TradeSession,Param)


def order_cancel(reportID: str):

    g_TradeZMQ = gl.get_value('g_TradeZMQ')
    g_TradeSession = gl.get_value('g_TradeSession')

    canorders_obj = {"ReportID":reportID,}
    g_TradeZMQ.cancel_order(g_TradeSession,canorders_obj)