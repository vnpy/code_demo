from PySide6 import QtWidgets

from vnpy.event import EventEngine
from vnpy_ctp import CtpGateway
from vnpy_ib import IbGateway

from ui import SimpleWidget
from engine import StrategyEngine


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

    engine: StrategyEngine = StrategyEngine(event_engine, gateway)      # noqa

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
