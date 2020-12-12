import sys
sys.coinit_flags = 0
import datetime
from tcoreapi_mq import *
import xlrd,xlwt
import time
from tkinter import filedialog, ttk, messagebox, font
from tkinter import *
import random
import os
import threading
import math
from enum import Enum
import time
import calendar
import numpy as np
import copy


global localtime
localtime = time.localtime()

# Maturity
class Maturity(Enum):
    M1 = 1; M2 = 2; M3 = 3; Q1 = 4; Q2 = 5; Q3 = 6

# Stock Type
class StockType(Enum):
    etf50 = 1; h300 = 2; gz300 = 3; s300 = 4

# Future Type
class FutureType(Enum):
    IF = 1; IH = 2

# Option Type
class OptionType(Enum):
    C = 1; P = 2

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

QuoteID = []
Mat = {'calendar': {}, 'contract_format': {}}
for format in ['calendar', 'contract_format']:
    for ty in [StockType.gz300, StockType.etf50, StockType.h300, StockType.s300, FutureType.IF, FutureType.IH]:
        Mat[format][ty] = []

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


def cdf(x: float):

    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    sign = 1
    if x < 0:
        sign = -1
    x = math.fabs(x) / math.sqrt(2.0)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(- x * x)
    return 0.5 * (1.0 + sign * y)

def pdf(x: float):

    pi = 3.141592653589793
    return 1 / (math.sqrt(2 * pi)) * math.exp(- x * x / 2)

def BS(oty: OptionType, K: float, T: float, S: float, sigma: float):

    sigmaSqrtT = sigma * math.sqrt(T)
    d1 = math.log(S / K) / sigmaSqrtT + 0.5 * sigmaSqrtT
    d2 = d1 - sigmaSqrtT
    if oty == OptionType.C:
        return S * cdf(d1) - K * cdf(d2)
    else:
        return K * cdf(-d2) - S * cdf(-d1)

class OptionInfo:

    def __init__(self, sty: StockType, mat: Maturity, oty: OptionType, K: float, P: float, ask: float, bid: float):
        self.sty = sty
        self.mat = mat
        self.oty = oty
        self.K = K
        self.P = P
        self.ask = ask
        self.bid = bid
        self.T: float = 1
        self.S: float = 1
        self.cb: bool = False
        self._iv: float = 0.25
        self.yc_master_contract: str = ''

    def midbidaskspread(self):
        if '' not in [self.ask, self.bid]:
            return (self.ask + self.bid)/2
        else:
            return None

    def iv(self):
        a = 0.0001; b = 3; NTRY = 20; FACTOR = 1.6; S = self.S; T = self.T; K = self.K; P = self.midbidaskspread(); oty = self.oty
        f1 = BS(oty, K, T, S, a) - P; f2 = BS(oty, K, T, S, b) - P
        # rfbisect
        tol = 1e-6
        while (b - a) > tol and NTRY > 0:
            NTRY -= 1
            c = (a + b) / 2.0
            if abs(BS(oty, K, T, S, c) - P) < tol:
                return c
            else:
                if (BS(oty, K, T, S, a) - P) * (BS(oty, K, T, S, c) - P) < 0:
                    b = c
                else:
                    a = c
        return c

    def delta(self):
        iv = self._iv; S = self.S; T = self.T
        if self.oty == OptionType.C:
            return cdf(math.log(S / self.K) / (iv * math.sqrt(T)) + 0.5 * iv * math.sqrt(T))
        else:
            return cdf(math.log(S / self.K) / (iv * math.sqrt(T)) + 0.5 * iv * math.sqrt(T)) - 1

    def gamma(self):
        iv = self._iv; S = self.S; T = self.T
        return pdf(math.log(S / self.K) / (iv * math.sqrt(T)) + 0.5 * iv * math.sqrt(T)) / S / iv / math.sqrt(T)

    def vega(self):
        iv = self._iv; S = self.S; T = self.T
        return S * math.sqrt(T) * pdf(math.log(S / self.K) / (iv * math.sqrt(T)) + 0.5 * iv * math.sqrt(T))

    def theta(self):
        iv = self._iv; S = self.S; T = self.T
        return - S * pdf(math.log(S / self.K) / (iv * math.sqrt(T)) + 0.5 * iv * math.sqrt(T)) * iv / 2 / math.sqrt(T)

class OptData: # one stock type

    def __init__(self, sty: StockType):
        self.sty = sty
        self.Mat_to_2005 = {}
        self._2005_to_Mat = {}
        self.T = {}
        self.initT = {}
        self.S = {}
        self.k0 = {}
        self.posi = {}
        self.OptionList = {}
        if sty == StockType.gz300:
            self.cm = 100
            self.mc = 0.2
            self.p_limit = 20
            self.tick_limit = 15
            self.matlist = [Maturity.M1, Maturity.M2, Maturity.M3, Maturity.Q1, Maturity.Q2, Maturity.Q3]
        elif sty in [StockType.etf50, StockType.h300, StockType.s300]:
            self.cm = 10000
            self.mc = 0.0001
            self.p_limit = 0.01
            self.tick_limit = 10
            self.matlist = [Maturity.M1, Maturity.M2, Maturity.Q1, Maturity.Q2]
        for mat in self.matlist:
            self.S[mat] = ''; self.k0[mat] = ''; self.posi[mat] = ''
        self.k_list = {}
        self.getMat()
        
    def getMat(self):
        for mat in self.matlist:
            self.Mat_to_2005[mat] = Mat['contract_format'][self.sty][mat]
            self._2005_to_Mat[self.Mat_to_2005[mat]] = mat

        def num_weekend(date1: calendar.datetime.date, date2: calendar.datetime.date):
            num = 0
            oneday = calendar.datetime.timedelta(days = 1)
            date = calendar.datetime.date(date1.year, date1.month, date1.day)
            while date != date2:
                if date.weekday() == 5 or date.weekday() == 6 or date in holiday:
                    num += 1
                date += oneday
            return num

        c = calendar.Calendar(firstweekday=calendar.SUNDAY)
        year = localtime.tm_year; month = localtime.tm_mon; mday = localtime.tm_mday
        currentDate = calendar.datetime.date(year, month, mday)

        for mat in self.matlist:
            self.T[mat] = ((Mat['calendar'][self.sty][mat] - currentDate).days - num_weekend(currentDate, Mat['calendar'][self.sty][mat]))/244
            self.initT[mat] = self.T[mat]

    def subscribe_init(self, mat: Maturity):
        # QuoteID and Optionlists      TC.O.SSE.510300.202012.C.5 | TC.O.SSE.510050A.202012.C.3.351
        QuoteID_addin = []
        for id in QuoteID:
            if self.sty == StockType.gz300 and id[11:13] == 'IO' and id[16:20] == self.Mat_to_2005[mat]:
                QuoteID_addin.append(id)
            elif self.sty == StockType.etf50 and id[9:15] == '510050' and self.Mat_to_2005[mat] in [id[18:22], id[19:23]]:
                QuoteID_addin.append(id)
            elif self.sty == StockType.h300 and id[9:15] == '510300' and self.Mat_to_2005[mat] in [id[18:22], id[19:23]]:
                QuoteID_addin.append(id)
            elif self.sty == StockType.s300 and id[10:16] == '159919' and self.Mat_to_2005[mat] in [id[19:23], id[20:24]]:
                QuoteID_addin.append(id)

        self.OptionList[mat] = []
        QuoteID_addin_C_K = []
        for id in QuoteID_addin:
            if '.C.' in id:
                QuoteID_addin_C_K.append(float(id[last_C_P(id):]))
        QuoteID_addin_C_K.sort()
        for k in QuoteID_addin_C_K:
            self.OptionList[mat].append([OptionInfo(self.sty, mat, OptionType.C, k, '', '', ''), OptionInfo(self.sty, mat, OptionType.P, k, '', '', '')])

        self.k_list[mat] = QuoteID_addin_C_K

    def S_k0_posi(self, mat: Maturity): # update
        optlist = self.OptionList[mat]
        n = len(optlist)
        future = [optlist[i][0].midbidaskspread() - optlist[i][1].midbidaskspread() + optlist[i][0].K for i in range(n) if None not in [optlist[i][0].midbidaskspread(), optlist[i][1].midbidaskspread()] and 'A' not in optlist[i][0].yc_master_contract]
        future.sort()
        if future[1:-1] == []:
            return
        avg = np.mean(future[1:-1])
        self.S[mat] = avg
        self.posi[mat] = np.argmin(abs(np.array(self.k_list[mat]) - avg))
        self.k0[mat] = optlist[self.posi[mat]][0].K

class FutureData:

    def __init__(self, fty: FutureType):
        self.fty = fty
        self.Mat_to_2005 = {}
        self._2005_to_Mat = {}
        self.T = {}
        self.initT = {}
        self.P = {}
        self.ask = {}
        self.bid = {}
        self.cm = 300
        self.yc_master_contract: dict = {}
        self.matlist = [Maturity.M1, Maturity.M2, Maturity.Q1, Maturity.Q2]
        for mat in self.matlist:
            self.P[mat] = -1
            self.ask[mat] = -1 
            self.bid[mat] = -1
            self.yc_master_contract[mat] = ''
        self.getMat()

    def midbidaskspread(self, mat: Maturity):
        if '' not in [self.ask[mat], self.bid[mat]]:
            return (self.ask[mat] + self.bid[mat])/2
        else:
            return None
        
    def getMat(self):
        for mat in self.matlist:
            self.Mat_to_2005[mat] = Mat['contract_format'][self.fty][mat]
            self._2005_to_Mat[self.Mat_to_2005[mat]] = mat

        def num_weekend(date1: calendar.datetime.date, date2: calendar.datetime.date):
            num = 0
            oneday = calendar.datetime.timedelta(days = 1)
            date = calendar.datetime.date(date1.year, date1.month, date1.day)
            while date != date2:
                if date.weekday() == 5 or date.weekday() == 6 or date in holiday:
                    num += 1
                date += oneday
            return num

        c = calendar.Calendar(firstweekday=calendar.SUNDAY)
        year = localtime.tm_year; month = localtime.tm_mon; mday = localtime.tm_mday
        currentDate = calendar.datetime.date(year, month, mday)

        for mat in self.matlist:
            self.T[mat] = ((Mat['calendar'][self.fty][mat] - currentDate).days - num_weekend(currentDate, Mat['calendar'][self.fty][mat]))/244
            self.initT[mat] = self.T[mat]


g_TradeZMQ = None
g_QuoteZMQ = None
g_TradeSession = ""
g_QuoteSession = ""
exit_signal = 0


