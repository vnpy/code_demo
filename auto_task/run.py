import sys
import multiprocessing
from datetime import time, datetime
from time import sleep

from vnpy.rpc import RpcClient, RpcServer
from vnpy.event import EventEngine
from vnpy.trader.utility import load_json
from vnpy.trader.engine import MainEngine

from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp, CtaEngine
from vnpy_ctastrategy.base import EVENT_CTA_LOG

from ding import send_ding_msg


# 通讯消息主题
TOPIC_INIT = "init"
TOPIC_START = "start"
TOPIC_STOP = "stop"
TOPIC_CLOSE = "close"

# 策略运行时间
DAY_START = time(8, 45)
DAY_END = time(15, 0)

NIGHT_START = time(20, 45)
NIGHT_END = time(2, 45)

# RPC通讯地址
req_address = "tcp://localhost:9988"
sub_address = "tcp://localhost:8899"
rep_address = "tcp://*:9988"
pub_address = "tcp://*:8899"


class MyServer(RpcServer):
    """RPC服务器"""

    def __init__(self) -> None:
        """"""
        super().__init__()

        self.inited = False
        self.trading = False

        self.register(self.write_log)
        self.register(self.send_msg)
        self.register(self.init_done)
        self.register(self.start_done)
        self.register(self.stop_done)

    def write_log(self, msg: str) -> None:
        """输出子进程日志"""
        print(f"[交易子进程] {msg}")
        send_ding_msg(f"[交易子进程] {msg}")        

    def parent_log(self, msg: str) -> None:
        """输出父进程日志"""
        print(f"[监控父进程] {msg}")
        send_ding_msg(f"[监控父进程] {msg}")

    def send_msg(self, msg: str) -> bool:
        """发送异常信息通知"""
        send_ding_msg(f"[异常信息] {msg}")

    def init_done(self) -> None:
        """初始化完成"""
        self.inited = True
        self.write_log("策略全部初始化完成")

    def start_done(self) -> None:
        """启动完成"""
        self.trading = True
        self.write_log("策略全部启动")

    def stop_done(self) -> None:
        """停止完成"""
        self.trading = False
        self.write_log("策略全部停止")

    def clear_status(self) -> None:
        """清空状态"""
        self.inited = False
        self.trading = False


class MyClient(RpcClient):

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.cta_engine: CtaEngine = None

        self.active = True

    def register_engine(self, cta_engine: CtaEngine) -> None:
        """在后续传入CTA引擎"""
        self.cta_engine = cta_engine

    def callback(self, topic: str, data: object):
        """回调函数"""
        # 初始化指令
        if topic == TOPIC_INIT:
            # 调用同步函数来执行策略初始化
            for strategy_name in self.cta_engine.strategies.keys():
                self.cta_engine._init_strategy(strategy_name)

            # 通知服务器初始化完成
            self.init_done()
        # 启动指令
        elif topic == TOPIC_START:
            self.cta_engine.start_all_strategies()

            self.start_done()
        # 停止指令
        elif topic == TOPIC_STOP:
            self.cta_engine.stop_all_strategies()

            self.stop_done()
        # 关闭指令
        elif topic == TOPIC_CLOSE:
            self.active = False


def check_trading_period() -> bool:
    """检查当前是否为交易时段"""
    return True
    current_time = datetime.now().time()

    trading = False
    if (
        (current_time >= DAY_START and current_time <= DAY_END)
        or (current_time >= NIGHT_START)
        or (current_time <= NIGHT_END)
    ):
        trading = True

    return trading


def run_child():
    """子进程运行"""
    # 创建客户端
    my_client = MyClient()
    my_client.subscribe_topic("")
    my_client.start(req_address, sub_address)

    # 创建核心引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(CtpGateway)

    cta_engine = main_engine.add_app(CtaStrategyApp)
    my_client.register_engine(cta_engine)

    my_client.write_log("核心引擎创建成功")

    # 注册CTA日志
    log_engine = main_engine.get_engine("log")
    event_engine.register(EVENT_CTA_LOG, log_engine.process_log_event)
    my_client.write_log("注册日志事件监听")

    # 连接CTP交易接口
    ctp_setting = load_json("connect_ctp.json")
    main_engine.connect(ctp_setting, "CTP")
    my_client.write_log("连接CTP接口")

    # 初始化CTA引擎
    cta_engine.init_engine()
    my_client.write_log("CTA引擎初始化完成")

    # 主线程进入循环
    while my_client.active:
        sleep(10)

    main_engine.close()
    sys.exit(0)


def run_parent():
    """父进程运行"""
    child_process = None

    my_server = MyServer()
    my_server.start(rep_address, pub_address)

    my_server.parent_log("启动CTA策略守护父进程")

    while True:
        trading = check_trading_period()

        # 交易时间
        if trading:
            # 启动子进程
            if child_process is None:
                my_server.parent_log("启动交易子进程")
                child_process = multiprocessing.Process(target=run_child)
                child_process.start()
                my_server.parent_log("子进程启动成功")
            # 启动交易策略
            elif child_process.is_alive():
                if not my_server.inited:
                    my_server.publish(TOPIC_INIT, None)
                elif not my_server.trading:
                    my_server.publish(TOPIC_START, None)
            # 异常信息报警
            else:
                code = child_process.exitcode
                my_server.send_msg(f"子进程异常终止运行，退出码{code}")

        # 非交易时间则退出子进程
        if not trading and child_process:
            if my_server.trading:
                my_server.publish(TOPIC_STOP, None)
            elif child_process.is_alive():
                my_server.publish(TOPIC_CLOSE, None)
            else:
                child_process = None
                my_server.clear_status()
                my_server.parent_log("子进程关闭成功")

        sleep(5)


if __name__ == "__main__":
    run_parent()
