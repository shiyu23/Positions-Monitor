from tcoreapi_mq import *
import calendar
import time

from .pf_enum import *
from . import pf_data


def _init():

    global global_var

    tmq = {'g_TradeZMQ': tcore_zmq(), 'g_QuoteZMQ': tcore_zmq(), 'g_TradeSession': None, 'g_QuoteSession': None, 't_data': None, 'q_data': None, 'exit_signal': 0}

    # 封装 cd C:\Users\pengs\Desktop\profit
    # 封装 pyinstaller -F main.py -w -i ./pictures/logo.ico

    t_data = tmq['g_TradeZMQ'].trade_connect("51848") # 公版
    q_data = tmq['g_QuoteZMQ'].quote_connect("51878")

    #t_data = tmq['g_TradeZMQ'].trade_connect("51492") # 方正2
    #q_data = tmq['g_QuoteZMQ'].quote_connect("51522")

    if q_data["Success"] != "OK":
        print("[quote]connection failed")
        return

    if t_data["Success"] != "OK":
        print("[trade]connection failed")
        return

    tmq['g_TradeSession'] = t_data["SessionKey"]
    tmq['g_QuoteSession'] = q_data["SessionKey"]
    tmq['t_data'] = t_data
    tmq['q_data'] = q_data


    holiday = (calendar.datetime.date(2020, 1, 1),
                          calendar.datetime.date(2020, 1, 24),
                          calendar.datetime.date(2020, 1, 27),
                          calendar.datetime.date(2020, 1, 28),
                          calendar.datetime.date(2020, 1, 29),
                          calendar.datetime.date(2020, 1, 30),
                          calendar.datetime.date(2020, 4, 6),
                          calendar.datetime.date(2020, 5, 1),
                          calendar.datetime.date(2020, 5, 4),
                          calendar.datetime.date(2020, 5, 5),
                          calendar.datetime.date(2020, 6, 25),
                          calendar.datetime.date(2020, 6, 26),
                          calendar.datetime.date(2020, 10, 1),
                          calendar.datetime.date(2020, 10, 2),
                          calendar.datetime.date(2020, 10, 5),
                          calendar.datetime.date(2020, 10, 6),
                          calendar.datetime.date(2020, 10, 7),
                          calendar.datetime.date(2020, 10, 8),

                          calendar.datetime.date(2021, 1, 1),
                          calendar.datetime.date(2021, 2, 11),
                          calendar.datetime.date(2021, 2, 12),
                          calendar.datetime.date(2021, 2, 15),
                          calendar.datetime.date(2021, 2, 16),
                          calendar.datetime.date(2021, 2, 17),
                          calendar.datetime.date(2021, 4, 5),
                          calendar.datetime.date(2021, 5, 3),
                          calendar.datetime.date(2021, 6, 14),
                          calendar.datetime.date(2021, 9, 20),
                          calendar.datetime.date(2021, 9, 21),
                          calendar.datetime.date(2021, 10, 1),
                          calendar.datetime.date(2021, 10, 4),
                          calendar.datetime.date(2021, 10, 5),
                          calendar.datetime.date(2021, 10, 6),
                          calendar.datetime.date(2021, 10, 7),
        ) # 2020 + 2021

    str_to_type: dict = {}
    type_to_str: dict = {}
    for sty in [('etf50', StockType.etf50), ('h300', StockType.h300), ('gz300', StockType.gz300), ('s300', StockType.s300)]:
        str_to_type[sty[0]] = sty[1]
        type_to_str[sty[1]] = sty[0]
    for fty in [('IF', FutureType.IF), ('IH', FutureType.IH)]:
        str_to_type[fty[0]] = fty[1]
        type_to_str[fty[1]] = fty[0]
    for mat in [('M1', Maturity.M1), ('M2', Maturity.M2), ('M3', Maturity.M3), ('Q1', Maturity.Q1), ('Q2', Maturity.Q2), ('Q3', Maturity.Q3)]:
        str_to_type[mat[0]] = mat[1]
        type_to_str[mat[1]] = mat[0]

    Mat = {'calendar': {}, 'contract_format': {}}
    for format in ['calendar', 'contract_format']:
        for ty in [StockType.gz300, StockType.etf50, StockType.h300, StockType.s300, FutureType.IF, FutureType.IH]:
            Mat[format][ty] = []

    global_var = {'holiday': holiday, 'str_to_type': str_to_type, 'type_to_str': type_to_str, 'Mat': Mat, 'localtime': time.localtime(), 'trade_period': False, 'QuoteID': [], 'data_opt': {}, 'hg_data': {}, 'hg_order': {'order': {}, 'Ft': {}, 'Opt': {}}, 'hg_index': {}}
    global_var.update(tmq)
    sub_all_options() # get Mat, QuoteID, data_opt


