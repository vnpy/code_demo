import json
from collections import defaultdict

from PySide6 import QtWidgets, QtCore

from vnpy.event import EventEngine, Event
from vnpy.trader.event import (
    EVENT_LOG, EVENT_TICK,
    EVENT_CONTRACT, EVENT_POSITION,
    EVENT_TIMER
)
from vnpy.trader.constant import (
    Exchange, Direction, OrderType, Offset
)
from vnpy.trader.object import (
    TickData, LogData, SubscribeRequest,
    ContractData, PositionData, OrderRequest
)
from vnpy.trader.gateway import BaseGateway
from vnpy_ctp import CtpGateway
from vnpy_ib import IbGateway


EVENT_STRATEGY = "eMyStrategy"


class SimpleWidget(QtWidgets.QWidget):
    """简单图形控件"""

    signal_log = QtCore.Signal(Event)
    signal_tick = QtCore.Signal(Event)

    def __init__(self, event_engine: EventEngine) -> None:
        """构造函数"""
        super().__init__()      # 这里要首先调用Qt对象C++中的构造函数

        # 连接信号槽
        self.signal_log.connect(self.process_log_event)
        self.signal_tick.connect(self.process_tick_event)

        self.event_engine: EventEngine = event_engine
        self.event_engine.register(EVENT_LOG, self.signal_log.emit)
        # self.event_engine.register(EVENT_TICK, self.signal_tick.emit)

        # 用于绑定API对象
        self.gateway: BaseGateway = None

        # 基础图形控件
        self.log_monitor: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.subscribe_button: QtWidgets.QPushButton = QtWidgets.QPushButton("订阅")
        self.symbol_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        self.strategy_monitor: StrategyMonitor = StrategyMonitor(event_engine)

        # 连接按钮函数
        self.subscribe_button.clicked.connect(self.subscribe_symbol)

        # 设置布局组合
        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.log_monitor)
        vbox.addWidget(self.symbol_line)
        vbox.addWidget(self.subscribe_button)
        vbox.addWidget(self.strategy_monitor)

        self.setLayout(vbox)

    def subscribe_symbol(self) -> None:
        """订阅行情"""
        vt_symbol: str = self.symbol_line.text()
        symbol, exchange_str = vt_symbol.split(".")

        req = SubscribeRequest(
            symbol=symbol,
            exchange=Exchange(exchange_str)
        )
        self.gateway.subscribe(req)

    def process_log_event(self, event: Event) -> None:
        """更新日志"""
        log: LogData = event.data
        self.log_monitor.append(log.msg)

    def process_tick_event(self, event: Event) -> None:
        """更新行情"""
        tick: TickData = event.data
        self.log_monitor.append(str(tick))


