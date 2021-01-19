from tkinter import *
from tkinter import ttk
import threading
import numpy as np
import time
import copy

from module.base.pf_enum import *
from ..base import pf_global as gl
from ..base import pf_order as od


class hedge:

    def __init__(self, index: int):

        self.index = index
        self.p_update_list = []
        self.p_update_flag = True
        self.far_from_bs_update = True
        self.change_list = {StockType.etf50: [StockType.etf50, StockType.h300, StockType.s300, StockType.gz300], StockType.h300: [StockType.h300, StockType.s300, StockType.gz300], StockType.s300: [StockType.s300, StockType.h300, StockType.gz300], StockType.gz300: [StockType.gz300]}

        # 记录
        localtime = gl.get_value('localtime')
        self.data_txt = open(f'./log/hedge data {localtime.tm_year}-{localtime.tm_mon}-{localtime.tm_mday}.txt', 'a')


    def open_hedge_ui(self, strategies, geometry):
        self.init_hedge_ui(strategies, geometry)


    def init_hedge_ui(self, strategies: list, geometry):

        if strategies == []:
            strategies = ['']

        root = Toplevel()
        root.title('对冲')
        index = [i for i, x in enumerate(geometry) if x == '+']
        root.geometry("%dx%d+%d+%d" % (750, 300, int(geometry[index[0] + 1 : index[1]]), int(geometry[index[1] + 1 :]) + 500))
        canvas = Canvas(root, borderwidth=0)
        frame = Frame(canvas)
        self.root = frame
        self.boxlist = {0:[]}
        vsb = Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((4, 4), window=frame, anchor="nw")

        def onFrameConfigure(canvas):
            '''Reset the scroll region to encompass the inner frame'''
            canvas.configure(scrollregion=canvas.bbox("all"))

        frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))


        lb_stg = ttk.Label(self.root, text = '策略')
        lb_stg.grid(row=1, column=1)
        stg = StringVar()
        stgChosen = ttk.Combobox(self.root, width=10, textvariable=stg)
        stgChosen['values'] = strategies
        stgChosen.grid(column=1, row=2, padx=5)
        stgChosen.current(0)
        self.boxlist[0].append(stgChosen)

        lb_grk = ttk.Label(self.root, text = 'Greeks')
        lb_grk.grid(row=1, column=2)
        grk = StringVar()
        grkChosen = ttk.Combobox(self.root, width=10, textvariable=grk)
        grkChosen['values'] = ['delta$(万)']
        grkChosen.grid(column=2, row=2, padx=5)
        grkChosen.current(0)
        self.boxlist[0].append(grkChosen)

        lb_thred = ttk.Label(self.root, text = '阈值（万）')
        lb_thred.grid(row=1, column=3)
        thred = StringVar()
        thredEntry = ttk.Entry(self.root, width=10, textvariable=thred)
        thredEntry.grid(column=3, row=2, padx=5)
        self.boxlist[0].append(thredEntry)

        lb_way = ttk.Label(self.root, text = '方式')
        lb_way.grid(row=1, column=4)
        way = StringVar()
        wayChosen = ttk.Combobox(self.root, width=10, textvariable=way)
        wayChosen['values'] = ['合成', '先期货后合成']
        wayChosen.grid(column=4, row=2, padx=5)
        wayChosen.current(0)
        self.boxlist[0].append(wayChosen)


        self.state = StringVar()
        self.state.set('对冲')
        b = Button(self.root, textvariable=self.state, command=self.hedge_thread, width=10)
        b.grid(row=2, column=5, sticky=E, padx=5, pady=10)

        b = Button(self.root, text='停止对冲', command=self.stop_hedge, width=10)
        b.grid(row=2, column=6, sticky=E, padx=5, pady=10)


        # 手动板
        l = ttk.Label(self.root, text = '手动模式')
        l.grid(row=1, column=7, sticky=E, padx=10)
        self.boxlist['mm'] = IntVar(self.root)
        l = Checkbutton(self.root,variable=self.boxlist['mm'])
        l.grid(row=2, column=7, sticky=E + W, padx=10)

        l = ttk.Label(self.root, text = '绝对中性')
        l.grid(row=1, column=8, sticky=E, padx=10)
        self.boxlist['an'] = IntVar(self.root)
        l = Checkbutton(self.root,variable=self.boxlist['an'])
        l.grid(row=2, column=8, sticky=E + W, padx=10)

        l = ttk.Label(self.root, text = 'M1')
        l.grid(row=3, column=2)
        l = ttk.Label(self.root, text = 'M2')
        l.grid(row=3, column=3)
        l = ttk.Label(self.root, text = 'M3')
        l.grid(row=3, column=4)
        l = ttk.Label(self.root, text = 'Q1')
        l.grid(row=3, column=5)
        l = ttk.Label(self.root, text = 'Q2')
        l.grid(row=3, column=6)
        l = ttk.Label(self.root, text = 'Q3')
        l.grid(row=3, column=7)

        l = ttk.Label(self.root, text = 'IF')
        l.grid(row=4, column=1)
        l = ttk.Label(self.root, text = 'IH')
        l.grid(row=5, column=1)
        l = ttk.Label(self.root, text = '50E')
        l.grid(row=6, column=1)
        l = ttk.Label(self.root, text = '沪E')
        l.grid(row=7, column=1)
        l = ttk.Label(self.root, text = '深E')
        l.grid(row=8, column=1)
        l = ttk.Label(self.root, text = '股指')
        l.grid(row=9, column=1)

        self.boxlist[FutureType.IF] = IntVar(self.root)
        l = Radiobutton(self.root,variable=self.boxlist[FutureType.IF],value=1)
        l.grid(row=4, column=2, sticky=E + W, padx=10)
        l = Radiobutton(self.root,variable=self.boxlist[FutureType.IF],value=2)
        l.grid(row=4, column=3, sticky=E + W, padx=10)
        l = Radiobutton(self.root,variable=self.boxlist[FutureType.IF],value=4)
        l.grid(row=4, column=5, sticky=E + W, padx=10)
        l = Radiobutton(self.root,variable=self.boxlist[FutureType.IF],value=5)
        l.grid(row=4, column=6, sticky=E + W, padx=10)

        self.boxlist[FutureType.IH] = IntVar(self.root)
        l = Radiobutton(self.root,variable=self.boxlist[FutureType.IH],value=1)
        l.grid(row=5, column=2, sticky=E + W, padx=10)
        l = Radiobutton(self.root,variable=self.boxlist[FutureType.IH],value=2)
        l.grid(row=5, column=3, sticky=E + W, padx=10)
        l = Radiobutton(self.root,variable=self.boxlist[FutureType.IH],value=4)
        l.grid(row=5, column=5, sticky=E + W, padx=10)
        l = Radiobutton(self.root,variable=self.boxlist[FutureType.IH],value=5)
        l.grid(row=5, column=6, sticky=E + W, padx=10)

        self.boxlist[StockType.etf50] = {Maturity.M1: IntVar(self.root), Maturity.M2: IntVar(self.root), Maturity.Q1: IntVar(self.root), Maturity.Q2: IntVar(self.root)}
        l = Checkbutton(self.root,variable=self.boxlist[StockType.etf50][Maturity.M1])
        l.grid(row=6, column=2, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.etf50][Maturity.M2])
        l.grid(row=6, column=3, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.etf50][Maturity.Q1])
        l.grid(row=6, column=5, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.etf50][Maturity.Q2])
        l.grid(row=6, column=6, sticky=E + W, padx=10)

        self.boxlist[StockType.h300] = {Maturity.M1: IntVar(self.root), Maturity.M2: IntVar(self.root), Maturity.Q1: IntVar(self.root), Maturity.Q2: IntVar(self.root)}
        l = Checkbutton(self.root,variable=self.boxlist[StockType.h300][Maturity.M1])
        l.grid(row=7, column=2, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.h300][Maturity.M2])
        l.grid(row=7, column=3, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.h300][Maturity.Q1])
        l.grid(row=7, column=5, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.h300][Maturity.Q2])
        l.grid(row=7, column=6, sticky=E + W, padx=10)

        self.boxlist[StockType.s300] = {Maturity.M1: IntVar(self.root), Maturity.M2: IntVar(self.root), Maturity.Q1: IntVar(self.root), Maturity.Q2: IntVar(self.root)}
        l = Checkbutton(self.root,variable=self.boxlist[StockType.s300][Maturity.M1])
        l.grid(row=8, column=2, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.s300][Maturity.M2])
        l.grid(row=8, column=3, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.s300][Maturity.Q1])
        l.grid(row=8, column=5, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.s300][Maturity.Q2])
        l.grid(row=8, column=6, sticky=E + W, padx=10)

        self.boxlist[StockType.gz300] = {Maturity.M1: IntVar(self.root), Maturity.M2: IntVar(self.root), Maturity.M3: IntVar(self.root), Maturity.Q1: IntVar(self.root), Maturity.Q2: IntVar(self.root), Maturity.Q3: IntVar(self.root)}
        l = Checkbutton(self.root,variable=self.boxlist[StockType.gz300][Maturity.M1])
        l.grid(row=9, column=2, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.gz300][Maturity.M2])
        l.grid(row=9, column=3, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.gz300][Maturity.M3])
        l.grid(row=9, column=4, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.gz300][Maturity.Q1])
        l.grid(row=9, column=5, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.gz300][Maturity.Q2])
        l.grid(row=9, column=6, sticky=E + W, padx=10)
        l = Checkbutton(self.root,variable=self.boxlist[StockType.gz300][Maturity.Q3])
        l.grid(row=9, column=7, sticky=E + W, padx=10)

        def callback():
            self.stop_hedge()
            root.destroy()
            gl.global_var['hg_index'].pop(self.index)
            self.data_txt.close()
        root.protocol("WM_DELETE_WINDOW", callback)
        root.mainloop()


    def hedge_thread(self):

        self.stop_hedge()
        thread = threading.Thread(target = self.hedge)
        thread.setDaemon(True)
        thread.start()


    def stop_hedge(self):

        if self.state.get() == '对冲中......':
            self.root.after_cancel(self.ongoing)
            self.state.set('对冲')
            self.boxlist[0][0].configure(state='normal')
            self.boxlist[0][1].configure(state='normal')
            self.boxlist[0][2].configure(state='normal')


    def hedge(self):

        hedge_strategy = self.boxlist[0][0].get()
        hedge_greeks = self.boxlist[0][1].get()
        hedge_way = self.boxlist[0][3].get()
        try:
            hedge_thred = float(self.boxlist[0][2].get())
        except:
            return

        self.ongoing = self.root.after(500, self.hedge)

        if self.state.get() == '对冲':
            self.state.set('对冲中......')
            self.boxlist[0][0].configure(state='disabled')
            self.boxlist[0][1].configure(state='disabled')
            self.boxlist[0][2].configure(state='disabled')


        trade_period = gl.get_value('trade_period')
        localtime = gl.get_value('localtime')
        if not trade_period or (localtime.tm_hour == 9 and localtime.tm_min < 33) or (localtime.tm_hour == 11 and localtime.tm_min > 26) or (localtime.tm_hour == 13 and localtime.tm_min < 3):
            return

        if not self.p_update_flag:
            return

        if not self.far_from_bs_update:
            return

        stg_greeks = gl.get_value('stg_greeks')
        total_greeks = sum([sum(stg_greeks[hedge_strategy][hedge_greeks][sty].values()) for sty in list(stg_greeks[hedge_strategy][hedge_greeks].keys())])
        if abs(hedge_thred) > abs(total_greeks):
            return

        order = gl.get_value('hg_order')['order']
        if hedge_strategy in list(order.keys()):
            return

        order[hedge_strategy] = {}


        Ft = gl.get_value('hg_order')['Ft']
        Opt = gl.get_value('hg_order')['Opt']
        Opt_for_hg_copy = copy.deepcopy(Opt)


        self.data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '对冲判断前......' + '\n' + 'order for hedge：' + str(order) + '\n' + 'Ft for hg：' + str(Ft) + '\n' + 'Opt for hg：' + str(Opt) + '\n')


        # 模式
        if_mm = self.boxlist['mm'].get()
        if_an = self.boxlist['an'].get()


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
            not_an_sty = [sty for sty in list(stg_greeks[hedge_strategy]['delta$(万)'].keys()) if sty not in [FutureType.IF, FutureType.IH] and stg_greeks[hedge_strategy]['position']['type'][sty] and sum(stg_greeks[hedge_strategy][hedge_greeks][sty].values()) * sign > 0]
            pre_location = {}
            for sty in not_an_sty:
                loc_greeks = total_greeks * sum(stg_greeks[hedge_strategy][hedge_greeks][sty].values()) / sum([sum(stg_greeks[hedge_strategy][hedge_greeks][_sty].values()) for _sty in not_an_sty])
                pre_location[sty] = {Maturity.M1: loc(loc_greeks, stg_greeks[hedge_strategy]['delta$(万)'][sty][Maturity.M1]), Maturity.M2: 0}
                pre_location[sty][Maturity.M2] = loc(loc_greeks - pre_location[sty][Maturity.M1], stg_greeks[hedge_strategy]['delta$(万)'][sty][Maturity.M2])
                pre_location[sty][Maturity.M1] = loc_greeks - pre_location[sty][Maturity.M2]


        data_opt = gl.get_value('data_opt')

        # 分品种，分月份
        for i, sty in enumerate([StockType.etf50, StockType.h300, StockType.s300, StockType.gz300]):

            if if_an and not stg_greeks[hedge_strategy]['position']['type'][sty]:
                continue
            if not if_an and not sty in not_an_sty:
                continue

            for j, mat in enumerate(list(stg_greeks[hedge_strategy][hedge_greeks][sty].keys())):

                if if_an and not stg_greeks[hedge_strategy]['position']['mat'][sty][mat]:
                    continue
                if not if_an and not mat in [Maturity.M1, Maturity.M2]:
                    continue


                if i == 0:
                    future_type = FutureType.IH
                else:
                    future_type = FutureType.IF

                Mat = gl.get_value('Mat')
                mat_future = data_opt[future_type].matlist[np.argmin(abs(np.array([int(Mat['contract_format'][future_type][mat0]) for mat0 in data_opt[future_type].matlist]) - int(Mat['contract_format'][sty][mat])))]
                if hedge_way == '先期货后合成' and if_mm:
                    if not self.boxlist[future_type].get() == 0:
                        mat_future = Maturity(self.boxlist[future_type].get())


                # 期货对冲
                pre_future = 0
                if (hedge_strategy, sty, mat) in list(Ft.keys()):
                    pre_future = sum([Ft[(hedge_strategy, sty, mat)][mat_from_future] * data_opt[future_type].midbidaskspread(mat_from_future) * data_opt[future_type].cm * 1 / 10000 for mat_from_future in list(Ft[(hedge_strategy, sty, mat)].keys())])

                def of(oo: tuple):
                    opt_c = gl.name_to_data(oo[2][0])
                    used_sty = opt_c.sty
                    used_mat = opt_c.mat
                    position_p = data_opt[used_sty].k_list[used_mat].index(float(oo[2][1][gl.last_C_P(oo[2][1]) : ]))
                    opt_p = data_opt[used_sty].OptionList[used_mat][position_p][1]

                    opt_c._iv = opt_c.iv()
                    opt_p._iv = opt_p.iv()
                    return data_opt[used_sty].S[used_mat] * data_opt[used_sty].cm * (opt_c.delta() - opt_p.delta()) / 10000

                pre_option = 0
                if (hedge_strategy, sty, mat) in list(Opt_for_hg_copy.keys()):
                    pre_option = sum([Opt_for_hg_copy[(hedge_strategy, sty, mat)][oo] * of(oo) for oo in list(Opt_for_hg_copy[(hedge_strategy, sty, mat)].keys())])

                current_greeks = 0
                if if_an:
                    current_greeks = stg_greeks[hedge_strategy][hedge_greeks][sty][mat] + pre_future + pre_option - sum([sum([Opt_for_hg_copy[hsm][oo] * of(oo) for oo in list(Opt_for_hg_copy[hsm].keys()) if oo[0:2] == (sty, mat)]) for hsm in list(Opt_for_hg_copy.keys())])
                else:
                    current_greeks = pre_location[sty][mat]

                future_tool = float('inf')
                if not data_opt[future_type].midbidaskspread(mat_future) == None:
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
                for hedge_sty in self.change_list[sty]:
                    if br:
                        break

                    mat_list = [mat, Maturity.M1, Maturity.M2]
                    if mat == Maturity.M1:
                        mat_list = mat_list[1:]

                    if if_mm:
                        mat_list = [mm_mat for mm_mat in list(self.boxlist[hedge_sty].keys()) if self.boxlist[hedge_sty][mm_mat].get()]

                    for z, hedge_mat in enumerate(mat_list):
                        if br:
                            break

                        mat_atm = data_opt[hedge_sty].OptionList[hedge_mat][data_opt[hedge_sty].posi[hedge_mat]['atm']]
                        mat_x1 = [data_opt[hedge_sty].OptionList[hedge_mat][data_opt[hedge_sty].posi[hedge_mat]['c_x1']][0], data_opt[hedge_sty].OptionList[hedge_mat][data_opt[hedge_sty].posi[hedge_mat]['p_x1']][1]]
                        try_k_list = [mat_atm, [mat_atm[0], mat_x1[1]], [mat_atm[1], mat_x1[0]], mat_x1]

                        for hedge_k in try_k_list:
                            # 未熔断 and 流动性好
                            if [True, True] == [True for i in range(2) if hedge_k[i].cb == False and '' not in [hedge_k[i].ask, hedge_k[i].bid] and hedge_k[i].ask - hedge_k[i].bid < data_opt[hedge_sty].mc * data_opt[hedge_sty].tick_limit and hedge_k[i].P > data_opt[hedge_sty].p_limit]:
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
                    order.pop(hedge_strategy)
                    return


                # for future
                if not num_future == 0:
                    if contract_for_future not in list(order[hedge_strategy].keys()):
                        order[hedge_strategy][contract_for_future] = 0
                    order[hedge_strategy][contract_for_future] -= num_future

                    # futures for hegde written in Ft
                    if (hedge_strategy, sty, mat) not in list(Ft.keys()):
                        Ft[(hedge_strategy, sty, mat)] = {}
                    if mat_future not in list(Ft[(hedge_strategy, sty, mat)].keys()):
                        Ft[(hedge_strategy, sty, mat)][mat_future] = 0 # 持仓
                    Ft[(hedge_strategy, sty, mat)][mat_future] -= num_future

                # for option
                if not num_opt == 0:
                    for z, ctr in enumerate(contract_for_option):
                        if ctr not in list(order[hedge_strategy].keys()):
                            order[hedge_strategy][ctr] = 0
                        if z == 0:
                            order[hedge_strategy][ctr] -= num_opt
                        else:
                            order[hedge_strategy][ctr] += num_opt

                    # options for hegde written in Opt
                    if if_an and not (sty, mat) == option_chosen[:2]:
                        if (hedge_strategy, sty, mat) not in list(Opt.keys()):
                            Opt[(hedge_strategy, sty, mat)] = {}
                        if option_chosen not in list(Opt[(hedge_strategy, sty, mat)].keys()):
                            Opt[(hedge_strategy, sty, mat)][option_chosen] = 0 # 持仓 for call
                        Opt[(hedge_strategy, sty, mat)][option_chosen] -= num_opt


        self.data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '对冲判断后......' + '\n' + 'order for hedge：' + hedge_strategy + str(order[hedge_strategy]) + '\n' + 'Ft for hg：' + str(Ft) + '\n' + 'Opt for hg：' + str(Opt) + '\n')
        self.data_txt.flush()

        if order[hedge_strategy] == {}:
            order.pop(hedge_strategy)
            return

        # 下单
        for target in list(order[hedge_strategy].keys()):
            num = order[hedge_strategy][target]
            od.order_api(target, 'HIT', num, hedge_strategy, 'hedge')

        self.p_update_flag = False
        self.p_update_list = list(order[hedge_strategy].keys())