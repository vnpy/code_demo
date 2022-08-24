import json

from vnpy.event import EventEngine, Event
from vnpy.trader.event import (
    EVENT_LOG, EVENT_TICK,
    EVENT_ORDER, EVENT_TRADE
)
from vnpy.trader.constant import (
    Direction, OrderType, Offset
)
from vnpy.trader.object import (
    TickData, LogData, SubscribeRequest,
    ContractData, OrderRequest,
    OrderData, TradeData
)
from vnpy.trader.engine import MainEngine, BaseEngine

from .base import EVENT_STRATEGY
from .template import StrategyTemplate
from .strategy import SimpleStrategy


class StrategyEngine(BaseEngine):
    """策略引擎"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__(main_engine, event_engine, "SimpleStrategy")

        self.strategies: dict[str, StrategyTemplate] = {}
        self.subscribed: set[str] = set()

        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_ORDER, self.process_order_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)

        self.load_setting()

    def load_setting(self) -> None:
        """加载交易代码配置"""
        with open("c:\\Github\\code_demo\\setting.json") as f:
            vt_symbols = json.load(f)
            for s in vt_symbols:
                strategy = SimpleStrategy(self, s)
                self.strategies[s] = strategy

    def process_tick_event(self, event: Event) -> None:
        """行情事件"""
        tick: TickData = event.data

        strategy = self.strategies.get(tick.vt_symbol, None)

        if strategy:
            strategy.on_tick(tick)

    def process_order_event(self, event: Event) -> None:
        """委托事件"""
        order: OrderData = event.data

        strategy = self.strategies.get(order.vt_symbol, None)

        if strategy:
            strategy.on_order(order)

    def process_trade_event(self, event: Event) -> None:
        """成交事件"""
        trade: TradeData = event.data

        strategy = self.strategies.get(trade.vt_symbol, None)

        if strategy:
            strategy.on_trade(trade)

    def process_contract_event(self, event: Event) -> None:
        """合约事件"""
        contract: ContractData = event.data

        # 订阅策略合约行情
        if contract.vt_symbol in self.strategies:
            req = SubscribeRequest(contract.symbol, contract.exchange)
            self.main_engine.subscribe(req, contract.gateway_name)

    def send_order(
        self,
        vt_symbol: str,
        price: float,
        volume: int,
        direction: Direction,
        offset: Offset
    ) -> None:
        """发送委托"""
        contract = self.main_engine.get_contract(vt_symbol)

        req = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            type=OrderType.LIMIT,
            price=price,
            volume=volume,
            offset=offset
        )
        self.main_engine.send_order(req, contract.gateway_name)

    def write_log(self, msg: str) -> None:
        """输出日志"""
        log = LogData(msg=msg, gateway_name="STRATEGY")
        event = Event(EVENT_LOG, log)
        self.event_engine.put(event)

    def put_event(self, data: dict) -> None:
        """推送事件"""
        event = Event(EVENT_STRATEGY, data)
        self.event_engine.put(event)