class StrategyEngine:
    """策略引擎"""

    def __init__(self, event_engine: EventEngine, gateway: BaseGateway) -> None:
        """"""
        self.event_engine: EventEngine = event_engine
        self.gateway: BaseGateway = gateway

        self.ticks: dict[str, TickData] = {}
        self.contracts: dict[str, ContractData] = {}
        self.positions: dict[str, PositionData] = {}
        self.subscribed: set[str] = set()

        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)
        self.event_engine.register(EVENT_POSITION, self.process_position_event)
        # self.event_engine.register(EVENT_TIMER, self.process_timer_event)
        self.event_engine.register(EVENT_LOG, self.process_log_event)

        self.tick_history: dict[str, list[TickData]] = defaultdict(list)
        self.trading_symbols: set[str] = set()
        self.trading_targets: dict[str, int] = defaultdict(int)

        self.load_setting()

    def load_setting(self) -> None:
        """加载交易代码配置"""
        with open("setting.json") as f:
            vt_symbols = json.load(f)
            for s in vt_symbols:
                self.trading_symbols.add(s)

    def process_tick_event(self, event: Event) -> None:
        """行情事件"""
        tick: TickData = event.data
        self.ticks[tick.vt_symbol] = tick

        # 缓存交易合约的Tick历史
        if tick.vt_symbol in self.trading_symbols:
            history: list[TickData] = self.tick_history[tick.vt_symbol]
            history.append(tick)

            self.run_trading(tick.vt_symbol)

    def process_contract_event(self, event: Event) -> None:
        """合约事件"""
        contract: ContractData = event.data
        self.contracts[contract.vt_symbol] = contract

        # 订阅策略合约行情
        if contract.vt_symbol in self.trading_symbols:
            req = SubscribeRequest(contract.symbol, contract.exchange)
            self.gateway.subscribe(req)

    def process_position_event(self, event: Event) -> None:
        """持仓事件"""
        position: PositionData = event.data
        self.positions[position.vt_positionid] = position

        # 如果已经订阅，则跳过
        if position.vt_symbol in self.subscribed:
            return

        # 如果没收到合约，则跳过
        contract = self.contracts.get(position.vt_symbol, None)
        if not contract:
            return

        # 订阅行情
        req: SubscribeRequest = SubscribeRequest(
            contract.symbol, contract.exchange
        )
        self.gateway.subscribe(req)

        # 记录信息
        self.subscribed.add(position.vt_symbol)

    def process_timer_event(self, event: Event) -> None:
        """定时事件"""
        self.calculate_value()

    def process_log_event(self, event: Event) -> None:
        """日志事件"""
        print(event.data.msg)

    def calculate_value(self) -> None:
        """计算市值"""
        for position in self.positions.values():
            tick: TickData = self.ticks.get(position.vt_symbol, None)
            contract: ContractData = self.contracts.get(position.vt_symbol, None)

            # 如果缺失行情或者合约，则跳过计算
            if not tick or not contract:
                continue

            value = position.volume * tick.last_price * contract.size
            print(f"{position.vt_symbol} {position.direction}当前持仓市值{value}")

    def run_trading(self, vt_symbol: str) -> None:
        """执行策略交易"""
        # 检查至少要3个Tick
        history = self.tick_history[vt_symbol]
        if len(history) < 3:
            return

        # 提取行情和合约
        tick1 = history[-1]
        tick2 = history[-2]
        tick3 = history[-3]

        contract = self.contracts[vt_symbol]

        # print(tick1.datetime, tick1.last_price, self.trading_target)

        # 多头检查
        if tick1.last_price > tick2.last_price > tick3.last_price:
            if not self.trading_targets[vt_symbol]:
                req = OrderRequest(
                    symbol=contract.symbol,
                    exchange=contract.exchange,
                    direction=Direction.LONG,
                    type=OrderType.LIMIT,
                    price=tick1.last_price + 10,
                    volume=1,
                    offset=Offset.OPEN
                )
                self.gateway.send_order(req)

                self.trading_targets[vt_symbol] = 1
                self.write_log(f"{vt_symbol}买入开仓1手 {tick1.datetime}")

        # 空头检查
        if tick1.last_price < tick2.last_price < tick3.last_price:
            if self.trading_targets[vt_symbol] > 0:
                req = OrderRequest(
                    symbol=contract.symbol,
                    exchange=contract.exchange,
                    direction=Direction.SHORT,
                    type=OrderType.LIMIT,
                    price=tick1.last_price - 10,
                    volume=1,
                    offset=Offset.CLOSE
                )
                self.gateway.send_order(req)

                self.trading_targets[vt_symbol] = 0
                self.write_log(f"{vt_symbol}卖出平仓1手 {tick1.datetime}")

        # 推送事件
        event = Event(
            type=EVENT_STRATEGY,
            data={
                "vt_symbol": vt_symbol,
                "datetime": tick1.datetime,
                "last_price": tick1.last_price,
                "trading_target": self.trading_targets[vt_symbol]
            }
        )
        self.event_engine.put(event)

    def write_log(self, msg: str) -> None:
        """输出日志"""
        log = LogData(msg=msg, gateway_name="STRATEGY")
        event = Event(EVENT_LOG, log)
        self.event_engine.put(event)