class monitor_yield(object):

    def __init__(self):
        self.load_file_signal = True
        self.strategy_contain_contract_num = {}
        self.strategy2totalprofit = {}
        self.strategy2totaldelta = {}
        self.strategy2totalgamma = {}
        self.strategy2totalvega = {}
        self.strategy2totaltheta = {}
        self.max_total_profit = {}

        self.label_var = {}
        self.add_new_signal = [1]
        self.bs_refresh_signal = []
        self.buy_sell_var = {}

        self.bs_root_flag = False
        self.od_root_flag = False
        self.mp_root_flag = False

        self.boxlist = []
        self.bs_boxlist = {}
        self.checkbutton_context_list = {}

        self.strategy_trade_return = {'all_data':[], 'type5': []}
        self.colors = ['#FFA500','#87CEFA','#778899', '#DB7093', '#FF1493',
                       '#7FFFAA','#F0E68C','#FF7F50','#C0C0C0','#BA55D3',
                       '#FF4500']

        self.stop_update_max_profit = {}

        # hedge
        self.hg_index = 0
        self.hg_root = {}
        self.hg_boxlist = {}
        self.hg_ongoing = {}
        self.hg_state = {}
        self.hg_p_update_list = {}
        self.hg_p_update_flag = {}

        self.hg_data = {}
        self.hg_change_list = {StockType.etf50: [StockType.etf50, StockType.h300, StockType.s300, StockType.gz300], StockType.h300: [StockType.h300, StockType.s300, StockType.gz300], StockType.s300: [StockType.s300, StockType.h300, StockType.gz300], StockType.gz300: [StockType.gz300]}
        self.order_for_hg = {}
        # futures / options used for hedging
        self.Ft_for_hg = {}
        self.Opt_for_hg = {}

        # 补单
        self.addin_orderid = []

        # 记录
        self.order_data_txt = open(f'./log/order data {localtime.tm_year}-{localtime.tm_mon}-{localtime.tm_mday}.txt', 'a')
        self.hedge_data_txt = open(f'./log/hedge data {localtime.tm_year}-{localtime.tm_mon}-{localtime.tm_mday}.txt', 'a')

        #部位是否有熔断
        self.if_position_cb: bool = False

        #random.shuffle(self.colors)
        #self.lock = threading.RLock()


    ##############################################################################################################
    def init_profit_ui(self):

        root = Tk()
        root.iconbitmap(default=r'./pictures/logo.ico')

        root.resizable(0, 0)
        root.title('策略持仓监控')

        self.main_root = root
        self.main_root_position = self.main_root.winfo_geometry()

        menubar = Menu(root)
        # 创建菜单项
        fmenu1 = Menu(root, tearoff=0)
        fmenu1.add_command(label='打开', command=self.load_file)
        fmenu1.add_separator()
        fmenu1.add_command(label='另存为',command=self.save_file)

        menubar.add_cascade(label="文件", menu=fmenu1)
        root.config(menu=menubar)

        fmenu2 = Menu(root, tearoff=0)
        fmenu2.add_command(label='查看策略', command=self.check_strategy_name)
        fmenu2.add_separator()
        fmenu2.add_command(label='修改策略', command=self.modify_strategy_name)

        menubar.add_cascade(label="策略名", menu=fmenu2)
        root.config(menu=menubar)

        self.p_root = root
        names = ['策略', '合约', '持仓数', '均价', '留仓损益', '平仓损益', '中价损益', '总收益', '当日最大总收益', '总Delta$(万)', '总Gamma$(万)', '总Vega$', '总Theta$', '买卖中价', '当前价格', 'delta$(万)', 'gamma$(万)', 'vega$', 'theta$']
        self.p_names = names
        for i,name in enumerate(names):
            Label(root, text=name, font = font.Font(family='Arial', size=10, weight=font.BOLD)).grid(row=0, column=i, sticky=E + W, pady=1)

        def callback():
            def close():
                g_TradeZMQ.trade_logout(g_TradeSession)
                g_QuoteZMQ.quote_logout(g_QuoteSession)
                self.order_data_txt.close()
                self.hedge_data_txt.close()
                root.destroy()
                global exit_signal
                exit_signal = 1
                os._exit(0)

            login_out = messagebox.askyesnocancel(title='提示', message='是否需要关闭前保存文件？')
            if login_out == True:
                self.save_file()
                close()
            elif login_out == False:
                close()
            elif login_out == None:
                pass

        root.protocol("WM_DELETE_WINDOW", callback)
        root.mainloop()


    def load_file(self):

        if not self.load_file_signal:
            messagebox.showerror(title='错误', message='导入文件失败，已导入文件，请重新开启软件再导入！')
            return

        path = filedialog.askopenfilename()
        if path == '':
            messagebox.showerror(title='错误', message='导入文件失败！')
            return

        inputs = []
        data = xlrd.open_workbook(path, encoding_override = 'utf-8')
        names = data.sheet_names()
        table = data.sheet_by_name(names[0])
        data.sheet_loaded(names[0])
        nrows = table.nrows

        t = 1
        for i in range(nrows):
            row = table.row_values(i, start_colx=0, end_colx=None)
            if t:
                t = 0
                continue
            if row[0] == 'HEDGE_F' or row[0] == 'HEDGE_O':
                continue
            strategy = row[0]
            contract = row[1]
            nums = int(row[2])
            avg_price = float(row[3])
            dynamic_profit = float(row[4])  # 所持仓，与当前价格计算而来
            fixed_profit = float(row[5])  # 卖掉而产生的收益
            inputs.append([strategy, contract, nums, avg_price, dynamic_profit, fixed_profit])

        for i, values in enumerate(inputs):
            if values[2] == 0: ### 持仓为零的不录入
                continue

            if values[0] not in list(self.label_var.keys()):
                self.label_var[values[0]] = {}
                for init in [self.strategy2totalprofit, self.strategy2totaldelta, self.strategy2totalgamma, self.strategy2totalvega, self.strategy2totaltheta, self.max_total_profit]:
                    init[values[0]] = StringVar(self.p_root)
                    init[values[0]].set('-inf') 

            self.label_var[values[0]][values[1]] = {}
            for j, name in enumerate(self.p_names):
                self.label_var[values[0]][values[1]][name] = StringVar(self.p_root)
                if j < 3:
                    self.label_var[values[0]][values[1]][name].set(values[j])
                else:
                    self.label_var[values[0]][values[1]][name].set('{:g}'.format(0))

        # read Ft_for_hg
        t = 1
        for i in range(nrows):
            row = table.row_values(i, start_colx=0, end_colx=None)
            if t:
                t = 0
                continue
            if not row[0] == 'HEDGE_F':
                continue
            if not int(row[5]) == 0:
                key = (row[1], str_to_type[row[2]], str_to_type[row[3]])
                if key not in list(self.Ft_for_hg.keys()):
                    self.Ft_for_hg[key] = {}
                used_mat = str_to_type[row[4]]
                if used_mat not in list(self.Ft_for_hg[key].keys()):
                    self.Ft_for_hg[key][used_mat] = 0
                self.Ft_for_hg[key][used_mat] += int(row[5])

        # read Opt_for_hg
        t = 1
        for i in range(nrows):
            row = table.row_values(i, start_colx=0, end_colx=None)
            if t:
                t = 0
                continue
            if not row[0] == 'HEDGE_O':
                continue
            if not int(row[8]) == 0:
                key = (row[1], str_to_type[row[2]], str_to_type[row[3]])
                if key not in list(self.Opt_for_hg.keys()):
                    self.Opt_for_hg[key] = {}
                used_sty = str_to_type[row[4]]
                used_mat = str_to_type[row[5]]
                used_call = row[6]
                used_put = row[7]
                if (used_sty, used_mat, (used_call, used_put)) not in list(self.Opt_for_hg[key].keys()):
                    self.Opt_for_hg[key][(used_sty, used_mat, (used_call, used_put))] = 0
                self.Opt_for_hg[key][(used_sty, used_mat, (used_call, used_put))] += int(row[8])

        self.p_refresh()
        self.load_file_signal = False


    def save_file(self):
        path = filedialog.askdirectory()
        if path == '':
            return

        dt = datetime.datetime.now()
        dt = str(dt).split(' ')[0]
        result_path = path + '/' + dt + '.xls'

        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('sheet')

        def insert_row(row, vals):
            for col, val in enumerate(vals):
                worksheet.write(row, col, val)

        row_counter = 0
        headers = ['策略', '合约', '持仓数', '均价', '留仓损益', '平仓损益', '总Delta$(万)', '总Gamma$(万)', '总Vega$', '总Theta$', 'delta$(万)', 'gamma$(万)', 'vega$', 'theta$']
        insert_row(row_counter, headers)
        row_counter += 1

        for strategy in list(self.label_var.keys()):
            for contract in list(self.label_var[strategy].keys()):
                nums = int(self.label_var[strategy][contract]['持仓数'].get())
                avg_price = float(self.label_var[strategy][contract]['均价'].get())
                dynamic_profit = float(self.label_var[strategy][contract]['留仓损益'].get())
                fixed_profit = float(self.label_var[strategy][contract]['平仓损益'].get())
                all_delta = str(self.strategy2totaldelta[strategy].get())
                all_gamma = str(self.strategy2totalgamma[strategy].get())
                all_vega = str(self.strategy2totalvega[strategy].get())
                all_theta = str(self.strategy2totaltheta[strategy].get())
                delta = float(self.label_var[strategy][contract]['delta$(万)'].get())
                gamma = float(self.label_var[strategy][contract]['gamma$(万)'].get())
                vega = float(self.label_var[strategy][contract]['vega$'].get())
                theta = float(self.label_var[strategy][contract]['theta$'].get())

                row_vals = [strategy, contract, nums, avg_price, dynamic_profit, fixed_profit, all_delta, all_gamma, all_vega, all_theta, delta, gamma, vega, theta]
                insert_row(row_counter, row_vals)
                row_counter += 1

        # record Ft_for_hg
        for i in list(self.Ft_for_hg.keys()):
            strategy = i[0]
            sty = type_to_str[i[1]]
            mat = type_to_str[i[2]]
            for j in list(self.Ft_for_hg[i].keys()):
                used_mat = type_to_str[j]
                if not self.Ft_for_hg[i][j] == 0:
                    row_vals = ['HEDGE_F', strategy, sty, mat, used_mat, self.Ft_for_hg[i][j]]
                    insert_row(row_counter, row_vals)
                    row_counter += 1

        # record Opt_for_hg
        for i in list(self.Opt_for_hg.keys()):
            strategy = i[0]
            sty = type_to_str[i[1]]
            mat = type_to_str[i[2]]
            for j in list(self.Opt_for_hg[i].keys()):
                used_sty = type_to_str[j[0]]
                used_mat = type_to_str[j[1]]
                used_call = j[2][0]
                used_put = j[2][1]
                if not self.Opt_for_hg[i][j] == 0:
                    row_vals = ['HEDGE_O', strategy, sty, mat, used_sty, used_mat, used_call, used_put, self.Opt_for_hg[i][j]]
                    insert_row(row_counter, row_vals)
                    row_counter += 1

        try:
            workbook.save(result_path)
        except:
            messagebox.showerror(title='错误', message='文件保存失败，当前的路径没有权限！')
            return

        if os.path.exists(result_path):
            messagebox.showinfo(title='提示', message='文件已经保存成功！')
        else:
            messagebox.showerror(title='错误', message='文件保存失败！')


    def check_strategy_name(self):
        strategies = []
        with open('./strategies.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for strategy in lines:
                strategies.append(strategy.replace('\n', ''))

        root = Tk()
        root.iconbitmap(default=r'./pictures/logo.ico')

        root.resizable(0, 0)
        self.main_root_position = self.main_root.winfo_geometry()
        index = [i for i, x in enumerate(self.main_root_position) if x == '+']
        root.geometry("%dx%d+%d+%d" % (233, 400, int(self.main_root_position[index[0] + 1 : index[1]]), int(self.main_root_position[index[1] + 1 :]) + 100))
        root.title('盈利界面')

        for i, strategy in enumerate(strategies):
            Label(root, text=strategy).grid(row=i, column=0, sticky=E)

        root.mainloop()


    def modify_strategy_name(self):
        messagebox.showinfo(title='~', message='对不起，还在开发~')


    def p_refresh(self):
        global localtime, trade_period
        localtime = time.localtime()
        if (localtime.tm_hour == 9 and localtime.tm_min >= 30) or localtime.tm_hour == 10 or (localtime.tm_hour == 11 and localtime.tm_min < 30) or localtime.tm_hour == 13 or (localtime.tm_hour == 14 and localtime.tm_min < 57):
            trade_period = True
        else:
            trade_period = False

        if len(self.add_new_signal) != 0:
            # 清空信号
            for i in range(len(self.add_new_signal) - 1, -1, -1):
                self.add_new_signal.pop(i)

            for box in self.boxlist:
                box.grid_forget()

            self.boxlist = []
            i = 1
            total_profit_position = self.p_names.index('总收益')
            total_delta_position = self.p_names.index('总Delta$(万)')
            total_gamma_position = self.p_names.index('总Gamma$(万)')
            total_vega_position = self.p_names.index('总Vega$')
            total_theta_position = self.p_names.index('总Theta$')
            max_total_profit_position = self.p_names.index('当日最大总收益')
            total_profit_row = 1

            try:

                for p, strategy in enumerate(list(self.label_var.keys())):

                    color = self.colors[p]
                    self.strategy_contain_contract_num[strategy] = len(self.label_var[strategy])
                    

                    # 盈利界面合约显示顺序
                    label_contracts_list = sorted(self.label_var[strategy].keys())


                    for contract in label_contracts_list:
                        for j, name in enumerate(self.p_names):
                            if name not in ['策略', '总收益', '总Delta$(万)', '总Gamma$(万)', '总Vega$', '总Theta$', '当日最大总收益']:
                                bg_color = color
                                # 熔断提示
                                if contract[:6] == 'TC.O.S' and name == '合约':
                                    opt = name_to_data(contract)
                                    if opt.cb:
                                        bg_color = '#FF0000'
                                        self.if_position_cb = True
                                l = Label(self.p_root, text='', textvariable=self.label_var[strategy][contract][name], bg=bg_color, font = font.Font(family='Arial', size=10))
                                self.boxlist.append(l)
                                l.grid(row=i, column=j, sticky=E + W)


                        i += 1

                    l = Label(self.p_root, text=strategy, height=self.strategy_contain_contract_num[strategy], bg=color, font = font.Font(family='Arial', size=10))
                    self.boxlist.append(l)
                    l.grid(row=total_profit_row, column=0, rowspan=self.strategy_contain_contract_num[strategy], sticky=N + S + W + E)

                    for total in [(self.strategy2totalprofit, total_profit_position), (self.strategy2totaldelta, total_delta_position), (self.strategy2totalgamma, total_gamma_position), (self.strategy2totalvega, total_vega_position), (self.strategy2totaltheta, total_theta_position), (self.max_total_profit, max_total_profit_position)]:
                        l = Label(self.p_root, text=1, height=self.strategy_contain_contract_num[strategy], textvariable=total[0][strategy], bg=color, font = font.Font(family='Arial', size=10))
                        self.boxlist.append(l)
                        l.grid(row=total_profit_row, column=total[1], rowspan=self.strategy_contain_contract_num[strategy], sticky=N + S + W + E)
                    total_profit_row += self.strategy_contain_contract_num[strategy]


                j = len(self.p_names) - 1

                b = Button(self.p_root, text='成交回报', width=10, command=self.open_bs_ui)
                b.grid(row=i, column= j, columnspan=1, sticky=W, padx=10, pady=10)
                self.boxlist.append(b)

                b = Button(self.p_root, text='参数修改', width=10, command=self.open_mp_ui)
                b.grid(row=i, column= j-1, columnspan=1, sticky=W, padx=10, pady=10)
                self.boxlist.append(b)

                b = Button(self.p_root, text='对冲', width=10, command=self.open_hedge_ui)
                b.grid(row=i, column= j-2, columnspan=1, sticky=W, padx=10, pady=10)
                self.boxlist.append(b)

            except:
                pass

        self.p_root.after(500, self.p_refresh)


    def p_update(self, quote):

        BidPrice1 = quote['Bid'] if quote['Bid'] == '' else float(quote['Bid'])
        AskPrice1 = quote['Ask'] if quote['Ask'] == '' else float(quote['Ask'])
        LastPrice = quote["TradingPrice"] if quote['TradingPrice'] == '' else float(quote['TradingPrice'])
        avgP = quote['YClosedPrice'] if quote['YClosedPrice'] == '' else float(quote['YClosedPrice']) ## 实际录昨收盘价
        contract = quote['Symbol']


        if 'TC.O' in contract:

            opt = name_to_data(contract)
            sty = opt.sty
            mat = opt.mat

            # update data_opt
            # update OptionList
            opt.P = LastPrice
            opt.bid = BidPrice1
            opt.ask = AskPrice1
            # update S, k0, posi
            data_opt[sty].S_k0_posi(mat)
            opt.S = data_opt[sty].S[mat]
            # update time
            data_opt[sty].T[mat] = data_opt[sty].initT[mat] + ((15 - localtime.tm_hour - 1 - 1.5 * (localtime.tm_hour < 12)) * 60 * 60 + (60 - localtime.tm_min -1) * 60 + (60 - localtime.tm_sec) + 120) / (60 * 60 * 4 + 120) / 244
            opt.T = data_opt[sty].T[mat]
            # update cb
            if BidPrice1 == AskPrice1 and '' not in [BidPrice1, AskPrice1] and not [BidPrice1, AskPrice1] == [data_opt[sty].mc] * 2:
                opt.cb = True
            else:
                opt.cb = False
            # yc master contract name
            opt.yc_master_contract = contract

        elif 'IF' in contract:
            mat_future = data_opt[FutureType.IF]._2005_to_Mat[contract[-4 : ]]
            data_opt[FutureType.IF].P[mat_future] = LastPrice
            data_opt[FutureType.IF].ask[mat_future] = AskPrice1
            data_opt[FutureType.IF].bid[mat_future] = BidPrice1
            data_opt[FutureType.IF].yc_master_contract[mat_future] = contract

        elif 'IH' in contract:
            mat_future = data_opt[FutureType.IH]._2005_to_Mat[contract[-4 : ]]
            data_opt[FutureType.IH].P[mat_future] = LastPrice
            data_opt[FutureType.IH].ask[mat_future] = AskPrice1
            data_opt[FutureType.IH].bid[mat_future] = BidPrice1
            data_opt[FutureType.IH].yc_master_contract[mat_future] = contract


        # update label_var
        try:

            if self.load_file_signal:
                return

            if not self.if_position_cb and 'TC.O.S' in contract and opt.cb and len([0 for s in list(self.label_var.keys()) if contract in list(self.label_var[s].keys())]) > 0:
                self.add_new_signal.append(1)

            if self.if_position_cb:
                num = 0
                for s in list(self.label_var.keys()):
                    for c in list(self.label_var[s].keys()):
                        if 'TC.O.S' in c:
                            o = name_to_data(c)
                            if o.cb:
                                num += 1
                if num == 0:
                    self.if_position_cb = False
                    self.add_new_signal.append(1)

            # greeks已更新flag
            for index in list(self.hg_root.keys()):
                hedge_strategy = self.hg_boxlist[index][0][0].get()

                if hedge_strategy not in list(self.order_for_hg.keys()):
                    if contract in self.hg_p_update_list[index]:
                        self.hg_p_update_list[index].remove(contract)
           
            for strategy in list(self.label_var.keys()):
                if contract not in list(self.label_var[strategy].keys()):
                    continue

                # 录昨收
                if not avgP == '' and ((localtime.tm_hour == 9 and localtime.tm_min < 31) or self.label_var[strategy][contract]['均价'].get() == '0'):
                    self.label_var[strategy][contract]['均价'].set('{:g}'.format(avgP))

                price_conver = 0
                if 'SSE' in contract or 'SZSE' in contract:
                    price_conver = 10000
                elif 'CFFEX' in contract:
                    if 'IO' in contract:
                        price_conver = 100
                    elif 'IF' in contract or 'IH' in contract:
                        price_conver = 300

                # profit
                price = float(self.label_var[strategy][contract]['均价'].get())
                volume = int(self.label_var[strategy][contract]['持仓数'].get())
                prof = volume * (LastPrice - price) * price_conver

                self.label_var[strategy][contract]['留仓损益'].set('{:g}'.format(prof))
                self.label_var[strategy][contract]['当前价格'].set('{:g}'.format(LastPrice))

                avg_bid_ask = (AskPrice1 + BidPrice1) / 2
                self.label_var[strategy][contract]['买卖中价'].set('{:g}'.format(avg_bid_ask))

                if abs(AskPrice1 - BidPrice1) > 0.05 * LastPrice:
                    self.label_var[strategy][contract]['中价损益'].set('{:g}'.format(prof))
                else:
                    middle_pro = volume * (avg_bid_ask - price) * price_conver
                    self.label_var[strategy][contract]['中价损益'].set('%0.1f' %middle_pro)

                total_profit = 0
                middle_price_profit = 0
                for val in list(self.label_var[strategy].keys()):
                    total_profit = total_profit + \
                                    float(self.label_var[strategy][val]['留仓损益'].get()) + \
                                    float(self.label_var[strategy][val]['平仓损益'].get())

                    middle_price_profit = middle_price_profit + \
                                            float(self.label_var[strategy][val]['中价损益'].get()) + + \
                                            float(self.label_var[strategy][val]['平仓损益'].get())

                self.strategy2totalprofit[strategy].set('{}\n{}'.format(int(total_profit),
                                                                        int(middle_price_profit)))


                if strategy in list(self.stop_update_max_profit.keys()) and time.time() - self.stop_update_max_profit[strategy] > 5:
                    self.stop_update_max_profit.pop(strategy)

                if trade_period and not ((localtime.tm_hour == 9 and localtime.tm_min == 30) or (localtime.tm_hour == 11 and localtime.tm_min == 29) or (localtime.tm_hour == 13 and localtime.tm_min == 0)) and (middle_price_profit > float(self.max_total_profit[strategy].get())) and (BidPrice1 != AskPrice1 or sty == StockType.gz300) and not quote["TradingPrice"] == '' and strategy not in self.stop_update_max_profit.keys():
                    self.max_total_profit[strategy].set('{:g}'.format(int(middle_price_profit)))

                # greeks
                vol = int(self.label_var[strategy][contract]['持仓数'].get())
                
                if 'TC.O' in contract:

                    opt._iv = opt.iv()
                    delta = opt.delta()
                    gamma = opt.gamma()
                    vega = opt.vega()
                    theta = opt.theta()
                
                    self.label_var[strategy][contract]['delta$(万)'].set('{:.1f}'.format(vol * data_opt[sty].S[mat] * price_conver * delta / 10000))
                    self.label_var[strategy][contract]['gamma$(万)'].set('{:.1f}'.format(vol * data_opt[sty].S[mat] ** 2 * price_conver * gamma * 0.01 / 10000))
                    self.label_var[strategy][contract]['vega$'].set('{:.0f}'.format(vol * vega * price_conver * 0.01))
                    self.label_var[strategy][contract]['theta$'].set('{:.0f}'.format(vol * theta * price_conver / 244))

                elif 'TC.F' in contract:

                    self.label_var[strategy][contract]['delta$(万)'].set('{:.1f}'.format(vol * (BidPrice1 + AskPrice1) / 2 * price_conver * 1 / 10000))
                    self.label_var[strategy][contract]['gamma$(万)'].set('{:.1f}'.format(0))
                    self.label_var[strategy][contract]['vega$'].set('{:.0f}'.format(0))
                    self.label_var[strategy][contract]['theta$'].set('{:.0f}'.format(0))


                ty_position = {StockType.etf50: False, StockType.h300: False, StockType.gz300: False, StockType.s300: False, FutureType.IF: False, FutureType.IH: False}
                ty_mat_position = {StockType.etf50: {}, StockType.h300: {}, StockType.gz300: {}, StockType.s300: {}, FutureType.IF: {}, FutureType.IH: {}}
                ty_contract_element = {StockType.etf50: 'TC.O.SSE.510050', StockType.h300: 'TC.O.SSE.510300', StockType.gz300: 'TC.O.CFFEX.IO', StockType.s300: 'TC.O.SZSE.159919', FutureType.IF: 'TC.F.CFFEX.IF', FutureType.IH: 'TC.F.CFFEX.IH'}
                ty_name = {StockType.etf50: '50E', StockType.h300: '沪E', StockType.gz300: '股指', StockType.s300: '深E', FutureType.IF: 'IF', FutureType.IH: 'IH'}


                for i, comb in enumerate([('delta$(万)', self.strategy2totaldelta[strategy]), ('gamma$(万)', self.strategy2totalgamma[strategy]), ('vega$', self.strategy2totalvega[strategy]), ('theta$', self.strategy2totaltheta[strategy])]):

                    greeks = {}
                    for ty in list(ty_position.keys()):
                        greeks[ty] = {}
                        for mat_ in data_opt[ty].matlist:
                            greeks[ty][mat_] = 0
                            ty_mat_position[ty][mat_] = False

                    for val in list(self.label_var[strategy].keys()):
                        for ty in list(greeks.keys()):
                            if ty_contract_element[ty] in val:
                                ty_position[ty] = True
                                for mat_ in list(greeks[ty].keys()):
                                    if Mat['contract_format'][ty][mat_] in val:
                                        greeks[ty][mat_] += float(self.label_var[strategy][val][comb[0]].get())
                                        ty_mat_position[ty][mat_] = True

                    overall = sum(sum(greeks[ty].values()) for ty in list(ty_position.keys()))

                    if len([0 for _ in ty_position.values() if _ == True]) > 1:
                        if i < 2:
                            _str = '{:.1f}'.format(overall)
                        else:
                            _str = '{:.0f}'.format(overall)

                        for ty in list(ty_position.keys()):
                            if ty_position[ty]:
                                mat_num = len([0 for _ in ty_mat_position[ty].values() if _ == True])
                                if i < 2:
                                    _str += '\n' + str(ty_name[ty]) + ': ' + '{:.1f}'.format(sum(greeks[ty].values()))
                                    if mat_num > 1:
                                        _str += '\n' + '\n'.join([Mat['contract_format'][ty][mat_] + ': ' + '{:.1f}'.format(greeks[ty][mat_]) for mat_ in list(greeks[ty].keys()) if ty_mat_position[ty][mat_]])
                                else:
                                    _str += '\n' + str(ty_name[ty]) + ': ' + '{:.0f}'.format(sum(greeks[ty].values()))
                                    if mat_num > 1:
                                        _str += '\n' + '\n'.join([Mat['contract_format'][ty][mat_] + ': ' + '{:.0f}'.format(greeks[ty][mat_]) for mat_ in list(greeks[ty].keys()) if ty_mat_position[ty][mat_]])
                        comb[1].set(_str)
                    else:
                        for ty in list(ty_position.keys()):
                            if ty_position[ty]:
                                mat_num = len([0 for _ in ty_mat_position[ty].values() if _ == True])
                                if i < 2:
                                    _str = '{:.1f}'.format(overall)
                                    if mat_num > 1:
                                        _str += '\n' + '\n'.join([Mat['contract_format'][ty][mat_] + ': ' + '{:.1f}'.format(greeks[ty][mat_]) for mat_ in list(greeks[ty].keys()) if ty_mat_position[ty][mat_]])
                                else:
                                    _str = '{:.0f}'.format(overall)
                                    if mat_num > 1:
                                        _str += '\n' + '\n'.join([Mat['contract_format'][ty][mat_] + ': ' + '{:.0f}'.format(greeks[ty][mat_]) for mat_ in list(greeks[ty].keys()) if ty_mat_position[ty][mat_]])
                                comb[1].set(_str)


                    # hedge data
                    if strategy not in list(self.hg_data.keys()):
                        self.hg_data[strategy] = {}
                        self.hg_data[strategy]['position'] = {}
                    self.hg_data[strategy][comb[0]] = greeks
                    self.hg_data[strategy]['position']['type'] = ty_position
                    self.hg_data[strategy]['position']['mat'] = ty_mat_position

            # greeks已更新flag
            for index in list(self.hg_root.keys()):
                self.hg_p_update_flag[index] = False
                if self.hg_p_update_list[index] == []:
                    self.hg_p_update_flag[index] = True

        except:
            pass


    ##############################################################################################################
    def open_bs_ui(self):

        self.bs_refresh_signal.append(1)
        if self.bs_root_flag:
            return
        self.init_buy_sell_ui()


    def init_buy_sell_ui(self):

        strategies = []
        with open('./strategies.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for strategy in lines:
                strategies.append(strategy.replace('\n',''))

        self.strategies = sorted(set(strategies), key=strategies.index)

        root = Toplevel()
        self.root = root
        root.title('成交回报')
        self.main_root_position = self.main_root.winfo_geometry()
        index = [i for i, x in enumerate(self.main_root_position) if x == '+']
        root.geometry("%dx%d+%d+%d" % (750, 500, int(self.main_root_position[index[0] + 1 : index[1]]) + 1100, int(self.main_root_position[index[1] + 1 :]) + 400))
        canvas = Canvas(root, borderwidth=0)
        frame = Frame(canvas)
        self.bs_root = frame
        self.bs_root_flag = True
        vsb = Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((4, 4), window=frame, anchor="nw")

        def onFrameConfigure(canvas):
            '''Reset the scroll region to encompass the inner frame'''
            canvas.configure(scrollregion=canvas.bbox("all"))

        frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))

        names = ['交易时间', '成交类型','数量', '价格', '合约', '策略']
        self.bs_names = names

        for i, name in enumerate(names):
            Label(frame, text=name).grid(row=0, column=i, sticky=E + W, padx=10)

        self.bs_refresh()
        def callback():
            root.destroy()
            self.bs_root_flag = False
        root.protocol("WM_DELETE_WINDOW", callback)
        root.mainloop()


    def bs_refresh(self):

        if len(self.bs_refresh_signal) != 0:
            # 清空信号
            for i in range(len(self.bs_refresh_signal) - 1, -1, -1):
                self.bs_refresh_signal.pop(i)


            for k in list(self.bs_boxlist.keys()):
                for box in self.bs_boxlist[k]:
                    try:
                        box.grid_forget()
                    except:
                        pass

            self.bs_boxlist = {}


            for i, k1 in enumerate(list(self.buy_sell_var.keys())):
                self.bs_boxlist[i] = []
                for j, k2 in enumerate(list(self.buy_sell_var[k1].keys())):
                    l = Label(self.bs_root, text=self.buy_sell_var[k1][k2])
                    self.bs_boxlist[i].append(l)
                    l.grid(row=i + 1, column=j, sticky=E + W, padx=10)

                self.checkbutton_context_list[i] = {}
                self.checkbutton_context_list[i][0] = IntVar(self.bs_root)
                if self.buy_sell_var[k1]['策略'] == '未知': # 内外部下单
                    l = Checkbutton(self.bs_root,variable=self.checkbutton_context_list[i][0])
                    l.grid(row=i + 1, column=j + 1, sticky=E + W, padx=10)
                else:
                    self.checkbutton_context_list[i][0].set(0)
                    l = None
                self.checkbutton_context_list[i][1] = l
                self.bs_boxlist[i].append(l)


            i = len(self.bs_boxlist)
            self.bs_boxlist[i] = []
            stg = StringVar()
            stgChosen = ttk.Combobox(self.bs_root, width=10, textvariable=stg)
            stgChosen['values'] = [strategy for strategy in self.strategies]
            stgChosen.grid(row=i + 1, column=0, padx=5)
            stgChosen.current(0)
            self.bs_boxlist[i].append(stgChosen)

            b = Button(self.bs_root, text="全选", command=self.all_select, width=10)
            b.grid(row=i + 1, column=1, sticky=E, padx=5, pady=10)
            self.bs_boxlist[i].append(b)

            b = Button(self.bs_root, text="全不选", command=self.de_all_select, width=10)
            b.grid(row=i + 1, column=2, sticky=E, padx=5, pady=10)
            self.bs_boxlist[i].append(b)

            b = Button(self.bs_root, text="更新", command=self.bs_update_thread, width=10)
            b.grid(row=i + 1, column=3, sticky=E, padx=5, pady=10)
            self.bs_boxlist[i].append(b)


            # 筛选成交回报
            self.bs_boxlist[i+1] = []
            sty = StringVar()
            styChosen = ttk.Combobox(self.bs_root, width=10, textvariable=sty)
            styChosen['values'] = ['510050', '510300', '159919', 'IO', 'IF', 'IH']
            styChosen.grid(row=i + 2, column=0, padx=5)
            styChosen.current(0)
            self.bs_boxlist[i+1].append(styChosen)

            mat = StringVar()
            matChosen = ttk.Combobox(self.bs_root, width=10, textvariable=mat)
            matChosen['values'] = ['']
            matChosen.grid(row=i + 2, column=1, padx=5)
            matChosen.current(0)
            self.bs_boxlist[i+1].append(matChosen)

            def func(*args):
                if styChosen.get() == '510050':
                    matlist = list(Mat['contract_format'][StockType.etf50].values())
                elif styChosen.get() == '510300':
                    matlist = list(Mat['contract_format'][StockType.h300].values())
                elif styChosen.get() == '159919':
                    matlist = list(Mat['contract_format'][StockType.s300].values())
                elif styChosen.get() == 'IO':
                    matlist = list(Mat['contract_format'][StockType.gz300].values())
                elif styChosen.get() == 'IF':
                    matlist = list(Mat['contract_format'][FutureType.IF].values())
                elif styChosen.get() == 'IH':
                    matlist = list(Mat['contract_format'][FutureType.IH].values())
                else:
                    matlist = []

                matChosen['values'] = matlist

            styChosen.bind("<<ComboboxSelected>>", func)

            b = Button(self.bs_root, text='筛选', command=self.filter, width=10)
            b.grid(row=i + 2, column=2, sticky=E, padx=5, pady=10)
            self.bs_boxlist[i+1].append(b)

        self.bs_root.after(2000, self.bs_refresh) # when root destroyed, stops.


    def check_buy_sell(self, quote):

        self.order_data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '(全) ' + str(quote) + '\n')

        if quote not in self.strategy_trade_return['all_data']:
            self.strategy_trade_return['all_data'].append(quote)
        else:
            return

        id,cumqty,leavesqty = quote['OrderID'], int(quote['CumQty']), int(quote['LeavesQty'])
        contract = quote['Symbol']
        Price = float(quote['AvgPrice'])
        Direction = int(quote['Side'])
        utc = quote['TransactTime']
        TradeTime = '{}:{}:{}'.format(int(utc[0]) + 8, utc[1:3], utc[3:6])
        ExecType = quote['ExecType']
        strategy = quote['UserKey1']
        source = quote['UserKey2']
        OriginalQty = quote['OriginalQty']
        OrderQty = quote['OrderQty']

        if id == '':
            return

        flag = False

        if strategy == '':
            outer = True
            self.order_data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '(外) ' + str(quote) + '\n')
        else:
            outer = False
            self.order_data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '(内) ' + str(quote) + '\n')

        if ExecType in ['3','6'] and not Price == 0.0:
            if id not in list(self.strategy_trade_return.keys()):
                if cumqty != 0:
                    Volume = cumqty
                    flag = True

                self.strategy_trade_return[id] = leavesqty

            else:
                Volume = self.strategy_trade_return[id] - leavesqty
                self.strategy_trade_return[id] = leavesqty
                flag = True

        # 内部下单
        if not outer:
            if ExecType == '5' and id not in self.strategy_trade_return['type5']:
                if id not in list(self.strategy_trade_return.keys()):
                    Volume = int(OrderQty)
                else:
                    Volume = int(OrderQty) - (int(OriginalQty) - self.strategy_trade_return[id])
                
                self.strategy_trade_return[id] = int(OriginalQty) - int(OrderQty)
                self.strategy_trade_return['type5'].append(id)
                flag = True


        while flag:
            self.order_data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '(更新会使用的成交回报) ' + str(quote) + '\n')

            if Volume == 0 or Price == 0.0:
                break

            self.buy_sell_var[len(self.buy_sell_var) + 1] = {}
            self.buy_sell_var[len(self.buy_sell_var)]['交易时间'] = TradeTime
            t = [{1: '买', 2: '卖'}]
            self.buy_sell_var[len(self.buy_sell_var)]['成交类型'] = t[0][Direction]
            self.buy_sell_var[len(self.buy_sell_var)]['数量'] = Volume
            self.buy_sell_var[len(self.buy_sell_var)]['价格'] = '%f'%Price
            self.buy_sell_var[len(self.buy_sell_var)]['合约'] = contract
            if outer: # 内外部下单
                self.buy_sell_var[len(self.buy_sell_var)]['策略'] = '未知'
            else:
                self.buy_sell_var[len(self.buy_sell_var)]['策略'] = strategy


            # 内部下单，更新到盈利界面
            if not outer:

                price_conver = 0
                if 'SSE' in contract or 'SZSE' in contract:
                    price_conver = 10000
                elif 'CFFEX' in contract:
                    if 'IO' in contract:
                        price_conver = 100
                    elif 'IF' in contract or 'IH' in contract:
                        price_conver = 300

                in_price = Price
                in_volume = int(Volume)
                in_type = t[0][Direction]


                if strategy not in list(self.label_var.keys()) or \
                        contract not in list(self.label_var[strategy].keys()):
                    self.add(strategy,contract)

                volume = int(self.label_var[strategy][contract]['持仓数'].get())
                price = float(self.label_var[strategy][contract]['均价'].get())

                direction = 0
                if volume > 0:
                    direction = 1
                elif volume < 0:
                    direction = -1
                t = {'买': 1, '卖': -1}
                in_profit = 0
                if t[in_type] == direction or direction == 0:
                    price = (price * abs(volume) + in_price * in_volume) / (abs(volume) + in_volume)
                else:
                    in_profit = (price - in_price) * in_volume * t[in_type] * price_conver
                remain_volume = volume + in_volume * t[in_type]


                self.label_var[strategy][contract]['持仓数'].set(remain_volume)
                deal_profit = float(self.label_var[strategy][contract]['平仓损益'].get()) \
                              + in_profit
                self.label_var[strategy][contract]['平仓损益'].set('%0.1f' % deal_profit)
                self.label_var[strategy][contract]['均价'].set('{:g}'.format(price))


                # 判断 自对冲下单 是否完成
                if source == 'hedge':
                    if strategy in list(self.order_for_hg.keys()):
                        if contract in list(self.order_for_hg[strategy].keys()) and OriginalQty == OrderQty and leavesqty == 0:
                            self.order_for_hg[strategy].pop(contract)
                        if self.order_for_hg[strategy] == {}:
                            self.order_for_hg.pop(strategy)

            self.bs_refresh_signal.append(1)
            break


        # 补单
        if not outer and ExecType in ['5', '8', '9'] and not id in self.addin_orderid:
            self.order_data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '(需要补单的成交回报) ' + str(quote) + '\n')

            num_add = int(OriginalQty) - int(OrderQty)
            mp = 1 if Direction == 1 else -1
            num_add *= mp

            if source == 'hedge':
                if strategy in list(self.order_for_hg.keys()):
                    if contract in list(self.order_for_hg[strategy].keys()):
                        self.order_for_hg[strategy][contract] = num_add

            self.addin_orderid.append(id)

            self.order_api(contract, 'HIT', num_add, strategy, source)

        self.order_data_txt.flush()


    def all_select(self):
        for k in list(self.checkbutton_context_list.keys()):
            if not self.checkbutton_context_list[k][1] == None: # 内外部下单
                self.checkbutton_context_list[k][1].select()


    def de_all_select(self):
        for k in list(self.checkbutton_context_list.keys()):
            if not self.checkbutton_context_list[k][1] == None: #内外部下单
                self.checkbutton_context_list[k][1].deselect()


    def filter(self):

        str_sty = self.bs_boxlist[len(self.bs_boxlist)-1][0].get()
        str_mat = self.bs_boxlist[len(self.bs_boxlist)-1][1].get()

        if '' in [str_sty, str_mat]:
            return

        for k in list(self.checkbutton_context_list.keys()):
            if not self.checkbutton_context_list[k][1] == None: # 内外部下单
                contract = self.bs_boxlist[k][4].cget('text')
                if str_sty in contract and str_mat in contract:
                    self.checkbutton_context_list[k][1].select()


    def bs_update_thread(self):
    
        thread = threading.Thread(target = self.bs_update, args=())
        thread.setDaemon(True)
        thread.start()


    def bs_update(self):

        login_out = messagebox.askquestion(title='提示', message='选对了策略吗？确定更新？')

        if login_out != 'yes':
            return

        strategy = self.bs_boxlist[len(self.bs_boxlist)-2][0].get()
        
        if strategy == '':
            return

        # 更新后5s停更最大盈亏
        self.stop_update_max_profit[strategy] = time.time()

        ks = []

        for i, k1 in enumerate(list(self.buy_sell_var.keys())):

            if self.checkbutton_context_list[i][0].get() == 0:
                continue

            ks.append(k1)
            contract = self.buy_sell_var[k1]['合约']

            price_conver = 0
            if 'SSE' in contract or 'SZSE' in contract:
                price_conver = 10000
            elif 'CFFEX' in contract:
                if 'IO' in contract:
                    price_conver = 100
                elif 'IF' in contract or 'IH' in contract:
                    price_conver = 300


            bs_price = float(self.buy_sell_var[k1]['价格'])
            bs_volume = int(self.buy_sell_var[k1]['数量'])
            bs_type = self.buy_sell_var[k1]['成交类型']


            if strategy not in list(self.label_var.keys()) or \
                    contract not in list(self.label_var[strategy].keys()):
                self.add(strategy,contract)

            volume = int(self.label_var[strategy][contract]['持仓数'].get())
            price = float(self.label_var[strategy][contract]['均价'].get())

            direction = 0
            if volume > 0:
                direction = 1
            elif volume < 0:
                direction = -1
            t = {'买': 1, '卖': -1}
            bs_profit = 0
            if t[bs_type] == direction or direction == 0:
                price = (price * abs(volume) + bs_price * bs_volume) / (abs(volume) + bs_volume)
            else:
                bs_profit = (price - bs_price) * bs_volume * t[bs_type] * price_conver
            remain_volume = volume + bs_volume * t[bs_type]


            self.label_var[strategy][contract]['持仓数'].set(remain_volume)
            deal_profit = float(self.label_var[strategy][contract]['平仓损益'].get()) \
                          + bs_profit
            self.label_var[strategy][contract]['平仓损益'].set('%0.1f' % deal_profit)
            self.label_var[strategy][contract]['均价'].set('{:g}'.format(price))


        for k in ks:
            self.buy_sell_var.pop(k)
            self.checkbutton_context_list.pop(k-1)
        nums = [i+1 for i in range(len(self.buy_sell_var))]
        temp = {}
        temp_c = {}
        for i,k in zip(nums, self.buy_sell_var.keys()):
            temp[i]=self.buy_sell_var[k]
            temp_c[i - 1] = self.checkbutton_context_list[k - 1]
        self.buy_sell_var = temp
        self.checkbutton_context_list = temp_c

        self.bs_refresh_signal.append(1)


    def add(self, strategy, contract):

        names = ['策略', '合约', '持仓数', '均价', '留仓损益', '平仓损益', '中价损益', '买卖中价', '当前价格', 'delta$(万)', 'gamma$(万)', 'vega$', 'theta$']
        init_data = ['0' for _ in names]
        init_data[0], init_data[1] = strategy, contract

        if strategy not in list(self.label_var.keys()):
            self.label_var[strategy] = {}
            for init in [self.strategy2totalprofit, self.strategy2totaldelta, self.strategy2totalgamma, self.strategy2totalvega, self.strategy2totaltheta, self.max_total_profit]:
                init[strategy] = StringVar(self.p_root)
                init[strategy].set('-inf')

        if contract not in list(self.label_var[strategy].keys()):
            self.label_var[strategy][contract] = {}
            for j, name in enumerate(names):
                self.label_var[strategy][contract][name] = StringVar(self.p_root)
                self.label_var[strategy][contract][name].set(init_data[j])

        self.add_new_signal.append(1)


    ##############################################################################################################
    def order_api(self, target: str, price: str, num: int, strategy: str, source: str):
        # 查询持仓
        accountInfo = g_TradeZMQ.account_lookup(g_TradeSession)
        if accountInfo != None:
            arrInfo = accountInfo["Accounts"]
            if len(arrInfo) != 0:
                strAccountMask = arrInfo[0]["AccountMask"]

        g_TradeZMQ.position(g_TradeSession,strAccountMask,"")

        if num == 0:
            return

        side = '1' if num > 0 else '2'
        if price == 'HIT':
            Price = 'ASK+0' if side == '1' else 'BID+0'
        else:
            return

        Param = {

        'BrokerID':arrInfo[0]['BrokerID'],
        'Account':arrInfo[0]['Account'],
        'Symbol':target,
        'Side':side,
        'Price':Price,
        'TimeInForce':'2',# 'IOC | FAK'
        'OrderType':'2',
        'OrderQty':str(abs(num)),
        'PositionEffect':'4',
        'UserKey1': strategy,
        'UserKey2': source,

        }
        print(g_TradeZMQ.new_order(g_TradeSession,Param))


    def open_hedge_ui(self):
        self.init_hedge_ui()


    def init_hedge_ui(self):

        self.hg_index += 1

        strategies = list(self.label_var.keys())
        if strategies == []:
            strategies = ['']

        root = Toplevel()
        root.title('对冲')
        self.main_root_position = self.main_root.winfo_geometry()
        index = [i for i, x in enumerate(self.main_root_position) if x == '+']
        root.geometry("%dx%d+%d+%d" % (750, 300, int(self.main_root_position[index[0] + 1 : index[1]]), int(self.main_root_position[index[1] + 1 :]) + 100))
        canvas = Canvas(root, borderwidth=0)
        frame = Frame(canvas)
        hedge_index = self.hg_index
        self.hg_root[hedge_index] = frame
        self.hg_boxlist[hedge_index] = {0:[]}
        self.hg_p_update_flag[hedge_index] = True
        self.hg_p_update_list[hedge_index] = []
        vsb = Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((4, 4), window=frame, anchor="nw")

        def onFrameConfigure(canvas):
            '''Reset the scroll region to encompass the inner frame'''
            canvas.configure(scrollregion=canvas.bbox("all"))

        frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))


        lb_stg = ttk.Label(self.hg_root[hedge_index], text = '策略')
        lb_stg.grid(row=1, column=1)
        stg = StringVar()
        stgChosen = ttk.Combobox(self.hg_root[hedge_index], width=10, textvariable=stg)
        stgChosen['values'] = strategies
        stgChosen.grid(column=1, row=2, padx=5)
        stgChosen.current(0)
        self.hg_boxlist[hedge_index][0].append(stgChosen)

        lb_grk = ttk.Label(self.hg_root[hedge_index], text = 'Greeks')
        lb_grk.grid(row=1, column=2)
        grk = StringVar()
        grkChosen = ttk.Combobox(self.hg_root[hedge_index], width=10, textvariable=grk)
        grkChosen['values'] = ['delta$(万)']
        grkChosen.grid(column=2, row=2, padx=5)
        grkChosen.current(0)
        self.hg_boxlist[hedge_index][0].append(grkChosen)

        lb_thred = ttk.Label(self.hg_root[hedge_index], text = '阈值（万）')
        lb_thred.grid(row=1, column=3)
        thred = StringVar()
        thredEntry = ttk.Entry(self.hg_root[hedge_index], width=10, textvariable=thred)
        thredEntry.grid(column=3, row=2, padx=5)
        self.hg_boxlist[hedge_index][0].append(thredEntry)

        lb_way = ttk.Label(self.hg_root[hedge_index], text = '方式')
        lb_way.grid(row=1, column=4)
        way = StringVar()
        wayChosen = ttk.Combobox(self.hg_root[hedge_index], width=10, textvariable=way)
        wayChosen['values'] = ['合成', '先期货后合成']
        wayChosen.grid(column=4, row=2, padx=5)
        wayChosen.current(0)
        self.hg_boxlist[hedge_index][0].append(wayChosen)


        self.hg_state[hedge_index] = StringVar()
        self.hg_state[hedge_index].set('对冲')
        b = Button(self.hg_root[hedge_index], textvariable=self.hg_state[hedge_index], command=lambda:self.hedge_thread(hedge_index), width=10)
        b.grid(row=2, column=5, sticky=E, padx=5, pady=10)

        b = Button(self.hg_root[hedge_index], text="停止对冲", command=lambda:self.stop_hedge(hedge_index), width=10)
        b.grid(row=2, column=6, sticky=E, padx=5, pady=10)


        # 手动板
        l = ttk.Label(self.hg_root[hedge_index], text = '手动模式')
        l.grid(row=1, column=7, sticky=E, padx=10)
        self.hg_boxlist[hedge_index]['mm'] = IntVar(self.hg_root[hedge_index])
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index]['mm'])
        l.grid(row=2, column=7, sticky=E + W, padx=10)

        l = ttk.Label(self.hg_root[hedge_index], text = '绝对中性')
        l.grid(row=1, column=8, sticky=E, padx=10)
        self.hg_boxlist[hedge_index]['an'] = IntVar(self.hg_root[hedge_index])
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index]['an'])
        l.grid(row=2, column=8, sticky=E + W, padx=10)

        l = ttk.Label(self.hg_root[hedge_index], text = 'M1')
        l.grid(row=3, column=2)
        l = ttk.Label(self.hg_root[hedge_index], text = 'M2')
        l.grid(row=3, column=3)
        l = ttk.Label(self.hg_root[hedge_index], text = 'M3')
        l.grid(row=3, column=4)
        l = ttk.Label(self.hg_root[hedge_index], text = 'Q1')
        l.grid(row=3, column=5)
        l = ttk.Label(self.hg_root[hedge_index], text = 'Q2')
        l.grid(row=3, column=6)
        l = ttk.Label(self.hg_root[hedge_index], text = 'Q3')
        l.grid(row=3, column=7)

        l = ttk.Label(self.hg_root[hedge_index], text = 'IF')
        l.grid(row=4, column=1)
        l = ttk.Label(self.hg_root[hedge_index], text = 'IH')
        l.grid(row=5, column=1)
        l = ttk.Label(self.hg_root[hedge_index], text = '50E')
        l.grid(row=6, column=1)
        l = ttk.Label(self.hg_root[hedge_index], text = '沪E')
        l.grid(row=7, column=1)
        l = ttk.Label(self.hg_root[hedge_index], text = '深E')
        l.grid(row=8, column=1)
        l = ttk.Label(self.hg_root[hedge_index], text = '股指')
        l.grid(row=9, column=1)

        self.hg_boxlist[hedge_index][FutureType.IF] = IntVar(self.hg_root[hedge_index])
        l = Radiobutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][FutureType.IF],value=1)
        l.grid(row=4, column=2, sticky=E + W, padx=10)
        l = Radiobutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][FutureType.IF],value=2)
        l.grid(row=4, column=3, sticky=E + W, padx=10)
        l = Radiobutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][FutureType.IF],value=4)
        l.grid(row=4, column=5, sticky=E + W, padx=10)
        l = Radiobutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][FutureType.IF],value=5)
        l.grid(row=4, column=6, sticky=E + W, padx=10)

        self.hg_boxlist[hedge_index][FutureType.IH] = IntVar(self.hg_root[hedge_index])
        l = Radiobutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][FutureType.IH],value=1)
        l.grid(row=5, column=2, sticky=E + W, padx=10)
        l = Radiobutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][FutureType.IH],value=2)
        l.grid(row=5, column=3, sticky=E + W, padx=10)
        l = Radiobutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][FutureType.IH],value=4)
        l.grid(row=5, column=5, sticky=E + W, padx=10)
        l = Radiobutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][FutureType.IH],value=5)
        l.grid(row=5, column=6, sticky=E + W, padx=10)

        self.hg_boxlist[hedge_index][StockType.etf50] = {Maturity.M1: IntVar(self.hg_root[hedge_index]), Maturity.M2: IntVar(self.hg_root[hedge_index]), Maturity.Q1: IntVar(self.hg_root[hedge_index]), Maturity.Q2: IntVar(self.hg_root[hedge_index])}
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.etf50][Maturity.M1])
        l.grid(row=6, column=2, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.etf50][Maturity.M2])
        l.grid(row=6, column=3, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.etf50][Maturity.Q1])
        l.grid(row=6, column=5, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.etf50][Maturity.Q2])
        l.grid(row=6, column=6, sticky=E + W, padx=10)

        self.hg_boxlist[hedge_index][StockType.h300] = {Maturity.M1: IntVar(self.hg_root[hedge_index]), Maturity.M2: IntVar(self.hg_root[hedge_index]), Maturity.Q1: IntVar(self.hg_root[hedge_index]), Maturity.Q2: IntVar(self.hg_root[hedge_index])}
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.h300][Maturity.M1])
        l.grid(row=7, column=2, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.h300][Maturity.M2])
        l.grid(row=7, column=3, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.h300][Maturity.Q1])
        l.grid(row=7, column=5, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.h300][Maturity.Q2])
        l.grid(row=7, column=6, sticky=E + W, padx=10)

        self.hg_boxlist[hedge_index][StockType.s300] = {Maturity.M1: IntVar(self.hg_root[hedge_index]), Maturity.M2: IntVar(self.hg_root[hedge_index]), Maturity.Q1: IntVar(self.hg_root[hedge_index]), Maturity.Q2: IntVar(self.hg_root[hedge_index])}
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.s300][Maturity.M1])
        l.grid(row=8, column=2, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.s300][Maturity.M2])
        l.grid(row=8, column=3, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.s300][Maturity.Q1])
        l.grid(row=8, column=5, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.s300][Maturity.Q2])
        l.grid(row=8, column=6, sticky=E + W, padx=10)

        self.hg_boxlist[hedge_index][StockType.gz300] = {Maturity.M1: IntVar(self.hg_root[hedge_index]), Maturity.M2: IntVar(self.hg_root[hedge_index]), Maturity.M3: IntVar(self.hg_root[hedge_index]), Maturity.Q1: IntVar(self.hg_root[hedge_index]), Maturity.Q2: IntVar(self.hg_root[hedge_index]), Maturity.Q3: IntVar(self.hg_root[hedge_index])}
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.gz300][Maturity.M1])
        l.grid(row=9, column=2, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.gz300][Maturity.M2])
        l.grid(row=9, column=3, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.gz300][Maturity.M3])
        l.grid(row=9, column=4, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.gz300][Maturity.Q1])
        l.grid(row=9, column=5, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.gz300][Maturity.Q2])
        l.grid(row=9, column=6, sticky=E + W, padx=10)
        l = Checkbutton(self.hg_root[hedge_index],variable=self.hg_boxlist[hedge_index][StockType.gz300][Maturity.Q3])
        l.grid(row=9, column=7, sticky=E + W, padx=10)

        def callback():
            self.stop_hedge(hedge_index)
            root.destroy()
            self.hg_root.pop(hedge_index)
        root.protocol("WM_DELETE_WINDOW", callback)
        root.mainloop()


    def hedge_thread(self, hedge_index: int):

        self.stop_hedge(hedge_index)
        thread = threading.Thread(target = self.hedge, args=(hedge_index, ))
        thread.setDaemon(True)
        thread.start()


    def stop_hedge(self, hedge_index: int):

        if self.hg_state[hedge_index].get() == '对冲中......':
            self.hg_root[hedge_index].after_cancel(self.hg_ongoing[hedge_index])
            self.hg_state[hedge_index].set('对冲')


    def hedge(self, hedge_index: int):

        hedge_strategy = self.hg_boxlist[hedge_index][0][0].get()
        hedge_greeks = self.hg_boxlist[hedge_index][0][1].get()
        hedge_way = self.hg_boxlist[hedge_index][0][3].get()
        try:
            hedge_thred = float(self.hg_boxlist[hedge_index][0][2].get())
        except:
            return

        self.hg_ongoing[hedge_index] = self.hg_root[hedge_index].after(500, self.hedge, hedge_index)

        if self.hg_state[hedge_index].get() == '对冲':
            self.hg_state[hedge_index].set('对冲中......')


        if not trade_period or (localtime.tm_hour == 9 and localtime.tm_min < 33) or (localtime.tm_hour == 11 and localtime.tm_min > 26) or (localtime.tm_hour == 13 and localtime.tm_min < 3):
            return

        if hedge_strategy in list(self.order_for_hg.keys()):
            return

        total_greeks = sum([sum(self.hg_data[hedge_strategy][hedge_greeks][sty].values()) for sty in list(self.hg_data[hedge_strategy][hedge_greeks].keys())])
        if abs(hedge_thred) > abs(total_greeks):
            return

        if not self.hg_p_update_flag[hedge_index]:
            return


        self.hedge_data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '对冲判断前......' + '\n' + 'order for hedge：' + str(self.order_for_hg) + '\n' + 'Ft for hg：' + str(self.Ft_for_hg) + '\n' + 'Opt for hg：' + str(self.Opt_for_hg) + '\n')


        self.order_for_hg[hedge_strategy] = {}
        self.Opt_for_hg_copy = copy.deepcopy(self.Opt_for_hg)


        # 模式
        if_mm = self.hg_boxlist[hedge_index]['mm'].get()
        if_an = self.hg_boxlist[hedge_index]['an'].get()


        # 分配greeks
        def loc(total: float, con: float):
            if total * con <= 0:
                return 0
            if abs(con) <= abs(total):
                return con
            else:
                return total

        if not if_an:
            sign = np.sign(total_greeks)
            not_an_sty = [sty for sty in list(self.hg_data[hedge_strategy]['delta$(万)'].keys()) if sty not in [FutureType.IF, FutureType.IH] and self.hg_data[hedge_strategy]['position']['type'][sty] and sum(self.hg_data[hedge_strategy][hedge_greeks][sty].values()) * sign > 0]
            pre_location = {}
            for sty in not_an_sty:
                loc_greeks = total_greeks * sum(self.hg_data[hedge_strategy][hedge_greeks][sty].values()) / sum([sum(self.hg_data[hedge_strategy][hedge_greeks][_sty].values()) for _sty in not_an_sty])
                pre_location[sty] = {Maturity.M1: loc(loc_greeks, self.hg_data[hedge_strategy]['delta$(万)'][sty][Maturity.M1]), Maturity.M2: 0}
                pre_location[sty][Maturity.M2] = loc(loc_greeks - pre_location[sty][Maturity.M1], self.hg_data[hedge_strategy]['delta$(万)'][sty][Maturity.M2])
                pre_location[sty][Maturity.M1] = loc_greeks - pre_location[sty][Maturity.M2]


        # 分品种，分月份
        for i, sty in enumerate([StockType.etf50, StockType.h300, StockType.s300, StockType.gz300]):

            if if_an and not self.hg_data[hedge_strategy]['position']['type'][sty]:
                continue
            if not if_an and not sty in not_an_sty:
                continue

            for j, mat in enumerate(list(self.hg_data[hedge_strategy][hedge_greeks][sty].keys())):

                if if_an and not self.hg_data[hedge_strategy]['position']['mat'][sty][mat]:
                    continue
                if not if_an and not mat in [Maturity.M1, Maturity.M2]:
                    continue


                if i == 0:
                    future_type = FutureType.IH
                else:
                    future_type = FutureType.IF
                mat_future = data_opt[future_type].matlist[np.argmin(abs(np.array([int(Mat['contract_format'][future_type][mat0]) for mat0 in data_opt[future_type].matlist]) - int(Mat['contract_format'][sty][mat])))]
                if hedge_way == '先期货后合成' and if_mm:
                    if not self.hg_boxlist[hedge_index][future_type].get() == 0:
                        mat_future = Maturity(self.hg_boxlist[hedge_index][future_type].get())


                # 期货对冲
                pre_future = 0
                if (hedge_strategy, sty, mat) in list(self.Ft_for_hg.keys()):
                    pre_future = sum([self.Ft_for_hg[(hedge_strategy, sty, mat)][mat_from_future] * data_opt[future_type].midbidaskspread(mat_from_future) * data_opt[future_type].cm * 1 / 10000 for mat_from_future in list(self.Ft_for_hg[(hedge_strategy, sty, mat)].keys())])

                def of(oo: tuple):
                    opt_c = name_to_data(oo[2][0])
                    used_sty = opt_c.sty
                    used_mat = opt_c.mat
                    position_p = data_opt[used_sty].k_list[used_mat].index(float(oo[2][1][last_C_P(oo[2][1]) : ]))
                    opt_p = data_opt[used_sty].OptionList[used_mat][position_p][1]

                    opt_c._iv = opt_c.iv()
                    opt_p._iv = opt_p.iv()
                    return data_opt[used_sty].S[used_mat] * data_opt[used_sty].cm * (opt_c.delta() - opt_p.delta()) / 10000

                pre_option = 0
                if (hedge_strategy, sty, mat) in list(self.Opt_for_hg_copy.keys()):
                    pre_option = sum([self.Opt_for_hg_copy[(hedge_strategy, sty, mat)][oo] * of(oo) for oo in list(self.Opt_for_hg_copy[(hedge_strategy, sty, mat)].keys())])

                current_greeks = 0
                if if_an:
                    current_greeks = self.hg_data[hedge_strategy][hedge_greeks][sty][mat] + pre_future + pre_option - sum([sum([self.Opt_for_hg_copy[hsm][oo] * of(oo) for oo in list(self.Opt_for_hg_copy[hsm].keys()) if oo[0:2] == (sty, mat)]) for hsm in list(self.Opt_for_hg_copy.keys())])
                else:
                    current_greeks = pre_location[sty][mat]
                future_tool = data_opt[future_type].midbidaskspread(mat_future) * data_opt[future_type].cm * 1 / 10000

                num_future = 0
                if hedge_way == '先期货后合成':
                    num_future = abs(current_greeks) // future_tool * np.sign(current_greeks) # 卖量

                contract_for_future = data_opt[future_type].yc_master_contract[mat_future]


                # 期权对冲
                # 考虑替换
                option_tool = 0
                contract_for_option = ()
                br = False
                for hedge_sty in self.hg_change_list[sty]:
                    if br:
                        break

                    mat_list = [mat, Maturity.M1, Maturity.M2]
                    if if_mm:
                        mat_list = [mm_mat for mm_mat in list(self.hg_boxlist[hedge_index][hedge_sty].keys()) if self.hg_boxlist[hedge_index][hedge_sty][mm_mat].get()]

                    for z, hedge_mat in enumerate(mat_list):
                        if br:
                            break

                        if z == 1 and mat_list[1] == mat_list[0]:
                            break

                        mat_atm = data_opt[hedge_sty].OptionList[hedge_mat][data_opt[hedge_sty].posi[hedge_mat]]
                        mat_x1 = [data_opt[hedge_sty].OptionList[hedge_mat][min(data_opt[hedge_sty].posi[hedge_mat] + 1, len(data_opt[hedge_sty].k_list[hedge_mat]) - 1)][0], data_opt[hedge_sty].OptionList[hedge_mat][max(data_opt[hedge_sty].posi[hedge_mat] - 1, 0)][1]]
                        try_k_list = [mat_atm, [mat_atm[0], mat_x1[1]], [mat_atm[1], mat_x1[0]], mat_x1]

                        for hedge_k in try_k_list:
                            # 未熔断 and 流动性好
                            if [True, True] == [True for i in range(2) if hedge_k[i].cb == False and '' not in [hedge_k[i].ask, hedge_k[i].bid] and 'A' not in hedge_k[i].yc_master_contract and hedge_k[i].ask - hedge_k[i].bid < data_opt[hedge_sty].mc * data_opt[hedge_sty].tick_limit and hedge_k[i].P > data_opt[hedge_sty].p_limit]:
                                hedge_k[0]._iv = hedge_k[0].iv()
                                hedge_k[1]._iv = hedge_k[1].iv()
                                greeks_c = data_opt[hedge_sty].S[hedge_mat] * data_opt[hedge_sty].cm * hedge_k[0].delta() / 10000
                                greeks_p = data_opt[hedge_sty].S[hedge_mat] * data_opt[hedge_sty].cm * hedge_k[1].delta() / 10000
                                option_tool = greeks_c - greeks_p
                                contract_for_option = (hedge_k[0].yc_master_contract, hedge_k[1].yc_master_contract)
                                br = True
                                option_chosen = (hedge_sty, hedge_mat, contract_for_option)
                                break

                num_opt = 0
                if not option_tool == 0:
                    num_opt = np.round(abs(current_greeks - num_future * future_tool) / option_tool, 0) * np.sign(current_greeks - num_future * future_tool)


                # 合约名初始值已被覆盖
                if contract_for_future == '' or '' in contract_for_option:
                    return


                # for future
                if not num_future == 0:
                    if contract_for_future not in list(self.order_for_hg[hedge_strategy].keys()):
                        self.order_for_hg[hedge_strategy][contract_for_future] = 0
                    self.order_for_hg[hedge_strategy][contract_for_future] -= num_future

                    # futures for hegde written in Ft_for_hg
                    if (hedge_strategy, sty, mat) not in list(self.Ft_for_hg.keys()):
                        self.Ft_for_hg[(hedge_strategy, sty, mat)] = {}
                    if mat_future not in list(self.Ft_for_hg[(hedge_strategy, sty, mat)].keys()):
                        self.Ft_for_hg[(hedge_strategy, sty, mat)][mat_future] = 0 # 持仓
                    self.Ft_for_hg[(hedge_strategy, sty, mat)][mat_future] -= num_future

                # for option
                if not num_opt == 0:
                    for z, ctr in enumerate(contract_for_option):
                        if ctr not in list(self.order_for_hg[hedge_strategy].keys()):
                            self.order_for_hg[hedge_strategy][ctr] = 0
                        if z == 0:
                            self.order_for_hg[hedge_strategy][ctr] -= num_opt
                        else:
                            self.order_for_hg[hedge_strategy][ctr] += num_opt

                    # options for hegde written in Opt_for_hg
                    if if_an and not (sty, mat) == option_chosen[:2]:
                        if (hedge_strategy, sty, mat) not in list(self.Opt_for_hg.keys()):
                            self.Opt_for_hg[(hedge_strategy, sty, mat)] = {}
                        if option_chosen not in list(self.Opt_for_hg[(hedge_strategy, sty, mat)].keys()):
                            self.Opt_for_hg[(hedge_strategy, sty, mat)][option_chosen] = 0 # 持仓 for call
                        self.Opt_for_hg[(hedge_strategy, sty, mat)][option_chosen] -= num_opt


        self.hedge_data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '对冲判断后......' + '\n' + 'order for hedge：' + hedge_strategy + str(self.order_for_hg[hedge_strategy]) + '\n' + 'Ft for hg：' + str(self.Ft_for_hg) + '\n' + 'Opt for hg：' + str(self.Opt_for_hg) + '\n')
        self.hedge_data_txt.flush()


        # 下单
        for target in list(self.order_for_hg[hedge_strategy].keys()):
            num = self.order_for_hg[hedge_strategy][target]
            self.order_api(target, 'HIT', num, hedge_strategy, 'hedge')

        self.hg_p_update_list[hedge_index] = list(self.order_for_hg[hedge_strategy].keys())

        if self.order_for_hg[hedge_strategy] == {}:
            self.order_for_hg.pop(hedge_strategy)


    ##############################################################################################################
    def open_mp_ui(self):

        if self.mp_root_flag:
            return
        self.init_modify_param_ui()


    def init_modify_param_ui(self):

        self.mp_boxlist = {0:[]}
        strategies = list(self.label_var.keys())
        if strategies == []:
            strategies = ['']
        contract = ['']

        root = Toplevel()
        root.title('参数修改')
        self.main_root_position = self.main_root.winfo_geometry()
        index = [i for i, x in enumerate(self.main_root_position) if x == '+']
        root.geometry("%dx%d+%d+%d" % (680, 100, int(self.main_root_position[index[0] + 1 : index[1]]), int(self.main_root_position[index[1] + 1 :]) + 100))
        canvas = Canvas(root, borderwidth=0)
        frame = Frame(canvas)
        self.mp_root = frame
        self.mp_root_flag = True
        vsb = Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((4, 4), window=frame, anchor="nw")

        def onFrameConfigure(canvas):
            '''Reset the scroll region to encompass the inner frame'''
            canvas.configure(scrollregion=canvas.bbox("all"))

        frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))


        stg = StringVar()
        stgChosen = ttk.Combobox(self.mp_root, width=10, textvariable=stg)
        stgChosen['values'] = strategies
        stgChosen.grid(column=1, row=1, padx=5)
        stgChosen.current(0)
        self.mp_boxlist[0].append(stgChosen)

        def func(*args):
            stg_name = stgChosen.get()
            contract = []
            contract += sorted(list(self.label_var[stg_name].keys()))
            ctChosen['values'] = contract

        stgChosen.bind("<<ComboboxSelected>>", func)


        ct = StringVar()
        ctChosen = ttk.Combobox(self.mp_root, width=30, textvariable=ct)
        ctChosen['values'] = contract
        ctChosen.grid(column=2, row=1, padx=5)
        ctChosen.current(0)
        self.mp_boxlist[0].append(ctChosen)


        param = StringVar()
        paramChosen = ttk.Combobox(self.mp_root, width=10, textvariable=param)
        paramChosen['values'] = ['持仓数', '均价', '平仓损益', '当日最大总收益']
        paramChosen.grid(column=3, row=1, padx=5)
        paramChosen.current(0)
        self.mp_boxlist[0].append(paramChosen)


        dt = StringVar()
        dtEntry = ttk.Entry(self.mp_root, width=10, textvariable=dt)
        dtEntry.grid(column=4, row=1, padx=5)
        self.mp_boxlist[0].append(dtEntry)


        b = Button(self.mp_root, text="更新", command=self.modify_param, width=10)
        b.grid(row=1, column=5, sticky=E, padx=5, pady=10)

        def callback():
            root.destroy()
            self.mp_root_flag = False
        root.protocol("WM_DELETE_WINDOW", callback)
        root.mainloop()


    def modify_param(self):

        try: 
            float(self.mp_boxlist[0][3].get())
        except: 
            return

        if self.mp_boxlist[0][2].get() == '当日最大总收益':
                self.max_total_profit[self.mp_boxlist[0][0].get()].set('{:g}'.format(float(self.mp_boxlist[0][3].get())))
        else:
            if self.mp_boxlist[0][0].get() in list(self.label_var.keys()):
                if self.mp_boxlist[0][1].get() in list(self.label_var[self.mp_boxlist[0][0].get()].keys()):
                    self.label_var[self.mp_boxlist[0][0].get()][self.mp_boxlist[0][1].get()][self.mp_boxlist[0][2].get()].set('{:g}'.format(float(self.mp_boxlist[0][3].get())))


