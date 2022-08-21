from PySide6 import QtWidgets

from vnpy.event import EventEngine, Event
from vnpy_ctp.api import MdApi


class SimpleWidget(QtWidgets.QWidget):
    """简单图形控件"""

    def __init__(self, event_engine: EventEngine) -> None:
        """构造函数"""
        super().__init__()      # 这里要首先调用Qt对象C++中的构造函数

        self.event_engine: EventEngine = event_engine
        self.event_engine.register("log", self.update_log)

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

    def write_log(self, msg: str) -> None:
        """"""
        event: Event = Event("log", msg)
        self.event_engine.put(event)


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

    # 创建API实例
    api: CtpMdApi = CtpMdApi(event_engine)

    # 初始化底层
    api.createFtdcMdApi(".")

    # 注册服务器地址
    api.registerFront("tcp://180.168.146.187:10131")

    # 发起连接
    api.init()

    # 启动主线程UI循环
    app.exec()

    # 关闭事件引擎
    event_engine.stop()


if __name__ == "__main__":
    main()
