from vnpy.event import EventEngine

from vnpy_ctp import CtpGateway as OriginalGateway
from vnpy_ctp.gateway.ctp_gateway import CtpTdApi, CtpMdApi, BaseGateway

from .event import EVENT_CONTRACT_INITED


class CxyTdApi(CtpTdApi):

    def onRspQryInstrument(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        super().onRspQryInstrument(data, error, reqid, last)

        if last:
            self.gateway.on_event(EVENT_CONTRACT_INITED)        


class CxyGateway(OriginalGateway):

    default_name: str = "CXY"

    def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
        BaseGateway.__init__(self, event_engine, gateway_name)

        self.td_api: "CxyTdApi" = CxyTdApi(self)
        self.md_api: "CtpMdApi" = CtpMdApi(self)
