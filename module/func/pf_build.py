from tkinter import *
from tkinter import ttk
import threading
import math
import copy
import time

from module.base.pf_enum import *
from ..base import pf_global as gl
from ..base import pf_order as od


class build:

    def __init__(self, index: int):

        self.index = index
        self.cb_in_grp = False
        self.order_completed = True
        self.direction = 0
        self.status = 'build'
        self.position_built = {}
        self.vega = {'long': 0, 'short': 0}
        self.build_strategy = None
        self.repeat = False
        self.completed = False
        self.first_detect = False
        self.first_close = True

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
        root.title('VolSpread')
        index = [i for i, x in enumerate(geometry) if x == '+']
        root.geometry("%dx%d+%d+%d" % (620, 180, int(geometry[index[0] + 1 : index[1]]), int(geometry[index[1] + 1 :]) + 500))
        canvas = Canvas(root, borderwidth=0)
        frame = Frame(canvas)
        self.root = frame
        self.boxlist = {0:[], 2:[], 3:[], 4: []}
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
        tyChosen['values'] = ['300', '350']
        tyChosen.grid(column=1, row=2, padx=5)
        tyChosen.current(0)
        self.boxlist[0].append(tyChosen)

        def func(*args):
            ty_name = tyChosen.get()
            fore_ty = StockType.gz300 if ty_name == '300' else StockType.h300
            Mat = gl.get_value('Mat')
            matChosen['values'] = list(Mat['contract_format'][fore_ty].values())[:3] if Mat['contract_format'][StockType.gz300][Maturity.M3] == Mat['contract_format'][StockType.h300][Maturity.Q1] else list(Mat['contract_format'][fore_ty].values())[:2]
            stgChosen['values'] = [i for i in all_strategies if ty_name in i]

        tyChosen.bind("<<ComboboxSelected>>", func)

        lb_mat = ttk.Label(self.root, text = '到期时间')
        lb_mat.grid(row=1, column=2)
        mat = StringVar()
        matChosen = ttk.Combobox(self.root, width=10, textvariable=mat)
        matChosen['values'] = ['']
        matChosen.grid(column=2, row=2, padx=5)
        matChosen.current(0)
        self.boxlist[0].append(matChosen)

        lb_stg = ttk.Label(self.root, text = '策略')
        lb_stg.grid(row=1, column=3)
        stg = StringVar()
        stgChosen = ttk.Combobox(self.root, width=10, textvariable=stg)
        stgChosen['values'] = ['']
        stgChosen.grid(column=3, row=2, padx=5)
        stgChosen.current(0)
        self.boxlist[0].append(stgChosen)

        lb = ttk.Label(self.root, text = '是否来回建仓')
        lb.grid(row=1, column=4)
        self.boxlist['repeat'] = IntVar(self.root)
        l = Checkbutton(self.root,variable=self.boxlist['repeat'])
        l.grid(row=2, column=4, sticky=E + W, padx=10)

        self.state = StringVar()
        self.state.set('启动')
        b = Button(self.root, textvariable=self.state, command=self.build_thread, width=10)
        b.grid(row=2, column=5, sticky=E, padx=5, pady=10)

        b = Button(self.root, text='停止', command=self.stop_build, width=10)
        b.grid(row=2, column=6, sticky=E, padx=5, pady=10)


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

        lb = ttk.Label(self.root, text = '平仓至vega')
        lb.grid(row=6, column=3)
        num = StringVar()
        numEntry = ttk.Entry(self.root, width=10, textvariable=num)
        numEntry.grid(column=4, row=6, padx=5)
        self.boxlist[4].append(numEntry)

        lb = ttk.Label(self.root, text = '建仓价格')
        lb.grid(row=4, column=5)
        price1 = StringVar()
        price1Chosen = ttk.Combobox(self.root, width=10, textvariable=price1)
        price1Chosen['values'] = ['MID', 'HIT']
        price1Chosen.grid(column=6, row=4, padx=5)
        price1Chosen.current(0)
        self.boxlist[2].append(price1Chosen)

        lb = ttk.Label(self.root, text = '平仓价格')
        lb.grid(row=5, column=5)
        price2 = StringVar()
        price2Chosen = ttk.Combobox(self.root, width=10, textvariable=price2)
        price2Chosen['values'] = ['HIT', 'MID']
        price2Chosen.grid(column=6, row=5, padx=5)
        price2Chosen.current(0)
        self.boxlist[3].append(price2Chosen)

        def callback():
            self.stop_build()
            root.destroy()
            gl.global_var['bd_index'].pop(self.index)
            self.data_txt.close()
            order = gl.get_value('bd_order')['order']
            if self.build_strategy in list(order.keys()):
                order.pop(self.build_strategy)
        root.protocol("WM_DELETE_WINDOW", callback)
        root.mainloop()


    def build_thread(self):

        self.stop_build()
        thread = threading.Thread(target = self.build)
        thread.setDaemon(True)
        thread.start()


    def stop_build(self):

        if self.state.get() == '运行中......':
            self.root.after_cancel(self.ongoing)
            self.state.set('启动')
            for tp in [(2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (2, 2), (3, 2)]:
                self.boxlist[tp[0]][tp[1]].configure(state='normal')


    def build(self):

        if self.completed:
            return

        build_mat = self.boxlist[0][1].get()
        build_strategy = self.boxlist[0][2].get()
        self.build_strategy = build_strategy
        self.repeat = self.boxlist['repeat'].get()

        build_price = self.boxlist[2][2].get()
        close_price = self.boxlist[3][2].get()

        if build_price not in ['HIT', 'MID'] or close_price not in ['HIT', 'MID']:
            return

        try:

            build_upper = float(self.boxlist[2][0].get()) / 100
            build_lower = float(self.boxlist[3][0].get()) / 100
            target_vega = abs(float(self.boxlist[2][1].get()))
            close_to_vega = abs(float(self.boxlist[4][0].get()))
            fore = abs(int(self.boxlist[3][1].get()))

        except:
            return

        if build_mat == '':
            return

        if build_strategy == '':
            return

        if build_upper <= build_lower:
            return

        self.ongoing = self.root.after(500, self.build)

        if self.state.get() == '启动':
            self.state.set('运行中......')
            for tp in [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (2, 2), (3, 2)]:
                self.boxlist[tp[0]][tp[1]].configure(state='disabled')

        trade_period = gl.get_value('trade_period')
        localtime = gl.get_value('localtime')
        if not trade_period or (localtime.tm_hour == 9 and localtime.tm_min < 35) or (localtime.tm_hour == 11 and localtime.tm_min > 24) or (localtime.tm_hour == 13 and localtime.tm_min < 5):
            return

        order = gl.get_value('bd_order')['order']
        if build_strategy in list(order.keys()):

            if not self.order_completed:
                return

            # 判断上轮下单是否成交完成
            if [order[build_strategy][target]['leavesqty'] for target in list(order[build_strategy].keys())] == [0] * len(order[build_strategy]):
                order.pop(build_strategy)

                if self.status == 'close':
                    stg_posi = gl.get_value('stg_posi')
                    if build_strategy in list(stg_posi.keys()):
                        self.position_built = stg_posi[build_strategy]

                    for key in list(self.position_built.keys()):
                        if not self.position_built[key] == 0:
                            return

                    if not self.repeat:
                        self.completed = True
                        return

                    self.position_built = {}
                    self.first_close = True
                    self.direction = 0

                return

            # 熔断提示
            current_time = time.time()
            target_list = list(order[build_strategy].keys())

            if True in [gl.name_to_data(target).cb for target in list(order[build_strategy].keys())] and not self.cb_in_grp:
                self.cb_in_grp = True
                def msg():
                    messagebox.showinfo(title='熔断提示', message='合约熔断，请交易员操作')
                _t = threading.Thread(target = msg)
                _t.setDaemon(True)
                _t.start()

            # 未成交单处理
            for i, target in enumerate(target_list):

                rp_list = list(order[build_strategy][target]['rp'].keys())

                # 合约未熔断（普通建/平仓）
                if not self.cb_in_grp:

                    for rp in rp_list:
                        num = order[build_strategy][target]['rp'][rp]['leavesqty']

                        if not num == 0 and current_time - order[build_strategy][target]['rp'][rp]['ot'] > 3:

                            if not order[build_strategy][target]['rp'][rp]['cancel_order']:
                                od.order_cancel(rp)
                                order[build_strategy][target]['rp'][rp]['cancel_order'] = True

                            if order[build_strategy][target]['rp'][rp]['canceled']:

                                order[build_strategy][target]['rp'].pop(rp)

                                if self.status == 'build':
                                    if '.C.' in target:
                                        couple_target = [t for t in target_list if '.C.' in t]
                                    elif '.P.' in target:
                                        couple_target = [t for t in target_list if '.P.' in t]

                                    def _order():
                                        if 0 in [order[build_strategy][ct]['leavesqty'] for ct in couple_target]:
                                            od.order_api(target, 'HIT', num, build_strategy, 'build')
                                        else:
                                            od.order_api(target, build_price, num, build_strategy, 'build')

                                elif self.status == 'close':
                                    def _order():
                                        od.order_api(target, close_price, num, build_strategy, 'build')

                                _t = threading.Thread(target=_order)
                                _t.setDaemon(True)
                                _t.start()

                # 合约熔断（撤单，出提示）
                else:

                    for rp in rp_list:
                        num = order[build_strategy][target]['rp'][rp]['leavesqty']

                        if not num == 0 and not order[build_strategy][target]['rp'][rp]['cancel_order']:
                            od.order_cancel(rp)
                            order[build_strategy][target]['rp'][rp]['cancel_order'] = True

                        if num == 0 or order[build_strategy][target]['rp'][rp]['canceled']:
                            order[build_strategy][target]['rp'].pop(rp)

                        if len(order[build_strategy][target]['rp']) == 0:
                            order[build_strategy][target]['leavesqty'] = 0

            return


        order[build_strategy] = {}

        if '300' in build_strategy:
            fore_ty = StockType.gz300
            hind_ty = StockType.h300
        elif '350' in build_strategy:
            fore_ty = StockType.h300
            hind_ty = StockType.etf50

        data_opt = gl.get_value('data_opt')
        mat_fore = data_opt[fore_ty]._2005_to_Mat[build_mat]
        mat_hind = data_opt[hind_ty]._2005_to_Mat[build_mat]
        vix_dict_fore = data_opt[fore_ty].vix(mat_fore)
        vix_dict_hind = data_opt[hind_ty].vix(mat_hind)

        if vix_dict_fore['cb'] == False and vix_dict_hind['cb'] == False:
            if vix_dict_fore['vix'] - vix_dict_hind['vix'] >= build_upper:
                direction = -1
            elif vix_dict_fore['vix'] - vix_dict_hind['vix'] <= build_lower:
                direction = 1
            else:
                order.pop(build_strategy)
                return
        else:
            order.pop(build_strategy)
            return

        self.status = 'build'
        stg_greeks = gl.get_value('stg_greeks')
        if not self.first_detect:
            self.first_detect = True
            if build_strategy in list(stg_greeks.keys()):
                v = sum(stg_greeks[build_strategy]['vega$'][fore_ty].values())
                if not v == 0:
                    self.direction = 1 if v > 0 else -1
        if self.direction * direction == -1:
            self.status = 'close'

        opt_fore = data_opt[fore_ty].OptionList[mat_fore][data_opt[fore_ty].posi[mat_fore]['atm']]
        opt_hind = data_opt[hind_ty].OptionList[mat_hind][data_opt[hind_ty].posi[mat_hind]['atm']]


        if self.status == 'build':

            if '' in [opt_fore[0].yc_master_contract, opt_fore[1].yc_master_contract, opt_hind[0].yc_master_contract, opt_hind[1].yc_master_contract]:
                order.pop(build_strategy)
                return

            if direction == 1 and self.vega['long'] >= target_vega:
                order.pop(build_strategy)
                return

            if direction == -1 and self.vega['short'] <= -1 * target_vega:
                order.pop(build_strategy)
                return

            fore *= direction

            curr_fore_delta = 0
            if build_strategy in list(stg_greeks.keys()) and fore_ty in list(stg_greeks[build_strategy]['delta$(万)'].keys()):
                curr_fore_delta = sum(stg_greeks[build_strategy]['delta$(万)'][fore_ty].values())
            c_p = 0 if (curr_fore_delta < 0 and direction > 0) or (curr_fore_delta > 0 and direction < 0) else 1
            thred_fore_delta = fore * data_opt[fore_ty].S[mat_fore] * data_opt[fore_ty].cm * opt_fore[c_p].delta() / 10000

            # 普通建仓
            if not abs(curr_fore_delta) >= abs(thred_fore_delta):

                # 前跨合成期货 调 前跨delta中性
                fore_delta = fore * data_opt[fore_ty].S[mat_fore] * data_opt[fore_ty].cm * (opt_fore[0].delta() + opt_fore[1].delta()) / 10000
                fore_synfut_delta = data_opt[fore_ty].S[mat_fore] * data_opt[fore_ty].cm * (opt_fore[0].delta() - opt_fore[1].delta()) / 10000
                fore_num_synfut = round(fore_delta / fore_synfut_delta, 0)

                # vega中性
                fore_straddle_vega = data_opt[fore_ty].cm * (opt_fore[0].vega() * (fore - fore_num_synfut) + opt_fore[1].vega() * (fore + fore_num_synfut)) * 0.01
                hind_straddle_vega_per_synfut = data_opt[hind_ty].cm * (opt_hind[0].vega() + opt_hind[1].vega()) * 0.01
                hind = -1 * round(fore_straddle_vega / hind_straddle_vega_per_synfut, 0)

                # 后跨合成期货 调 整体delta中性
                fore_straddle_delta = fore_delta - fore_num_synfut * fore_synfut_delta
                hind_straddle_delta = hind * data_opt[hind_ty].S[mat_hind] * data_opt[hind_ty].cm * (opt_hind[0].delta() + opt_hind[1].delta()) / 10000
                delta_per_grp = fore_straddle_delta + hind_straddle_delta
                hind_synfut_delta = data_opt[hind_ty].S[mat_hind] * data_opt[hind_ty].cm * (opt_hind[0].delta() - opt_hind[1].delta()) / 10000
                hind_num_synfut = round(delta_per_grp / hind_synfut_delta, 0)

                order[build_strategy] = {opt_fore[0].yc_master_contract: {'originalqty': fore - fore_num_synfut}, opt_hind[0].yc_master_contract: {'originalqty': hind - hind_num_synfut}, opt_fore[1].yc_master_contract: {'originalqty': fore + fore_num_synfut}, opt_hind[1].yc_master_contract: {'originalqty': hind + hind_num_synfut}}
                fore_vega = fore_straddle_vega

                d = 'long' if direction == 1 else 'short'
                self.vega[d] += fore_vega

            # 打单边
            else:

                single_fore_vega = fore * data_opt[fore_ty].cm * opt_fore[c_p].vega() * 0.01
                single_fore_delta = fore * data_opt[fore_ty].S[mat_fore] * data_opt[fore_ty].cm * opt_fore[c_p].delta() / 10000
                single_hind_vega = data_opt[hind_ty].cm * opt_hind[c_p].vega() * 0.01
                hind = round(-1 * single_fore_vega / single_hind_vega, 0)
                single_hind_delta = hind * data_opt[hind_ty].S[mat_hind] * data_opt[hind_ty].cm * opt_hind[c_p].delta() / 10000
                hind_synfut_delta = data_opt[hind_ty].S[mat_hind] * data_opt[hind_ty].cm * (opt_hind[0].delta() - opt_hind[1].delta()) / 10000
                hind_num_synfut = round((single_fore_delta + single_hind_delta) / hind_synfut_delta, 0)

                if c_p == 0:
                    order[build_strategy] = {opt_fore[c_p].yc_master_contract: {'originalqty': fore}, opt_hind[0].yc_master_contract: {'originalqty': hind - hind_num_synfut}, opt_hind[1].yc_master_contract: {'originalqty': hind_num_synfut}}
                else:
                    order[build_strategy] = {opt_fore[c_p].yc_master_contract: {'originalqty': fore}, opt_hind[0].yc_master_contract: {'originalqty': -1 * hind_num_synfut}, opt_hind[1].yc_master_contract: {'originalqty': hind + hind_num_synfut}}

                d = 'long' if direction == 1 else 'short'
                self.vega[d] += single_fore_vega

            self.data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '建仓判断后......' + '\n' + 'order for build：' + build_strategy + str(order[build_strategy]) + '\n')
            self.data_txt.flush()

            # 下单
            if True in [gl.name_to_data(target).cb for target in list(order[build_strategy].keys())]:
                order.pop(build_strategy)
                return

            self.cb_in_grp = False
            self.order_completed = False
            self.direction = direction

            def _order():
                for target in list(order[build_strategy].keys()):
                    # order
                    num = order[build_strategy][target]['originalqty']
                    order[build_strategy][target]['leavesqty'] = num
                    order[build_strategy][target]['rp'] = {}
                    od.order_api(target, build_price, num, build_strategy, 'build')
                self.order_completed = True

            _t = threading.Thread(target=_order)
            _t.setDaemon(True)
            _t.start()


        elif self.status == 'close':

            stg_posi = gl.get_value('stg_posi')
            if build_strategy in list(stg_posi.keys()):
                self.position_built = stg_posi[build_strategy]

            if self.first_close:

                # 先调一次整体delta中性
                fore_delta = sum(stg_greeks[build_strategy]['delta$(万)'][fore_ty].values())
                hind_delta = sum(stg_greeks[build_strategy]['delta$(万)'][hind_ty].values())
                used_ty = fore_ty if abs(fore_delta) > abs(hind_delta) else hind_ty
                used_mat = mat_fore if abs(fore_delta) > abs(hind_delta) else mat_hind
                used_opt = opt_fore if abs(fore_delta) > abs(hind_delta) else opt_hind
                delta_hedge = fore_delta + hind_delta
                synfut_delta = data_opt[used_ty].S[used_mat] * data_opt[used_ty].cm * (used_opt[0].delta() - used_opt[1].delta()) / 10000
                num_synfut = round(delta_hedge / synfut_delta, 0)
                order[build_strategy] = {used_opt[0].yc_master_contract: {'originalqty': -1 * num_synfut}, used_opt[1].yc_master_contract: {'originalqty': num_synfut}}

                self.first_close = False

            else:

                # 每组3000vega进行平仓
                v = abs(sum(stg_greeks[build_strategy]['vega$'][fore_ty].values()))
                close_vega = max(v - close_to_vega, 0)
                for key in list(self.position_built.keys()):
                    order[build_strategy][key] = {'originalqty': -1 * round(self.position_built[key] * min(3000, close_vega) / v, 0)}

            self.data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '平仓判断后......' + '\n' + 'order for build：' + build_strategy + str(order[build_strategy]) + '\n')
            self.data_txt.flush()

            # 下单
            if True in [gl.name_to_data(target).cb for target in list(order[build_strategy].keys())]:
                order.pop(build_strategy)
                return

            self.cb_in_grp = False
            self.order_completed = False

            def _order():
                for target in list(order[build_strategy].keys()):
                    # order
                    num = order[build_strategy][target]['originalqty']
                    order[build_strategy][target]['leavesqty'] = num
                    order[build_strategy][target]['rp'] = {}
                    od.order_api(target, close_price, num, build_strategy, 'build')
                self.order_completed = True

            _t = threading.Thread(target=_order)
            _t.setDaemon(True)
            _t.start()