from PySide6 import QtWidgets, QtCore

from vnpy.event import EventEngine, Event
from vnpy.trader.event import (
    EVENT_LOG
)
from vnpy.trader.constant import (
    Exchange
)
from vnpy.trader.object import (
    TickData, LogData, SubscribeRequest
)
from vnpy.trader.engine import MainEngine

from base import EVENT_STRATEGY


class SimpleWidget(QtWidgets.QWidget):
    """简单图形控件"""

    signal_log = QtCore.Signal(Event)
    signal_tick = QtCore.Signal(Event)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """构造函数"""
        super().__init__()      # 这里要首先调用Qt对象C++中的构造函数

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine

        # 连接信号槽
        self.signal_log.connect(self.process_log_event)
        self.signal_tick.connect(self.process_tick_event)

        self.event_engine.register(EVENT_LOG, self.signal_log.emit)
        # self.event_engine.register(EVENT_TICK, self.signal_tick.emit)

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
