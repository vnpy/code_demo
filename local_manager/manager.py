from typing import Dict, Set

from vnpy.trader.gateway import BaseGateway
from vnpy.trader.constant import Direction, Offset
from vnpy.trader.object import (
    PositionData, TradeData, OrderData, ContractData
)


class LocalManager:

    def __init__(self, gateway: BaseGateway):
        """"""
        self.gateway = gateway

        self.contracts: Dict[str, ContractData] = {}
        self.positions: Dict[str, PositionData] = {}
        self.vt_orderids: Set[str] = set()

        # Patch gateway callbacks
        self._on_position = gateway.on_position
        self._on_contract = gateway.on_contract
        self._on_trade = gateway.on_trade
        self._on_order = gateway.on_order

        gateway.on_position = self.on_position
        gateway.on_contract = self.on_contract
        gateway.on_trade = self.on_trade
        gateway.on_order = self.on_order

    def on_position(self, position: PositionData):
        """"""
        self.positions[position.vt_positionid] = position

        self._on_position(position)

    def on_trade(self, trade: TradeData):
        """"""
        self._on_trade(trade)

        if trade.direction == Direction.LONG:
            if trade.offset == Offset.OPEN:
                position = self.get_position(trade.vt_symbol, Direction.LONG)
            else:
                position = self.get_position(trade.vt_symbol, Direction.SHORT)
        else:
            if trade.offset == Offset.OPEN:
                position = self.get_position(trade.vt_symbol, Direction.SHORT)
            else:
                position = self.get_position(trade.vt_symbol, Direction.LONG)

        if trade.offset == Offset.OPEN:
            old_cost = position.price * position.volume
            new_cost = old_cost + trade.price * trade.volume

            position.volume += trade.volume

            position.price = new_cost / position.volume
        else:
            position.volume -= trade.volume
            if not position.volume:
                position.price = 0
                position.pnl = 0

            if trade.vt_orderid in self.vt_orderids:
                position.frozen -= trade.volume

        self._on_position(position)

    def on_order(self, order: OrderData):
        """"""
        self._on_order(order)

        if order.offset == Offset.CLOSE:
            if order.direction == Direction.LONG:
                position = self.get_position(order.vt_symbol, Direction.SHORT)
            else:
                position = self.get_position(order.vt_symbol, Direction.LONG)

            volume_change = order.volume - order.traded

            # Freeze new order volume
            if (order.vt_orderid not in self.vt_orderids and order.is_active()):
                self.vt_orderids.add(order.vt_orderid)
                position.frozen += volume_change
            # Unfreeze cancelled volume
            elif (order.vt_orderid in self.vt_orderids and not order.is_active()):
                position.frozen -= volume_change

            self._on_position(position)

    def on_contract(self, contract: ContractData):
        """"""
        self.contracts[contract.vt_symbol] = contract
        self._on_contract(contract)

    def get_position(self, vt_symbol: str, direction: Direction) -> PositionData:
        """"""
        vt_positionid = f"{vt_symbol}.{direction.value}"
        position = self.positions.get(vt_positionid, None)

        if not position:
            contract = self.contracts[vt_symbol]

            position = PositionData(
                symbol=contract.symbol,
                exchange=contract.exchange,
                direction=direction,
                gateway_name=contract.gateway_name
            )

        return position
