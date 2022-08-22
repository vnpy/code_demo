from PySide6 import QtWidgets

from vnpy.event import EventEngine, Event
from vnpy.trader.event import EVENT_LOG, EVENT_TICK
from vnpy.trader.constant import Exchange
from vnpy.trader.object import TickData, LogData, SubscribeRequest
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
    # ctp_setting = {
    #     "用户名": "000300",
    #     "密码": "vnpy1234",
    #     "经纪商代码": "9999",
    #     "交易服务器": "180.168.146.187:10130",
    #     "行情服务器": "180.168.146.187:10131",
    #     "产品名称": "simnow_client_test",
    #     "授权编码": "0000000000000000"
    # }
    # ctp_gateway = CtpGateway(event_engine, "CTP")
    # ctp_gateway.connect(ctp_setting)
    # widget.gateway = gateway = ctp_gateway

    # IB交易接口
    ib_setting = {
        "TWS地址": "127.0.0.1",
        "TWS端口": 7497,
        "客户号": 1,
        "交易账户": ""
    }
    ib_gateway = IbGateway(event_engine, "IB")
    ib_gateway.connect(ib_setting)
    widget.gateway = gateway = ib_gateway

    # 启动主线程UI循环
    app.exec()

    # 关闭事件引擎
    event_engine.stop()

    gateway.close()


if __name__ == "__main__":
    main()