MY = monitor_yield()
data_opt: dict = {}

def OnRealTimeQuote(Quote): # quote thread
    MY.p_update(Quote)

def OnGreeks(greek):
    pass

def OnGetAccount(account):
    print(account["BrokerID"])

def OnexeReport(report): # trade thread
    MY.check_buy_sell(report)
    return None

def trade_sub_th(obj,sub_port,filter = ""):
    socket_sub = obj.context.socket(zmq.SUB)
    #socket_sub.RCVTIMEO=5000
    socket_sub.connect("tcp://127.0.0.1:%s" % sub_port)
    socket_sub.setsockopt_string(zmq.SUBSCRIBE,filter)
    while True:

        if exit_signal:
            return

        message =  socket_sub.recv()
        if message:
            message = json.loads(message[:-1])
            if(message["DataType"] == "PING"):
                g_TradeZMQ.TradePong(g_TradeSession)
            elif(message["DataType"] == "ACCOUNTS"):
                for i in message["Accounts"]:
                    OnGetAccount(i)
            elif(message["DataType"] == "EXECUTIONREPORT"):
                OnexeReport(message["Report"])

def quote_sub_th(obj,q_data,filter = ""):
    socket_sub = obj.context.socket(zmq.SUB)
    socket_sub.connect("tcp://127.0.0.1:%s" % q_data["SubPort"])
    socket_sub.setsockopt_string(zmq.SUBSCRIBE,filter)
    while(True):

        if exit_signal:
            return

        message = (socket_sub.recv()[:-1]).decode("utf-8")
        index =  re.search(":",message).span()[1]  # filter
        symbol = message[:index-1]

        message = message[index:]
        message = json.loads(message)

        #for message in messages:
        if(message["DataType"] == "PING"):
            g_QuoteZMQ.QuotePong(g_QuoteSession)
        elif(message["DataType"]=="REALTIME"):
            OnRealTimeQuote(message["Quote"])
        elif(message["DataType"]=="GREEKS"):
            OnGreeks(message["Quote"])
        elif(message["DataType"]=="1K"):
            strQryIndex = ""
            while(True):
                History_obj = {
                    "Symbol": symbol,
                    "SubDataType":"1K",
                    "StartTime" : message["StartTime"],
                    "EndTime" : message["EndTime"],
                    "QryIndex" : strQryIndex
                }
                s_history = obj.get_history(q_data["SessionKey"],History_obj)
                historyData = s_history["HisData"]
                if len(historyData) == 0:
                    break

                last = ""
                for data in historyData:
                    last = data
                    print("Time:%s, Volume:%s, QryIndex:%s" % (data["Time"], data["Volume"], data["QryIndex"]))

                strQryIndex = last["QryIndex"]

    return