class StrategyMonitor(QtWidgets.QTableWidget):
    """策略监控表格"""

    signal = QtCore.Signal(Event)

    def __init__(self, event_engine: EventEngine) -> None:
        """"""
        super().__init__()

        self.signal.connect(self.process_strategy_event)
        self.event_engine: EventEngine = event_engine
        self.event_engine.register(EVENT_STRATEGY, self.signal.emit)

        labels = ["代码", "最新价", "时间", "目标仓位"]
        self.setColumnCount(len(labels))
        self.setHorizontalHeaderLabels(labels)      # 水平表头文字
        self.verticalHeader().setVisible(False)     # 垂直表头隐藏
        self.setEditTriggers(self.NoEditTriggers)   # 禁止内容编辑

        self.rows: dict[str, dict[str, QtWidgets.QTableWidgetItem]] = {}

    def process_strategy_event(self, event: Event) -> None:
        """处理策略事件"""
        data: dict = event.data
        print("strategy", data)

        # 如果是新收到的策略数据，则插入一行
        if data["vt_symbol"] not in self.rows:
            self.insertRow(0)

            symbol_cell = QtWidgets.QTableWidgetItem(str(data["vt_symbol"]))
            datetime_cell = QtWidgets.QTableWidgetItem(str(data["datetime"]))
            price_cell = QtWidgets.QTableWidgetItem(str(data["last_price"]))
            target_cell = QtWidgets.QTableWidgetItem(str(data["trading_target"]))

            self.setItem(0, 0, symbol_cell)
            self.setItem(0, 1, datetime_cell)
            self.setItem(0, 2, price_cell)
            self.setItem(0, 3, target_cell)

            self.rows[data["vt_symbol"]] = {
                "vt_symbol": symbol_cell,
                "datetime": datetime_cell,
                "last_price": price_cell,
                "trading_target": target_cell
            }
        # 如果是已有的策略数据，则直接更新
        else:
            row = self.rows[data["vt_symbol"]]

            row["vt_symbol"].setText(str(data["vt_symbol"]))
            row["datetime"].setText(str(data["datetime"]))
            row["last_price"].setText(str(data["last_price"]))
            row["trading_target"].setText(str(data["trading_target"]))


def main():
    """主函数"""
    # 创建并启动事件引擎
    event_engine: EventEngine = EventEngine()
    event_engine.start()

    # 创建Qt应用
    app: QtWidgets.QApplication = QtWidgets.QApplication()

    # 创建图形控件
    widget: SimpleWidget = SimpleWidget(event_engine)
    widget.show()

    # CTP交易接口
    ctp_setting = {
        "用户名": "000300",
        "密码": "vnpy1234",
        "经纪商代码": "9999",
        "交易服务器": "180.168.146.187:10201",
        "行情服务器": "180.168.146.187:10211",
        "产品名称": "simnow_client_test",
        "授权编码": "0000000000000000"
    }
    ctp_gateway = CtpGateway(event_engine, "CTP")
    ctp_gateway.connect(ctp_setting)
    gateway = ctp_gateway
    widget.gateway = ctp_gateway

    engine: StrategyEngine = StrategyEngine(event_engine, gateway)

    # IB交易接口
    # ib_setting = {
    #     "TWS地址": "127.0.0.1",
    #     "TWS端口": 7497,
    #     "客户号": 1,
    #     "交易账户": ""
    # }
    # ib_gateway = IbGateway(event_engine, "IB")
    # ib_gateway.connect(ib_setting)
    # widget.gateway = gateway = ib_gateway

    # 启动主线程UI循环
    app.exec()

    # input()

    # 关闭事件引擎
    event_engine.stop()

    gateway.close()


if __name__ == "__main__":
    main()