def sub_all_options():

    Mat = global_var['Mat']
    QuoteID = global_var['QuoteID']
    data_opt = global_var['data_opt']


    data = global_var['g_QuoteZMQ'].QueryAllInstrumentInfo(global_var['g_QuoteSession'], "Options")
    for i in range(len(data['Instruments']["Node"])):
        if data['Instruments']["Node"][i]['ENG'] == 'SSE(O)':
            for mat_classification in data['Instruments']["Node"][i]["Node"][0]["Node"][-4 : ]:
                for z in range(2):
                    QuoteID += mat_classification["Node"][z]['Contracts'] # etf50; z =1 for call; z=2 for put
                    Mat['calendar'][StockType.etf50] += [calendar.datetime.date(int(x[0:4]), int(x[4:6]), int(x[-2:])) for x in mat_classification["Node"][z]['ExpirationDate']]
                    Mat['contract_format'][StockType.etf50] += [x[2:6] for x in mat_classification["Node"][z]['ExpirationDate']]
            for mat_classification in data['Instruments']["Node"][i]["Node"][1]["Node"][-4 : ]:
                for z in range(2):
                    QuoteID += mat_classification["Node"][z]['Contracts'] # h300
                    Mat['calendar'][StockType.h300] += [calendar.datetime.date(int(x[0:4]), int(x[4:6]), int(x[-2:])) for x in mat_classification["Node"][z]['ExpirationDate']]
                    Mat['contract_format'][StockType.h300] += [x[2:6] for x in mat_classification["Node"][z]['ExpirationDate']]
        if data['Instruments']["Node"][i]['ENG'] == 'SZSE(O)':
            for mat_classification in data['Instruments']["Node"][i]["Node"][0]["Node"][-4 : ]:
                for z in range(2):
                    QuoteID += mat_classification["Node"][z]['Contracts'] # s300
                    Mat['calendar'][StockType.s300] += [calendar.datetime.date(int(x[0:4]), int(x[4:6]), int(x[-2:])) for x in mat_classification["Node"][z]['ExpirationDate']]
                    Mat['contract_format'][StockType.s300] += [x[2:6] for x in mat_classification["Node"][z]['ExpirationDate']]
        if data['Instruments']["Node"][i]['ENG'] == 'CFFEX(O)':
            for mat_classification in data['Instruments']["Node"][i]["Node"][0]["Node"][-6 : ]:
                for z in range(2):
                    QuoteID += mat_classification["Node"][z]['Contracts'] # gz300
                    Mat['calendar'][StockType.gz300] += [calendar.datetime.date(int(x[0:4]), int(x[4:6]), int(x[-2:])) for x in mat_classification["Node"][z]['ExpirationDate']]
                    Mat['contract_format'][StockType.gz300] += [x[2:6] for x in mat_classification["Node"][z]['ExpirationDate']]


    data = global_var['g_QuoteZMQ'].QueryAllInstrumentInfo(global_var['g_QuoteSession'], "Future")
    for i in range(len(data['Instruments']["Node"])):
        if data['Instruments']["Node"][i]['ENG'] == 'CFFEX':
            QuoteID += data['Instruments']["Node"][i]["Node"][2]['Contracts'][1:]
            QuoteID += data['Instruments']["Node"][i]["Node"][3]['Contracts'][1:]
            Mat['calendar'][FutureType.IF] += [calendar.datetime.date(int(x[0:4]), int(x[4:6]), int(x[-2:])) for x in data['Instruments']["Node"][i]["Node"][2]['ExpirationDate'][1:]]
            Mat['contract_format'][FutureType.IF] += [x[2:6] for x in data['Instruments']["Node"][i]["Node"][2]['ExpirationDate'][1:]]
            Mat['calendar'][FutureType.IH] += [calendar.datetime.date(int(x[0:4]), int(x[4:6]), int(x[-2:])) for x in data['Instruments']["Node"][i]["Node"][3]['ExpirationDate'][1:]]
            Mat['contract_format'][FutureType.IH] += [x[2:6] for x in data['Instruments']["Node"][i]["Node"][3]['ExpirationDate'][1:]]


    for sty in [StockType.etf50, StockType.h300, StockType.gz300, StockType.s300, FutureType.IF, FutureType.IH]:
        for format in ['calendar', 'contract_format']:
            Mat[format][sty] = sorted(set(Mat[format][sty]))
            copy = Mat[format][sty].copy()
            Mat[format][sty] = {}
            if sty == StockType.gz300:
                for i, mat in enumerate([Maturity.M1, Maturity.M2, Maturity.M3, Maturity.Q1, Maturity.Q2, Maturity.Q3]):
                    Mat[format][sty][mat] = copy[i]
            elif sty in [StockType.etf50, StockType.h300, StockType.s300, FutureType.IF, FutureType.IH]:
                for i, mat in enumerate([Maturity.M1, Maturity.M2, Maturity.Q1, Maturity.Q2]):
                    Mat[format][sty][mat] = copy[i]

    # 删除adj合约
    delect_index_list = []
    for posi, i in enumerate(QuoteID):
        if 'TC.F' in i:
            continue
        k = float(i[last_C_P(i):])
        if 'CFFEX' in i:
            if len([0  for j in [Maturity.M1, Maturity.M2, Maturity.M3] if int(i[14 : 18]) == Mat['calendar'][StockType.gz300][j].year and  int(i[18 : 20]) == Mat['calendar'][StockType.gz300][j].month]) > 0:
                if not ((k <= 2500 and k % 25 == 0) or (k > 2500 and k <= 5000 and k % 50 == 0) or (k > 5000 and k <= 10000 and k % 100 == 0) or (k > 10000 and k % 200 == 0)):
                    delect_index_list.append(posi)
            else:
                if not ((k <= 2500 and k % 50 == 0) or (k > 2500 and k <= 5000 and k % 100 == 0) or (k > 5000 and k <= 10000 and k % 200 == 0) or (k > 10000 and k % 400 == 0)):
                    delect_index_list.append(posi)
        else:
            k *= 1000
            if not ((k <= 3000 and k % 50 == 0) or (k > 3000 and k <= 5000 and k % 100 == 0) or (k > 5000 and k <= 10000 and k % 250 == 0) or (k > 10000 and k <= 20000 and k % 500 == 0) or (k > 20000 and k <= 50000 and k % 1000 == 0) or (k > 50000 and k <= 100000 and k % 2500 == 0) or (k > 100000 and k % 5000 == 0)):
                delect_index_list.append(posi)

    #for i in sorted(delect_index_list, reverse = True):
        #QuoteID.pop(i)

    for sty in [StockType.etf50, StockType.h300, StockType.s300, StockType.gz300]:
        data_opt[sty] = pf_data.OptData(sty)
        data_opt[sty].subscribe_init(Maturity.M1)
        data_opt[sty].subscribe_init(Maturity.M2)
        data_opt[sty].subscribe_init(Maturity.Q1)
        data_opt[sty].subscribe_init(Maturity.Q2)
        if sty == StockType.gz300:
            data_opt[sty].subscribe_init(Maturity.M3)
            data_opt[sty].subscribe_init(Maturity.Q3)
    for fty in [FutureType.IF, FutureType.IH]:
        data_opt[fty] = pf_data.FutureData(fty)

    quote_obj = {"Symbol":"ok", "SubDataType":"REALTIME"}
    for i in QuoteID:
        quote_obj["Symbol"] = i
        global_var['g_QuoteZMQ'].subquote(global_var['g_QuoteSession'],quote_obj)