# sub all options for data
def redundant_zero(string: str):
    string = list(string)
    num = len(string) - 1
    while string[num] == '0':
        string.pop(num)
        num -= 1

    if string[-1] == '.':
        string.pop(num)
    return ''.join(string)

def last_C_P(string: str):
    num = len(string) - 1
    while (string[num] != 'C' and string[num] != 'P'):
        num -= 1
    return num + 2

def name_to_data(yc_master_contract: str):
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

def sub_all_options():
    global QuoteID
    QuoteID = []
    data = g_QuoteZMQ.QueryAllInstrumentInfo(g_QuoteSession, "Options")
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


    data = g_QuoteZMQ.QueryAllInstrumentInfo(g_QuoteSession, "Future")
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
        data_opt[sty] = OptData(sty)
        data_opt[sty].subscribe_init(Maturity.M1)
        data_opt[sty].subscribe_init(Maturity.M2)
        data_opt[sty].subscribe_init(Maturity.Q1)
        data_opt[sty].subscribe_init(Maturity.Q2)
        if sty == StockType.gz300:
            data_opt[sty].subscribe_init(Maturity.M3)
            data_opt[sty].subscribe_init(Maturity.Q3)
    for fty in [FutureType.IF, FutureType.IH]:
        data_opt[fty] = FutureData(fty)

    quote_obj = {"Symbol":"ok", "SubDataType":"REALTIME"}
    for i in QuoteID:
        quote_obj["Symbol"] = i
        g_QuoteZMQ.subquote(g_QuoteSession,quote_obj)


