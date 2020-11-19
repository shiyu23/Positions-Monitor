import sys
sys.coinit_flags = 0
import datetime
from tcoreapi_mq import *
import xlrd,xlwt
import time
from tkinter import filedialog
from tkinter import ttk, messagebox
import random
import os
from tkinter import *
import threading

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

        self.quote_obj_list = []
        self.label_var = {}
        self.add_new_signal = [1]
        self.inputs = []

        self.p_refresh_signal = []
        self.bs_refresh_signal = []
        self.buy_sell_var = {}

        self.bs_boxlist = {0:[]}
        self.checkbutton_context_list = {}

        self.strategy_trade_return = {'all_data':[]}
        self.colors = ['#FFA500','#87CEFA','#778899', '#DB7093', '#FF1493',
                       '#7FFFAA','#F0E68C','#FF7F50','#C0C0C0','#BA55D3',
                       '#FF4500']

        # random.shuffle(self.colors)

    def load_file(self):

        if not self.load_file_signal:
            messagebox.showerror(title='错误', message='导入文件失败,已导入文件，请重新开启软件再导入！')
            return

        path = filedialog.askopenfilename()
        if path == '':
            messagebox.showerror(title='错误', message='导入文件失败！')
            return

        inputs = []
        data = xlrd.open_workbook(path)
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
            strategy = row[0]
            contract = row[1]
            nums = int(row[2])
            avg_price = float(row[3])
            dynamic_profit = float(row[4])  # 所持仓，与当前价格计算而来
            fixed_profit = float(float(row[5]))  # 卖掉而产生的收益
            inputs.append([strategy, contract, nums, avg_price, dynamic_profit, fixed_profit])

        for i, values in enumerate(inputs):
            if values[0] not in self.label_var.keys():
                self.label_var[values[0]] = {}
            if values[1] not in self.label_var[values[0]].keys():
                self.label_var[values[0]][values[1]] = {}
                self.quote_obj_list.append({"Symbol": values[1], "SubDataType": "REALTIME", })
                for j,name in enumerate(self.p_names):
                    self.label_var[values[0]][values[1]][name] = StringVar(self.p_root)
                    if j < len(self.p_names[:6]):
                        if j == 3:
                            self.label_var[values[0]][values[1]][name].set('{:g}'.format(values[j]))

                        else:
                            self.label_var[values[0]][values[1]][name].set(values[j])

        self.p_refresh()
        main()

        for quote_obj in self.quote_obj_list:
            g_QuoteZMQ.subquote(g_QuoteSession, quote_obj)

        self.load_file_signal = False

    def save_file(self):
        path = filedialog.askdirectory()

        dt = datetime.datetime.now()
        dt = str(dt).split(' ')[0]
        result_path = path + '/' + dt + '.xls'

        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('sheet')

        def insert_row(row, vals):
            for col, val in enumerate(vals):
                worksheet.write(row, col, val)

        row_counter = 0
        headers = ['策略', '合约', '持仓数', '均价', '收益']
        insert_row(row_counter, headers)
        row_counter += 1

        for strategy in self.label_var.keys():
            for contract in self.label_var[strategy].keys():
                nums = int(self.label_var[strategy][contract]['持仓数'].get())
                avg_price = float(self.label_var[strategy][contract]['均价'].get())
                dynamic_profit = float(self.label_var[strategy][contract]['留仓损益'].get())
                fixed_profit = float(self.label_var[strategy][contract]['平仓损益'].get())
                row_vals = [strategy, contract, nums, avg_price, dynamic_profit,fixed_profit]
                insert_row(row_counter, row_vals)
                row_counter += 1


        try:
            if path !='':
                workbook.save(result_path)

            if os.path.exists(result_path):
                messagebox.showinfo(title='提示', message='文件已经保存成功！')
            else:
                messagebox.showerror(title='错误', message='文件保存失败！')
        except:
            messagebox.showerror(title='错误', message='文件保存失败，当前的路径没有权限！')

    def check_strategy_name(self):
        strategies = []
        with open('./strategies.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for strategy in lines:
                strategies.append(strategy.replace('\n', ''))

        root = Tk()
        root.iconbitmap(default=r'./pictures/logo.ico')

        root.resizable(0, 0)
        root.geometry("%dx%d+%d+%d" % (233, 233, 0, 0))
        root.title('盈利界面')

        for i, strategy in enumerate(strategies):
            Label(root, text=strategy).grid(row=i, column=0, sticky=E)

        root.mainloop()

    def modify_strategy_name(self):
        messagebox.showinfo(title='~', message='对不起，还在开发~')

    def init_profit_ui(self):

        root = Tk()
        root.iconbitmap(default=r'./pictures/logo.ico')

        root.resizable(0, 0)
        root.title('盈利界面')

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
        names = ['策略','合约','持仓数','均价', '留仓损益', '平仓损益','中价损益', '总收益', '买卖中价', '当前价格', '买一价', '卖一价']
        self.p_names = names
        for i,name in enumerate(names):
            Label(root, text=name).grid(row=0, column=i, sticky=E + W, pady=1)

        def callback():
            login_out = messagebox.askquestion(title='提示', message='是否需要关闭前保存文件？')

            if login_out == 'yes':
                self.save_file()
                return
            try:
                g_TradeZMQ.trade_logout(g_TradeSession)
                g_QuoteZMQ.quote_logout(g_QuoteSession)
            except:
                pass
            try:
                self.bs_root.destroy()
            except:
                pass

            root.destroy()

            global exit_signal
            exit_signal = 1

            os._exit(0)

        root.protocol("WM_DELETE_WINDOW", callback)

        root.mainloop()

    def open_bs_ui(self):

        self.p_refresh_signal.append(1)
        self.bs_refresh_signal.append(1)
        try:
            self.bs_root.destroy()
            self.init_buy_sell_ui()
        except:
            self.init_buy_sell_ui()

    def p_refresh(self):
        if len(self.add_new_signal) != 0:
            # 清空信号
            for i in range(len(self.add_new_signal) - 1, -1, -1):
                self.add_new_signal.pop(i)

            try:
                for box in self.boxlist:
                    box.grid_forget()
            except:
                pass

            self.boxlist = []
            i = 1
            j = 0
            total_profit_position = self.p_names.index('总收益')
            total_profit_row = 1

            for p, strategy in enumerate(list(self.label_var.keys())):

                color = self.colors[p]
                self.strategy_contain_contract_num[strategy] = len(list(self.label_var[strategy].keys()))

                for contract in self.label_var[strategy].keys():
                    for j, name in enumerate(self.p_names):
                        if name == '合约':
                            l = Label(self.p_root, text='',
                                  textvariable=self.label_var[strategy][contract][name],
                                  bg=color)
                            self.boxlist.append(l)
                            l.grid(row=i, column=j, sticky=E + W)

                        elif name in ['持仓数','留仓损益', '平仓损益']:
                            l = Label(self.p_root, text='',
                                  textvariable=self.label_var[strategy][contract][name],
                                  bg=color)
                            self.boxlist.append(l)
                            l.grid(row=i, column=j, sticky=E + W)
                        elif name != '总收益':
                            l = Label(self.p_root, text='',
                                  textvariable=self.label_var[strategy][contract][name],
                                  bg=color)
                            self.boxlist.append(l)
                            l.grid(row=i, column=j, sticky=E + W)

                    i += 1

                self.strategy2totalprofit[strategy] = StringVar(self.p_root)
                l = Label(self.p_root, text=1, height=self.strategy_contain_contract_num[strategy],
                          textvariable=self.strategy2totalprofit[strategy],bg=color)
                self.boxlist.append(l)
                l.grid(row=total_profit_row, column=total_profit_position,
                       rowspan=self.strategy_contain_contract_num[strategy]
                       , sticky=N + S)
                total_profit_row += self.strategy_contain_contract_num[strategy]

            b = Button(self.p_root, text='打开交易监控', width=10,command=self.open_bs_ui)
            b.grid(row=i, column= j, columnspan=2,sticky=E, padx=10, pady=10)
            self.boxlist.append(b)

        self.p_root.after(500, self.p_refresh)

    def p_update(self, quote):

        contract = quote['Symbol']
        try:
            lastprice = float(quote['TradingPrice'])
            bidPrice1 = float(quote['Bid'])
            askPrice1 = float(quote['Ask'])
        except:
            return

        price_conver = 0
        if 'SSE' in contract or 'SH' in contract or \
                'SZSE' in contract or 'SZ' in contract:
            price_conver = 10000
        elif 'CFFEX' in contract or 'CFE' in contract:
            if 'IO' in contract:
                price_conver = 100
            elif 'IF' in contract or 'IH' in contract:
                price_conver = 300

        try:
            for strategy in self.label_var.keys():
                if contract not in self.label_var[strategy].keys():
                    continue

                price = float(self.label_var[strategy][contract]['均价'].get())
                volume = int(self.label_var[strategy][contract]['持仓数'].get())
                prof = volume * (lastprice - price) * price_conver

                self.label_var[strategy][contract]['留仓损益'].set('{:g}'.format(prof))
                self.label_var[strategy][contract]['当前价格'].set('{:g}'.format(lastprice))

                if bidPrice1 > 9e9:
                    self.label_var[strategy][contract]['买一价'].set('')
                else:
                    self.label_var[strategy][contract]['买一价'].set('{:g}'.format(bidPrice1))

                if askPrice1 > 9e9:
                    self.label_var[strategy][contract]['卖一价'].set('')
                else:
                    self.label_var[strategy][contract]['卖一价'].set('{:g}'.format(askPrice1))

                avg_bid_ask = (askPrice1 + bidPrice1) / 2
                self.label_var[strategy][contract]['买卖中价'].set('{:g}'.format(avg_bid_ask))

                middle_pro = volume * (avg_bid_ask - price) * price_conver
                self.label_var[strategy][contract]['中价损益'].set('%0.1f' %middle_pro)

                total_profit = 0
                middle_price_profit = 0
                for val in self.label_var[strategy].keys():
                    total_profit = total_profit + \
                                   float(self.label_var[strategy][val]['留仓损益'].get()) + \
                                   float(self.label_var[strategy][val]['平仓损益'].get())

                    middle_price_profit = middle_price_profit + \
                                          float(self.label_var[strategy][val]['中价损益'].get()) + + \
                                          float(self.label_var[strategy][val]['平仓损益'].get())

                self.strategy2totalprofit[strategy].set('{}\n{}'.format(int(total_profit),
                                                                        int(middle_price_profit)))
        except:
            pass

    def init_buy_sell_ui(self):

        strategies = []
        with open('./strategies.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for strategy in lines:
                strategies.append(strategy.replace('\n',''))

        self.strategies = sorted(set(strategies), key=strategies.index)

        root = Tk()
        root.title('交易监控')
        root.geometry("%dx%d+%d+%d" % (680, 500, 0, 0))
        canvas = Canvas(root, borderwidth=0)
        frame = Frame(canvas)
        self.bs_root = frame
        vsb = Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((4, 4), window=frame, anchor="nw")

        def onFrameConfigure(canvas):
            '''Reset the scroll region to encompass the inner frame'''
            canvas.configure(scrollregion=canvas.bbox("all"))

        frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))

        names = ['交易时间', '成交类型','数量', '价格', '合约']
        self.bs_names = names

        for i, name in enumerate(names):
            Label(frame, text=name).grid(row=0, column=i, sticky=E + W, padx=10)

        self.bs_refresh()
        root.mainloop()

    def bs_refresh(self):

        if len(self.bs_refresh_signal) != 0:
            # 清空信号
            for i in range(len(self.bs_refresh_signal) - 1, -1, -1):
                self.bs_refresh_signal.pop(i)

            try:
                for k in self.bs_boxlist.keys():
                    for box in self.bs_boxlist[k]:
                        box.grid_forget()
                self.bs_boxlist = {0:[]}
            except:
                pass

            j = 1
            for i, k1 in enumerate(self.buy_sell_var.keys()):
                self.bs_boxlist[i+1] = []
                for j, k2 in enumerate(self.buy_sell_var[k1].keys()):
                    l = Label(self.bs_root, text=self.buy_sell_var[k1][k2])
                    self.bs_boxlist[i+1].append(l)
                    l.grid(row=i + 1, column=j, sticky=E + W, padx=10)

                self.checkbutton_context_list[i+1] = {}
                self.checkbutton_context_list[i+1][0] = IntVar(self.bs_root)
                l = Checkbutton(self.bs_root,variable=self.checkbutton_context_list[i+1][0])
                self.checkbutton_context_list[i+1][1] = l
                self.bs_boxlist[i + 1].append(l)
                l.grid(row=i + 1, column=j + 1, sticky=E + W, padx=10)

            if j != 0:

                self.bs_boxlist[i+2] = []
                number = StringVar()
                numberChosen = ttk.Combobox(self.bs_root, width=10, textvariable=number)
                numberChosen['values'] = [strategy for strategy in self.strategies]  # 设置下拉列表的值
                numberChosen.grid(column=j-1, row=len(self.buy_sell_var.keys()) + 2, padx=5)  # 设置其在界面中出现的位置  column代表列   row 代表行
                numberChosen.current(0)
                self.bs_boxlist[i+2].append(numberChosen)

                b = Button(self.bs_root, text="全选", command=self.all_select, width=10)
                b.grid(row=len(self.buy_sell_var.keys()) + 2, column=j, sticky=E, padx=5, pady=10)
                self.bs_boxlist[i + 2].append(b)

                b = Button(self.bs_root, text="更新", command=self.bs_update, width=10)
                b.grid(row=len(self.buy_sell_var.keys()) + 2, column=j+1, sticky=E, padx=5, pady=10)
                self.bs_boxlist[i+2].append(b)

        self.bs_root.after(1000, self.bs_refresh)

    def all_select(self):
        for k in self.checkbutton_context_list.keys():
            self.checkbutton_context_list[k][1].select()

    def check_buy_sell(self, quote):

        print(quote)
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

        if id == '' or Price == 0.0:
            return

        flag = False

        if quote['ExecType'] in ['3','6']:
            if id not in self.strategy_trade_return.keys():
                if cumqty != 0:
                    Volume = cumqty
                    flag = True

                self.strategy_trade_return[id] = leavesqty

            else:
                Volume = self.strategy_trade_return[id] - leavesqty
                self.strategy_trade_return[id] = leavesqty
                flag = True

        if flag:
            print('******', quote)

            if Volume == 0:
                return

            if Price == 0.0:
                return

            self.buy_sell_var[len(self.buy_sell_var) + 1] = {}
            self.buy_sell_var[len(self.buy_sell_var)]['交易时间'] = TradeTime
            t = [{1: '买', 2: '卖'}]
            self.buy_sell_var[len(self.buy_sell_var)]['成交类型'] = t[0][int(Direction)]
            self.buy_sell_var[len(self.buy_sell_var)]['数量'] = Volume
            self.buy_sell_var[len(self.buy_sell_var)]['价格'] = '%f'%Price
            self.buy_sell_var[len(self.buy_sell_var)]['合约'] = contract

            self.bs_refresh_signal.append(1)

    def bs_update(self):

        login_out = messagebox.askquestion(title='提示', message='选对了策略吗？确定更新？')

        if login_out != 'yes':
            return

        ks = []

        for i, k1 in enumerate(self.buy_sell_var.keys()):

            if self.checkbutton_context_list[i+1][0].get() == 0:
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

            strategy = self.bs_boxlist[len(self.buy_sell_var.keys())+1][0].get()

            bs_price = float(self.buy_sell_var[k1]['价格'])
            bs_volume = int(self.buy_sell_var[k1]['数量'])
            bs_type = self.buy_sell_var[k1]['成交类型']


            if strategy not in self.label_var.keys() or \
                    contract not in self.label_var[strategy].keys():
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
        nums = [i+1 for i in range(len(self.buy_sell_var.keys()))]
        temp = {}
        for i,k in zip(nums,self.buy_sell_var.keys()):
            temp[i]=self.buy_sell_var[k]
        self.buy_sell_var = temp

        self.bs_refresh_signal.append(1)

    def add(self, strategy,contract):

        names = ['策略', '合约', '持仓数', '均价', '留仓损益', '平仓损益','中价损益','买卖中价', '当前价格', '买一价', '卖一价']
        init_data = [0 for _ in names]
        init_data[0], init_data[1] = strategy, contract

        quote_obj = {"Symbol": contract, "SubDataType": "REALTIME", }
        g_QuoteZMQ.subquote(g_QuoteSession, quote_obj)

        if strategy not in self.label_var.keys():
            self.label_var[strategy] = {}
            self.strategy2totalprofit[strategy] = StringVar(self.p_root)

        if contract not in self.label_var[strategy].keys():
            self.label_var[strategy][contract] = {}
            for j, name in enumerate(names):
                self.label_var[strategy][contract][name] = StringVar(self.p_root)
                self.label_var[strategy][contract][name].set(init_data[j])

        self.add_new_signal.append(1)

