from vnpy_ctp.api import MdApi


class CtpMdApi(MdApi):
    """实现行情API"""

    def __init__(self):
        """"""
        super().__init__()

    def onFrontConnected(self):
        """服务器连接成功回报"""
        print("行情服务器连接成功")

        # 发起登录操作
        ctp_req: dict = {
            "UserID": "000300",
            "Password": "vnpy1234",
            "BrokerID": "9999"
        }
        self.reqUserLogin(ctp_req, 1)

    def onFrontDisconnected(self, reason):
        """服务器连接断开回报"""
        print("行情服务器连接断开", reason)

    def onRspUserLogin(self, data, error, reqid, last):
        """用户登录请求回报"""
        if not error["ErrorID"]:
            print("行情服务器登录成功")

            # 订阅行情推送
            self.subscribeMarketData("rb2301")
        else:
            print("行情服务器登录失败", error)

    def onRtnDepthMarketData(self, data):
        """行情数据推送回调"""
        print(data)


def main():
    """主函数"""
    # 创建实例
    api = CtpMdApi()

    # 初始化底层
    api.createFtdcMdApi(".")

    # 注册服务器地址
    api.registerFront("tcp://180.168.146.187:10131")

    # 发起连接
    api.init()

    # 阻塞主线程推出
    input()


if __name__ == "__main__":
    main()