def main():

    global g_TradeZMQ
    global g_QuoteZMQ
    global g_TradeSession
    global g_QuoteSession

    g_TradeZMQ = tcore_zmq()
    g_QuoteZMQ = tcore_zmq()

    # 封装 cd C:\Users\pengs\Desktop\profit
    # 封装 pyinstaller -F profit.py -w -i ./pictures/logo.ico

    t_data = g_TradeZMQ.trade_connect("51848") # 公版
    q_data = g_QuoteZMQ.quote_connect("51878")

    #t_data = g_TradeZMQ.trade_connect("51492") # 方正2
    #q_data = g_QuoteZMQ.quote_connect("51522")


    if t_data["Success"] != "OK":
        print("[quote]connection failed")
        return

    if t_data["Success"] != "OK":
        print("[trade]connection failed")
        return

    g_TradeSession = t_data["SessionKey"]
    g_QuoteSession = q_data["SessionKey"]

    sub_all_options()

    t1 = threading.Thread(target = trade_sub_th,args=(g_TradeZMQ,t_data["SubPort"],))
    t1.start()

    #quote
    t2 = threading.Thread(target = quote_sub_th,args=(g_QuoteZMQ,q_data,))
    t2.start()

    while not t2.is_alive():
        pass


if __name__ == '__main__':
    main()
    MY.init_profit_ui()