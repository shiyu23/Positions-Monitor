from tkinter import font, messagebox, filedialog, ttk
from tkinter import *
from tcoreapi_mq import *
import xlrd,xlwt
import threading
import time
import json
import sys
import os
sys.coinit_flags = 0

from module.base import pf_global as gl
from module.base.pf_enum import *
from module.func import pf_hedge


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
        self.mp_root_flag = False

        self.boxlist = []
        self.bs_boxlist = {}
        self.checkbutton_context_list = {}

        self.strategy_trade_return = {'all_data':[], 'type5': []}
        self.colors = ['#FFA500','#87CEFA','#778899', '#DB7093', '#FF1493',
                       '#7FFFAA','#F0E68C','#FF7F50','#C0C0C0','#BA55D3',
                       '#FF4500']

        self.stop_update_max_profit = {}

        # 补单
        self.addin_orderid = []
        # 记录
        localtime = gl.get_value('localtime')
        self.order_data_txt = open(f'./log/order data {localtime.tm_year}-{localtime.tm_mon}-{localtime.tm_mday}.txt', 'a')
        #部位是否有熔断
        self.if_position_cb: bool = False
        #self.lock = threading.RLock()


    ##############################################################################################################
    def init_profit_ui(self):

        root = Tk()
        root.iconbitmap(default=r'./pictures/logo.ico')

        root.resizable(0, 0)
        root.title('策略持仓监控')

        self.main_root_position = root.winfo_geometry()

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
                g_TradeZMQ = gl.get_value('g_TradeZMQ')
                g_TradeSession = gl.get_value('g_TradeSession')
                g_QuoteZMQ = gl.get_value('g_QuoteZMQ')
                g_QuoteSession = gl.get_value('g_QuoteSession')

                g_TradeZMQ.trade_logout(g_TradeSession)
                g_QuoteZMQ.quote_logout(g_QuoteSession)
                self.order_data_txt.close()
                root.destroy()
                gl.set_value('exit_signal', 1)
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
        try:
            data = xlrd.open_workbook(path, encoding_override = 'utf-8')
        except:
            messagebox.showerror(title='错误', message='请导入excel文件！')
            return
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
        Ft_for_hg = gl.get_value('hg_order')['Ft']
        Opt_for_hg = gl.get_value('hg_order')['Opt']
        str_to_type = gl.get_value('str_to_type')

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
                if key not in list(Ft_for_hg.keys()):
                    Ft_for_hg[key] = {}
                used_mat = str_to_type[row[4]]
                if used_mat not in list(Ft_for_hg[key].keys()):
                    Ft_for_hg[key][used_mat] = 0
                Ft_for_hg[key][used_mat] += int(row[5])

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
                if key not in list(Opt_for_hg.keys()):
                    Opt_for_hg[key] = {}
                used_sty = str_to_type[row[4]]
                used_mat = str_to_type[row[5]]
                used_call = row[6]
                used_put = row[7]
                if (used_sty, used_mat, (used_call, used_put)) not in list(Opt_for_hg[key].keys()):
                    Opt_for_hg[key][(used_sty, used_mat, (used_call, used_put))] = 0
                Opt_for_hg[key][(used_sty, used_mat, (used_call, used_put))] += int(row[8])

        self.p_refresh()
        self.load_file_signal = False


    def save_file(self):
        path = filedialog.askdirectory()
        if path == '':
            return

        localtime = gl.get_value('localtime')
        dt = time.strftime('%Y-%m-%d', localtime)
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
        Ft_for_hg = gl.get_value('hg_order')['Ft']
        Opt_for_hg = gl.get_value('hg_order')['Opt']
        type_to_str = gl.get_value('type_to_str')

        for i in list(Ft_for_hg.keys()):
            strategy = i[0]
            sty = type_to_str[i[1]]
            mat = type_to_str[i[2]]
            for j in list(Ft_for_hg[i].keys()):
                used_mat = type_to_str[j]
                if not Ft_for_hg[i][j] == 0:
                    row_vals = ['HEDGE_F', strategy, sty, mat, used_mat, Ft_for_hg[i][j]]
                    insert_row(row_counter, row_vals)
                    row_counter += 1

        # record Opt_for_hg
        for i in list(Opt_for_hg.keys()):
            strategy = i[0]
            sty = type_to_str[i[1]]
            mat = type_to_str[i[2]]
            for j in list(Opt_for_hg[i].keys()):
                used_sty = type_to_str[j[0]]
                used_mat = type_to_str[j[1]]
                used_call = j[2][0]
                used_put = j[2][1]
                if not Opt_for_hg[i][j] == 0:
                    row_vals = ['HEDGE_O', strategy, sty, mat, used_sty, used_mat, used_call, used_put, Opt_for_hg[i][j]]
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
        index = [i for i, x in enumerate(self.main_root_position) if x == '+']
        root.geometry("%dx%d+%d+%d" % (233, 400, int(self.main_root_position[index[0] + 1 : index[1]]), int(self.main_root_position[index[1] + 1 :]) + 100))
        root.title('盈利界面')

        for i, strategy in enumerate(strategies):
            Label(root, text=strategy).grid(row=i, column=0, sticky=E)

        root.mainloop()


    def modify_strategy_name(self):
        messagebox.showinfo(title='~', message='对不起，还在开发~')


    def p_refresh(self):
        gl.set_value('localtime', time.localtime())
        localtime = gl.get_value('localtime')
        if (localtime.tm_hour == 9 and localtime.tm_min >= 30) or localtime.tm_hour == 10 or (localtime.tm_hour == 11 and localtime.tm_min < 30) or localtime.tm_hour == 13 or (localtime.tm_hour == 14 and localtime.tm_min < 57):
            gl.set_value('trade_period', True)
        else:
            gl.set_value('trade_period', False)

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
                                    opt = gl.name_to_data(contract)
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

                def create_hedge():
                    hg_index = gl.global_var['hg_index']
                    index = len(hg_index)
                    hg_index[index] = pf_hedge.hedge(index)
                    hg_index[index].open_hedge_ui(list(self.label_var.keys()), self.main_root_position)

                b = Button(self.p_root, text='对冲', width=10, command=create_hedge)
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
        localtime = gl.get_value('localtime')
        data_opt = gl.get_value('data_opt')
        Mat = gl.get_value('Mat')


        if 'TC.O' in contract:

            opt = gl.name_to_data(contract)
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
                            o = gl.name_to_data(c)
                            if o.cb:
                                num += 1
                if num == 0:
                    self.if_position_cb = False
                    self.add_new_signal.append(1)

            # greeks已更新flag
            order_for_hg = gl.get_value('hg_order')['order']
            hg_index = gl.global_var['hg_index']
            for index in list(hg_index.keys()):
                hedge_strategy = hg_index[index].boxlist[0][0].get()

                if hedge_strategy not in list(order_for_hg.keys()):
                    if contract in hg_index[index].p_update_list:
                        hg_index[index].p_update_list.remove(contract)
           
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

                trade_period = gl.get_value('trade_period')
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
                    hg_data = gl.get_value('hg_data')
                    if strategy not in list(hg_data.keys()):
                        hg_data[strategy] = {}
                        hg_data[strategy]['position'] = {}
                    hg_data[strategy][comb[0]] = greeks
                    hg_data[strategy]['position']['type'] = ty_position
                    hg_data[strategy]['position']['mat'] = ty_mat_position

            # greeks已更新flag
            for index in list(hg_index.keys()):
                hg_index[index].p_update_flag = False
                if hg_index[index].p_update_list == []:
                    hg_index[index].p_update_flag = True

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
        root.title('成交回报')
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
                Mat = gl.get_value('Mat')

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

        localtime = gl.get_value('localtime')
        order_for_hg = gl.get_value('hg_order')['order']
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
                    if strategy in list(order_for_hg.keys()):
                        if contract in list(order_for_hg[strategy].keys()) and OriginalQty == OrderQty and leavesqty == 0:
                            order_for_hg[strategy].pop(contract)
                        if order_for_hg[strategy] == {}:
                            order_for_hg.pop(strategy)

            self.bs_refresh_signal.append(1)
            break


        # 补单
        if not outer and ExecType in ['5', '8', '9'] and not id in self.addin_orderid:
            self.order_data_txt.write(time.strftime('%H:%M:%S', localtime) + ' | ' + '(需要补单的成交回报) ' + str(quote) + '\n')

            num_add = int(OriginalQty) - int(OrderQty)
            mp = 1 if Direction == 1 else -1
            num_add *= mp

            if source == 'hedge':
                if strategy in list(order_for_hg.keys()):
                    if contract in list(order_for_hg[strategy].keys()):
                        order_for_hg[strategy][contract] = num_add

            self.addin_orderid.append(id)

            gl.global_var['hg_index'][0].order_api(contract, 'HIT', num_add, strategy, source)

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
        index = [i for i, x in enumerate(self.main_root_position) if x == '+']
        root.geometry("%dx%d+%d+%d" % (680, 100, int(self.main_root_position[index[0] + 1 : index[1]]), int(self.main_root_position[index[1] + 1 :]) + 100))
        canvas = Canvas(root, borderwidth=0)
        frame = Frame(canvas)
        mp_root = frame
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
        stgChosen = ttk.Combobox(mp_root, width=10, textvariable=stg)
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
        ctChosen = ttk.Combobox(mp_root, width=30, textvariable=ct)
        ctChosen['values'] = contract
        ctChosen.grid(column=2, row=1, padx=5)
        ctChosen.current(0)
        self.mp_boxlist[0].append(ctChosen)


        param = StringVar()
        paramChosen = ttk.Combobox(mp_root, width=10, textvariable=param)
        paramChosen['values'] = ['持仓数', '均价', '平仓损益', '当日最大总收益']
        paramChosen.grid(column=3, row=1, padx=5)
        paramChosen.current(0)
        self.mp_boxlist[0].append(paramChosen)


        dt = StringVar()
        dtEntry = ttk.Entry(mp_root, width=10, textvariable=dt)
        dtEntry.grid(column=4, row=1, padx=5)
        self.mp_boxlist[0].append(dtEntry)


        b = Button(mp_root, text="更新", command=self.modify_param, width=10)
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
        exit_signal = gl.get_value('exit_signal')
        g_TradeZMQ = gl.get_value('g_TradeZMQ')
        g_TradeSession = gl.get_value('g_TradeSession')

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
    while True:
        exit_signal = gl.get_value('exit_signal')
        g_QuoteZMQ = gl.get_value('g_QuoteZMQ')
        g_QuoteSession = gl.get_value('g_QuoteSession')

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


def main():

    gl._init()

    global MY
    MY = monitor_yield()

    g_TradeZMQ = gl.get_value('g_TradeZMQ')
    g_TradeSession = gl.get_value('g_TradeSession')
    g_QuoteZMQ = gl.get_value('g_QuoteZMQ')
    g_QuoteSession = gl.get_value('g_QuoteSession')
    t_data = gl.get_value('t_data')
    q_data = gl.get_value('q_data')

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