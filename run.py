from PySide6 import QtWidgets

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


class SimpleWidget(QtWidgets.QWidget):
    """简单图形控件"""

    def __init__(self, event_engine: EventEngine) -> None:
        """构造函数"""
        super().__init__()      # 这里要首先调用Qt对象C++中的构造函数

        self.event_engine: EventEngine = event_engine
        self.event_engine.register(EVENT_LOG, self.process_log_event)
        self.event_engine.register(EVENT_TICK, self.process_tick_event)

        # 用于绑定API对象
        self.gateway: BaseGateway = None

        # 基础图形控件
        self.log_monitor: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.subscribe_button: QtWidgets.QPushButton = QtWidgets.QPushButton("订阅")
        self.symbol_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        # 连接按钮函数
        self.subscribe_button.clicked.connect(self.subscribe_symbol)

        # 设置布局组合
        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.log_monitor)
        vbox.addWidget(self.symbol_line)
        vbox.addWidget(self.subscribe_button)

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


class MonitorEngine:
    """监控引擎"""

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

        self.tick_history: list[TickData] = []
        self.trading_symbol: str = "IF2209.CFFEX"
        self.trading_target: int = 0

    def process_tick_event(self, event: Event) -> None:
        """行情事件"""
        tick: TickData = event.data
        self.ticks[tick.vt_symbol] = tick

        # 缓存交易合约的Tick历史
        if tick.vt_symbol == self.trading_symbol:
            self.tick_history.append(tick)

            self.run_trading()

    def process_contract_event(self, event: Event) -> None:
        """合约事件"""
        contract: ContractData = event.data
        self.contracts[contract.vt_symbol] = contract

        # 订阅策略合约行情
        if contract.vt_symbol == self.trading_symbol:
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

    def run_trading(self) -> None:
        """执行策略交易"""
        # 检查至少要3个Tick
        if len(self.tick_history) < 3:
            return

        # 提取行情和合约
        tick1 = self.tick_history[-1]
        tick2 = self.tick_history[-2]
        tick3 = self.tick_history[-3]

        contract = self.contracts[self.trading_symbol]

        # print(tick1.datetime, tick1.last_price, self.trading_target)

        # 多头检查
        if tick1.last_price > tick2.last_price > tick3.last_price:
            if not self.trading_target:
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

                self.trading_target = 1
                print(f"{self.trading_symbol}买入开仓1手", tick1.datetime)

        # 空头检查
        if tick1.last_price < tick2.last_price < tick3.last_price:
            if self.trading_target > 0:
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

                self.trading_target = 0
                print(f"{self.trading_symbol}卖出平仓1手", tick1.datetime)


def main():
    """主函数"""
    # 创建并启动事件引擎
    event_engine: EventEngine = EventEngine()
    event_engine.start()

    # 创建Qt应用
    # app: QtWidgets.QApplication = QtWidgets.QApplication()

    # 创建图形控件
    # widget: SimpleWidget = SimpleWidget(event_engine)
    # widget.show()

    # CTP交易接口
    ctp_setting = {
        "用户名": "000300",
        "密码": "vnpy1234",
        "经纪商代码": "9999",
        "交易服务器": "180.168.146.187:10130",
        "行情服务器": "180.168.146.187:10131",
        "产品名称": "simnow_client_test",
        "授权编码": "0000000000000000"
    }
    ctp_gateway = CtpGateway(event_engine, "CTP")
    ctp_gateway.connect(ctp_setting)
    gateway = ctp_gateway
    # widget.gateway = ctp_gateway

    engine: MonitorEngine = MonitorEngine(event_engine, gateway)

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
    # app.exec()

    input()

    # 关闭事件引擎
    event_engine.stop()

    gateway.close()


if __name__ == "__main__":
    main()
