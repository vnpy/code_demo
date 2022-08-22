from threading import Thread
from datetime import datetime

from PySide6 import QtWidgets
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.common import TickAttrib, TickerId
from ibapi.ticktype import TickType
from ibapi.contract import Contract

from vnpy.event import EventEngine, Event
from vnpy.trader.constant import Exchange
from vnpy.trader.object import TickData
from vnpy.trader.event import EVENT_LOG
from vnpy_ctp.api import MdApi


class SimpleWidget(QtWidgets.QWidget):
    """简单图形控件"""

    def __init__(self, event_engine: EventEngine) -> None:
        """构造函数"""
        super().__init__()      # 这里要首先调用Qt对象C++中的构造函数

        self.event_engine: EventEngine = event_engine
        self.event_engine.register(EVENT_LOG, self.update_log)

        # 用于绑定API对象
        self.api = None

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
        symbol: str = self.symbol_line.text()

        self.api.subscribeMarketData(symbol)

        # self.api.subscribe(symbol)

    def update_log(self, event: Event) -> None:
        """更新日志"""
        msg: str = event.data
        self.log_monitor.append(msg)


class CtpMdApi(MdApi):
    """实现行情API"""

    def __init__(self, event_engine: EventEngine) -> None:
        """"""
        super().__init__()

        self.event_engine: EventEngine = event_engine

    def onFrontConnected(self) -> None:
        """服务器连接成功回报"""
        self.write_log("行情服务器连接成功")

        # 发起登录操作
        ctp_req: dict = {
            "UserID": "000300",
            "Password": "vnpy1234",
            "BrokerID": "9999"
        }
        self.reqUserLogin(ctp_req, 1)

    def onFrontDisconnected(self, reason: int) -> None:
        """服务器连接断开回报"""
        self.write_log(f"行情服务器连接断开{reason}")

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """用户登录请求回报"""
        if not error["ErrorID"]:
            self.write_log("行情服务器登录成功")
        else:
            self.write_log(f"行情服务器登录失败{error}")

    def onRtnDepthMarketData(self, data: dict) -> None:
        """行情数据推送回调"""
        self.write_log(str(data))

        timestamp: str = f"{data['ActionDay']} {data['UpdateTime']}.{int(data['UpdateMillisec']/100)}"
        dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S.%f")

        tick: TickData = TickData(
            symbol=data["InstrumentID"],
            exchange=Exchange.SHFE,
            datetime=dt,
            volume=data["Volume"],
            turnover=data["Turnover"],
            open_interest=data["OpenInterest"],
            last_price=data["LastPrice"],
            limit_up=data["UpperLimitPrice"],
            limit_down=data["LowerLimitPrice"],
            open_price=data["OpenPrice"],
            high_price=data["HighestPrice"],
            low_price=data["LowestPrice"],
            pre_close=data["PreClosePrice"],
            bid_price_1=data["BidPrice1"],
            ask_price_1=data["AskPrice1"],
            bid_volume_1=data["BidVolume1"],
            ask_volume_1=data["AskVolume1"],
            gateway_name="CTP"
        )

        self.write_log(str(tick))

    def write_log(self, msg: str) -> None:
        """输出日志信息"""
        event: Event = Event(EVENT_LOG, msg)
        self.event_engine.put(event)


class IbApi(EWrapper):
    """IB的API实现"""

    def __init__(self, event_engine: EventEngine):
        """"""
        super().__init__()

        self.event_engine: EventEngine = event_engine

        self.client: EClient = EClient(self)
        self.reqid: int = 0

        self.close = self.client.disconnect

    def connectAck(self) -> None:
        """连接成功回报"""
        self.write_log("IB TWS连接成功")

    def connectionClosed(self) -> None:
        """连接断开回报"""
        self.write_log("IB TWS连接断开")

    def tickPrice(
        self,
        reqId: TickerId,
        tickType: TickType,
        price: float,
        attrib: TickAttrib
    ) -> None:
        """tick价格更新回报"""
        super().tickPrice(reqId, tickType, price, attrib)

        self.write_log(f"{reqId} {tickType}: {price}")

    def tickSize(
        self,
        reqId: TickerId,
        tickType: TickType,
        size: int
    ) -> None:
        """tick数量更新回报"""
        super().tickSize(reqId, tickType, size)

        self.write_log(f"{reqId} {tickType}: {size}")

    def tickString(
        self,
        reqId: TickerId,
        tickType: TickType,
        value: str
    ) -> None:
        """tick字符串更新回报"""
        super().tickString(reqId, tickType, value)

        self.write_log(f"{reqId} {tickType}: {value}")

    def write_log(self, msg: str) -> None:
        """输出日志信息"""
        event: Event = Event(EVENT_LOG, msg)
        self.event_engine.put(event)

    def connect(self, host: str, port: int, clientid: int) -> None:
        """连接TWS"""
        self.client.connect(host, port, clientid)
        self.thread = Thread(target=self.client.run)
        self.thread.start()

    def subscribe(self, symbol: str) -> None:
        """订阅美股聚合行情"""
        ib_contract: Contract = Contract()
        ib_contract.exchange = "SMART"
        ib_contract.secType = "CMDTY"
        ib_contract.currency = "USD"
        ib_contract.symbol = symbol

        self.reqid += 1
        self.client.reqMktData(self.reqid, ib_contract, "", False, False, [])


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

    # CTP API
    ctp_api: CtpMdApi = CtpMdApi(event_engine)
    ctp_api.createFtdcMdApi(".")
    ctp_api.registerFront("tcp://180.168.146.187:10131")
    ctp_api.init()
    widget.api = ctp_api

    # IB API
    # ib_api: IbApi = IbApi(event_engine)
    # ib_api.connect("localhost", 7497, 1)
    # widget.api = ib_api

    # 启动主线程UI循环
    app.exec()

    # 关闭事件引擎
    event_engine.stop()

#    ib_api.close()


if __name__ == "__main__":
    main()
