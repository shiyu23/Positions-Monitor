from tkinter import *
from tkinter import ttk
import threading
import math
import time

from module.base.pf_enum import *
from ..base import pf_global as gl
from ..base import pf_order as od


class build:

    def __init__(self, index: int):

        self.index = index
        self.vega = {'long': 0, 'short': 0}

        # 记录
        localtime = gl.get_value('localtime')
        self.data_txt = open(f'./log/build data {localtime.tm_year}-{localtime.tm_mon}-{localtime.tm_mday}.txt', 'a')


    def open_build_ui(self, geometry):
        self.init_build_ui(geometry)


    def init_build_ui(self, geometry):

        all_strategies = []
        with open('./strategies.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for strategy in lines:
                all_strategies.append(strategy.replace('\n', ''))

        if all_strategies == []:
            all_strategies = ['']

        root = Toplevel()
        root.title('建仓')
        index = [i for i, x in enumerate(geometry) if x == '+']
        root.geometry("%dx%d+%d+%d" % (550, 180, int(geometry[index[0] + 1 : index[1]]), int(geometry[index[1] + 1 :]) + 500))
        canvas = Canvas(root, borderwidth=0)
        frame = Frame(canvas)
        self.root = frame
        self.boxlist = {0:[], 2:[], 3:[]}
        vsb = Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((4, 4), window=frame, anchor="nw")

        def onFrameConfigure(canvas):
            '''Reset the scroll region to encompass the inner frame'''
            canvas.configure(scrollregion=canvas.bbox("all"))

        frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))


        lb_ty = ttk.Label(self.root, text = '跨品种')
        lb_ty.grid(row=1, column=1)
        ty = StringVar()
        tyChosen = ttk.Combobox(self.root, width=10, textvariable=ty)
        tyChosen['values'] = ['300'] #, '350']
        tyChosen.grid(column=1, row=2, padx=5)
        tyChosen.current(0)
        self.boxlist[0].append(tyChosen)

        def func(*args):
            ty_name = tyChosen.get()
            strategies = []
            for i in all_strategies:
                if ty_name in i:
                    strategies.append(i)
            stgChosen['values'] = strategies

        tyChosen.bind("<<ComboboxSelected>>", func)

        lb_mat = ttk.Label(self.root, text = '到期时间')
        lb_mat.grid(row=1, column=2)
        mat = StringVar()
        matChosen = ttk.Combobox(self.root, width=10, textvariable=mat)
        Mat = gl.get_value('Mat')
        if Mat['contract_format'][StockType.gz300][Maturity.M3] == Mat['contract_format'][StockType.h300][Maturity.Q1]:
            matChosen['values'] = list(Mat['contract_format'][StockType.gz300].values())[:3]
        else:
            matChosen['values'] = list(Mat['contract_format'][StockType.gz300].values())[:2]
        matChosen.grid(column=2, row=2, padx=5)
        matChosen.current(0)
        self.boxlist[0].append(matChosen)

        lb_stg = ttk.Label(self.root, text = '策略')
        lb_stg.grid(row=1, column=3)
        stg = StringVar()
        stgChosen = ttk.Combobox(self.root, width=10, textvariable=stg)
        stgChosen['values'] = [i for i in all_strategies if '300' in i]
        stgChosen.grid(column=3, row=2, padx=5)
        stgChosen.current(0)
        self.boxlist[0].append(stgChosen)

        self.state = StringVar()
        self.state.set('建仓')
        b = Button(self.root, textvariable=self.state, command=self.build_thread, width=10)
        b.grid(row=2, column=4, sticky=E, padx=5, pady=10)

        b = Button(self.root, text='停止建仓', command=self.stop_build, width=10)
        b.grid(row=2, column=5, sticky=E, padx=5, pady=10)


        lb = ttk.Label(self.root, text = '前跨')
        lb.grid(row=3, column=4)

        lb_thred_u = ttk.Label(self.root, text = 'VIX上阈值%')
        lb_thred_u.grid(row=4, column=1)
        thred_u = StringVar()
        thredEntry_u = ttk.Entry(self.root, width=10, textvariable=thred_u)
        thredEntry_u.grid(column=2, row=4, padx=5)
        self.boxlist[2].append(thredEntry_u)

        lb_thred_l = ttk.Label(self.root, text = 'VIX下阈值%')
        lb_thred_l.grid(row=5, column=1)
        thred_l = StringVar()
        thredEntry_l = ttk.Entry(self.root, width=10, textvariable=thred_l)
        thredEntry_l.grid(column=2, row=5, padx=5)
        self.boxlist[3].append(thredEntry_l)

        lb = ttk.Label(self.root, text = '建仓达vega')
        lb.grid(row=4, column=3)
        num = StringVar()
        numEntry = ttk.Entry(self.root, width=10, textvariable=num)
        numEntry.grid(column=4, row=4, padx=5)
        self.boxlist[2].append(numEntry)

        lb = ttk.Label(self.root, text = '每组数量')
        lb.grid(row=5, column=3)
        num = StringVar()
        numEntry = ttk.Entry(self.root, width=10, textvariable=num)
        numEntry.grid(column=4, row=5, padx=5)
        self.boxlist[3].append(numEntry)

        def callback():
            self.stop_build()
            root.destroy()
            gl.global_var['bd_index'].pop(self.index)
            self.data_txt.close()
        root.protocol("WM_DELETE_WINDOW", callback)
        root.mainloop()


    def build_thread(self):

        self.stop_build()
        thread = threading.Thread(target = self.build)
        thread.setDaemon(True)
        thread.start()


    def stop_build(self):

        if self.state.get() == '建仓中......':
            self.root.after_cancel(self.ongoing)
            self.state.set('建仓')
            for tp in [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (3, 0), (3, 1)]:
                self.boxlist[tp[0]][tp[1]].configure(state='normal')


    def build(self):

        build_ty = self.boxlist[0][0].get()
        build_mat = self.boxlist[0][1].get()
        build_strategy = self.boxlist[0][2].get()

        try:

            build_upper = float(self.boxlist[2][0].get()) / 100
            build_lower = float(self.boxlist[3][0].get()) / 100
            target_vega = float(self.boxlist[2][1].get())
            fore = abs(int(self.boxlist[3][1].get()))

        except:
            return

        if build_strategy == '':
            return

        if build_upper <= build_lower:
            return

        self.ongoing = self.root.after(500, self.build)

        if self.state.get() == '建仓':
            self.state.set('建仓中......')
            for tp in [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (3, 0), (3, 1)]:
                self.boxlist[tp[0]][tp[1]].configure(state='disabled')

        trade_period = gl.get_value('trade_period')
        localtime = gl.get_value('localtime')
        if not trade_period or (localtime.tm_hour == 9 and localtime.tm_min < 35) or (localtime.tm_hour == 11 and localtime.tm_min > 24) or (localtime.tm_hour == 13 and localtime.tm_min < 5):
            return

        order = gl.get_value('bd_order')['order']
        if build_strategy in list(order.keys()):

            # 判断上轮下单是否成交完成
            if [order[build_strategy][target]['num'] for target in list(order[build_strategy].keys())] == [0] * len(order[build_strategy]):
                order.pop(build_strategy)
                return

            # 判断是否需要追中价
            current_time = time.time()
            target_list = list(order[build_strategy].keys())
            for i, target in enumerate(target_list):
                for rp in list(order[build_strategy][target]['rp'].keys()):
                    num = order[build_strategy][target]['rp'][rp]['num']

                    if not num == 0 and current_time - order[build_strategy][target]['rp'][rp]['ot'] > 3:

                        if not order[build_strategy][target]['rp'][rp]['cancel_order']:
                            od.order_cancel(rp)
                            order[build_strategy][target]['rp'][rp]['cancel_order'] = True

                        if order[build_strategy][target]['rp'][rp]['canceled']:

                            if '.C.' in target:
                                couple_target = [t for t in target_list if '.C.' in t]
                            elif '.P.' in target:
                                couple_target = [t for t in target_list if '.P.' in t]

                            if 0 in [order[build_strategy][ct]['num'] for ct in couple_target]:
                                od.order_api(target, 'HIT', num, build_strategy, 'build')
                            else:
                                od.order_api(target, 'MID', num, build_strategy, 'build')
                            order[build_strategy][target]['rp'].pop(rp)

            return

        order[build_strategy] = {}


        self.data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '建仓判断前......' + '\n' + 'order for build：' + str(order) + '\n')


        data_opt = gl.get_value('data_opt')
        mat_gz300 = data_opt[StockType.gz300]._2005_to_Mat[build_mat]
        mat_h300 = data_opt[StockType.h300]._2005_to_Mat[build_mat]
        vix_dict_gz300 = data_opt[StockType.gz300].vix(mat_gz300)
        vix_dict_h300 = data_opt[StockType.h300].vix(mat_h300)

        direction = None
        if build_ty == '300' and vix_dict_h300['cb'] == False:
            if vix_dict_gz300['vix'] - vix_dict_h300['vix'] >= build_upper:
                direction = -1
            elif vix_dict_gz300['vix'] - vix_dict_h300['vix'] <= build_lower:
                direction = 1
            else:
                order.pop(build_strategy)
                return
        else:
            order.pop(build_strategy)
            return

        gz300 = data_opt[StockType.gz300].OptionList[mat_gz300][data_opt[StockType.gz300].posi[mat_gz300]]
        h300 = data_opt[StockType.h300].OptionList[mat_h300][data_opt[StockType.h300].posi[mat_h300]]

        if '' in [gz300[0].yc_master_contract, gz300[1].yc_master_contract, h300[0].yc_master_contract, h300[1].yc_master_contract]:
            order.pop(build_strategy)
            return

        if direction == 1 and self.vega['long'] > target_vega:
            order.pop(build_strategy)
            return

        if direction == -1 and self.vega['short'] < -1 * target_vega:
            order.pop(build_strategy)
            return

        # vega中性
        gz300_straddle_vega = direction * 100 * (gz300[0].vega() + gz300[1].vega()) * 0.01
        h300_straddle_vega = direction * 10000 * (h300[0].vega() + h300[1].vega()) * 0.01
        hind = round(fore * gz300_straddle_vega / h300_straddle_vega, 0)

        # 后跨合成期货 调 整体中性
        gz300_straddle_delta = fore * direction * data_opt[StockType.gz300].S[mat_gz300] * 100 * (gz300[0].delta() + gz300[1].delta()) / 10000
        h300_straddle_delta = -1 * hind * direction * data_opt[StockType.h300].S[mat_h300] * 10000 * (h300[0].delta() + h300[1].delta()) / 10000
        delta_per_grp = gz300_straddle_delta + h300_straddle_delta
        h300_synfut_delta = data_opt[StockType.h300].S[mat_h300] * 10000 * (h300[0].delta() - h300[1].delta()) / 10000
        num_h300_synfut = round(delta_per_grp / h300_synfut_delta, 0)

        # 打单边 调 单品种中性
        stg_greeks = gl.get_value('stg_greeks')
        order[build_strategy] = {gz300[0].yc_master_contract: {'num': fore * direction}, h300[0].yc_master_contract: {'num': -1 * hind * direction - num_h300_synfut}, gz300[1].yc_master_contract: {'num': fore * direction}, h300[1].yc_master_contract: {'num': -1 * hind * direction + num_h300_synfut}}
        gz300_vega = fore * gz300_straddle_vega
        if build_strategy in stg_greeks.keys():
            gz300_greeks = sum(stg_greeks[build_strategy]['delta$(万)'][StockType.gz300].values())
            gz300_delta_C = fore * direction * data_opt[StockType.gz300].S[mat_gz300] * 100 * gz300[0].delta() / 10000
            gz300_delta_P = fore * direction * data_opt[StockType.gz300].S[mat_gz300] * 100 * gz300[1].delta() / 10000
            if (gz300_greeks < 0 and gz300_delta_C > 0 and gz300_greeks < -1 * gz300_delta_C) or (gz300_greeks > 0 and gz300_delta_C < 0 and gz300_greeks > -1 * gz300_delta_C):
                order[build_strategy] = {gz300[0].yc_master_contract: {'num': fore * direction}, h300[0].yc_master_contract: {'num': -1 * hind * direction}}
                gz300_vega = fore * direction * gz300[0].vega() * 100 * 0.01
            elif (gz300_greeks < 0 and gz300_delta_P > 0 and gz300_greeks < -1 * gz300_delta_P) or (gz300_greeks > 0 and gz300_delta_P < 0 and gz300_greeks > -1 * gz300_delta_P):
                order[build_strategy] = {gz300[1].yc_master_contract: {'num': fore * direction}, h300[1].yc_master_contract: {'num': -1 * hind * direction}}
                gz300_vega = fore * direction * gz300[1].vega() * 100 * 0.01

        d = 'long' if direction == 1 else 'short'
        self.vega[d] += gz300_vega


        self.data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '建仓判断后......' + '\n' + 'order for build：' + build_strategy + str(order[build_strategy]) + '\n')
        self.data_txt.flush()

        # 下单
        for target in list(order[build_strategy].keys()):
            num = order[build_strategy][target]['num']
            od.order_api(target, 'MID', num, build_strategy, 'build')
            order[build_strategy][target]['rp'] = {}