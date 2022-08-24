from PySide6 import QtWidgets

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy_ib import IbGateway

from ui import SimpleWidget
from engine import StrategyEngine


def main():
    """主函数"""
    # 创建Qt应用
    app: QtWidgets.QApplication = QtWidgets.QApplication()

    # 创建并启动事件引擎
    event_engine: EventEngine = EventEngine()

    # 创建主引擎
    main_engine: MainEngine = MainEngine(event_engine)
    main_engine.add_gateway(CtpGateway)
    main_engine.add_gateway(IbGateway)

    # 创建策略引擎
    engine: StrategyEngine = StrategyEngine(main_engine, event_engine)      # noqa

    # 创建图形控件
    widget: SimpleWidget = SimpleWidget(main_engine, event_engine)
    widget.show()

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
    main_engine.connect(ctp_setting, "CTP")

    # 启动主线程UI循环
    app.exec()

    # 关闭主引擎
    main_engine.close()


if __name__ == "__main__":
    main()
