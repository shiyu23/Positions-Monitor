from scipy.interpolate import CubicSpline
import numpy as np
import calendar
import math

from . import pf_global as gl
from .pf_enum import *


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
            self.p_limit = 10
            self.tick_limit = 15
            self.matlist = [Maturity.M1, Maturity.M2, Maturity.M3, Maturity.Q1, Maturity.Q2, Maturity.Q3]
        elif sty in [StockType.etf50, StockType.h300, StockType.s300]:
            self.cm = 10000
            self.mc = 0.0001
            self.p_limit = 0.003
            self.tick_limit = 10
            self.matlist = [Maturity.M1, Maturity.M2, Maturity.Q1, Maturity.Q2]
        for mat in self.matlist:
            self.S[mat] = ''; self.k0[mat] = ''; self.posi[mat] = ''
        self.k_list = {}
        self.getMat()

    def getMat(self):
        Mat = gl.get_value('Mat')
        holiday = gl.get_value('holiday')
        localtime = gl.get_value('localtime')

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
        QuoteID = gl.get_value('QuoteID')

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
                QuoteID_addin_C_K.append(float(id[gl.last_C_P(id):]))
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

    def vix(self, mat: Maturity): # 计算vix
        k_list_copy = self.k_list[mat].copy()
        k1 = k_list_copy[np.argmin(abs(np.array(k_list_copy) - self.S[mat]))]
        k_list_copy.remove(k1)
        k2 = k_list_copy[np.argmin(abs(np.array(k_list_copy) - self.S[mat]))]
        k_list_copy.remove(k2)
        k3 = k_list_copy[np.argmin(abs(np.array(k_list_copy) - self.S[mat]))]
        k_list_copy.remove(k3)

        [k1, k2, k3] = sorted([k1, k2, k3])

        opt1 = self.OptionList[mat][self.k_list[mat].index(k1)]
        opt2 = self.OptionList[mat][self.k_list[mat].index(k2)]
        opt3 = self.OptionList[mat][self.k_list[mat].index(k3)]
        x = [opt1[0].K, opt2[0].K, opt3[0].K]
        y = [(opt1[0].iv() + opt1[1].iv()) / 2, (opt2[0].iv() + opt2[1].iv()) / 2, (opt3[0].iv() + opt3[1].iv()) / 2]
        cs = CubicSpline(x, y)
        return {'vix': cs(self.S[mat]), 'cb': opt1[0].cb or opt1[1].cb or opt2[0].cb or opt2[1].cb or opt3[0].cb or opt3[1].cb}


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
        Mat = gl.get_value('Mat')
        holiday = gl.get_value('holiday')
        localtime = gl.get_value('localtime')

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