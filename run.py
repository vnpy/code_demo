from PySide6 import QtWidgets

from vnpy_ctp.api import MdApi


class CtpMdApi(MdApi):
    """实现行情API"""

    def __init__(self, log_monitor):
        """"""
        super().__init__()

        self.log_monitor = log_monitor

    def onFrontConnected(self):
        """服务器连接成功回报"""
        self.write_log("行情服务器连接成功")

        # 发起登录操作
        ctp_req: dict = {
            "UserID": "000300",
            "Password": "vnpy1234",
            "BrokerID": "9999"
        }
        self.reqUserLogin(ctp_req, 1)

    def onFrontDisconnected(self, reason):
        """服务器连接断开回报"""
        self.write_log(f"行情服务器连接断开{reason}")

    def onRspUserLogin(self, data, error, reqid, last):
        """用户登录请求回报"""
        if not error["ErrorID"]:
            self.write_log("行情服务器登录成功")

            # 订阅行情推送
            self.subscribeMarketData("rb2301")
        else:
            self.write_log(f"行情服务器登录失败{error}")

    def onRtnDepthMarketData(self, data):
        """行情数据推送回调"""
        self.write_log(str(data))

    def write_log(self, msg):
        """"""
        self.log_monitor.append(msg)


def main():
    """主函数"""
    # 创建Qt应用
    app = QtWidgets.QApplication()

    # 创建日志监控组件
    log_monitor = QtWidgets.QTextEdit()
    log_monitor.show()

    # 创建实例
    api = CtpMdApi(log_monitor)

    # 初始化底层
    api.createFtdcMdApi(".")

    # 注册服务器地址
    api.registerFront("tcp://180.168.146.187:10131")

    # 发起连接
    api.init()

    # 启动主线程UI循环
    app.exec()


if __name__ == "__main__":
    main()
