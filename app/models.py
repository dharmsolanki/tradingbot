from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class Signal:
    signal: str
    option_type: Optional[str]
    score: int
    confidence: int
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SelectedOption:
    symbol: str
    instrument_key: str
    option_type: str
    strike: float
    expiry: str

    ltp: float
    bid: Optional[float]
    ask: Optional[float]

    volume: Optional[int]
    oi: Optional[int]

    delta: Optional[float]
    gamma: Optional[float]
    theta: Optional[float]
    vega: Optional[float]
    iv: Optional[float]


@dataclass(slots=True)
class TradePlan:
    trade: bool

    symbol: str
    instrument_key: str

    option_type: str

    strike: float
    expiry: str

    entry: float
    stop_loss: float
    target: float

    risk: float
    reward: float
    risk_reward: float

    quantity: int

    confidence: int
    score: int

    reason: list[str] = field(default_factory=list)