MY = monitor_yield()

def OnRealTimeQuote(Quote):
    MY.p_update(Quote)

def OnGreeks(greek):
    print(greek)

def OnGetAccount(account):
    print(account["BrokerID"])

def OnexeReport(report):
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

def ShowEXECUTIONREPORT(ZMQ,SessionKey,reportData):
    if reportData["Reply"] == "RESTOREREPORT":
        Orders = reportData["Orders"]
        if len(Orders) == 0:
            return

        last = ""
        for data in Orders:
            last = data
            print(data["ReportID"])

        reportData = g_TradeZMQ.restore_report(SessionKey,last["QryIndex"])
        ShowEXECUTIONREPORT(g_TradeZMQ,SessionKey,reportData)

def ShowPOSITIONS(ZMQ,SessionKey,AccountMask,positionData):
    if positionData["Reply"] == "POSITIONS":
        position = positionData["Positions"]
        if len(position) == 0:
            return

        last = ""
        for data in position:
            last = data
            print("position:" + data["Symbol"])

        positionData = g_TradeZMQ.position(SessionKey,AccountMask,last["QryIndex"])
        ShowPOSITIONS(g_TradeZMQ,SessionKey,AccountMask,positionData)

def quote_sub_th(obj,q_data,filter = ""):
    socket_sub = obj.context.socket(zmq.SUB)
    #socket_sub.RCVTIMEO=7000
    #print(sub_port)
    socket_sub.connect("tcp://127.0.0.1:%s" % q_data["SubPort"])
    socket_sub.setsockopt_string(zmq.SUBSCRIBE,filter)
    while(True):

        if exit_signal:
            return

        message = (socket_sub.recv()[:-1]).decode("utf-8")
        index =  re.search(":",message).span()[1]  # filter
        symbol = message[:index-1]
        # print("symbol get ",symbol)

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
    orders_obj = {
    "Symbol":"TC.O.SSE.510050.202001.P.2.95",
    "BrokerID":"",
    "Account":"",
    "Price":"0.0215",
    "TimeInForce":"1",
    "Side":"1",
    "OrderType":"2",
    "OrderQty":"1",
    "PositionEffect":"0"
    }

    History_obj = {
        "Symbol": "TC.F.CFFEX.IF.HOT",
        "SubDataType":"1K",
        "StartTime" : "2019030500",
        "EndTime" : "2019030700"
    }

    global g_TradeZMQ
    global g_QuoteZMQ
    global g_TradeSession
    global g_QuoteSession

    g_TradeZMQ = tcore_zmq()
    g_QuoteZMQ = tcore_zmq()
    t_data = g_TradeZMQ.trade_connect("51879")
    q_data = g_QuoteZMQ.quote_connect("51909")

    if t_data["Success"] != "OK":
        print("[quote]connection failed")
        return

    if t_data["Success"] != "OK":
        print("[trade]connection failed")
        return		

    g_TradeSession = t_data["SessionKey"]
    g_QuoteSession = q_data["SessionKey"]

    t1 = threading.Thread(target = trade_sub_th,args=(g_TradeZMQ,t_data["SubPort"],))
    t1.start()

    #quote
    t2 = threading.Thread(target = quote_sub_th,args=(g_QuoteZMQ,q_data,))
    t2.start()

if __name__ == '__main__':
    MY.init_profit_ui()