def last_C_P(string: str):

    num = len(string) - 1
    while (string[num] != 'C' and string[num] != 'P'):
        num -= 1
    return num + 2


def name_to_data(yc_master_contract: str):

    data_opt = global_var['data_opt']

    if 'TC.O.SSE.510050' in yc_master_contract:
        sty = StockType.etf50
        if yc_master_contract[15] == 'A':
            mat = data_opt[sty]._2005_to_Mat[yc_master_contract[19 : 23]]
        else:
            mat = data_opt[sty]._2005_to_Mat[yc_master_contract[18 : 22]]
    elif 'TC.O.SSE.510300' in yc_master_contract:
        sty = StockType.h300
        if yc_master_contract[15] == 'A':
            mat = data_opt[sty]._2005_to_Mat[yc_master_contract[19 : 23]]
        else:
            mat = data_opt[sty]._2005_to_Mat[yc_master_contract[18 : 22]]
    elif 'TC.O.SZSE.159919' in yc_master_contract:
        sty = StockType.s300
        if yc_master_contract[16] == 'A':
            mat = data_opt[sty]._2005_to_Mat[yc_master_contract[20 : 24]]
        else:
            mat = data_opt[sty]._2005_to_Mat[yc_master_contract[19 : 23]]
    elif 'TC.O.CFFEX.IO' in yc_master_contract:
        sty = StockType.gz300
        mat = data_opt[sty]._2005_to_Mat[yc_master_contract[16 : 20]]

    position = data_opt[sty].k_list[mat].index(float(yc_master_contract[last_C_P(yc_master_contract) : ]))
    if '.C.' in yc_master_contract:
        se = 0
    elif '.P.' in yc_master_contract:
        se = 1

    return data_opt[sty].OptionList[mat][position][se]


def get_value(key):
    return global_var[key]


def set_value(key, value):
    global_var[key] = value