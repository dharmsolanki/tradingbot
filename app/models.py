from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class Signal:
    signal: str
    option_type: Optional[str]
    score: int
    confidence: int
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not (0 <= self.confidence <= 100):
            raise ValueError("confidence must be between 0 and 100.")

        if self.score < 0:
            raise ValueError("score cannot be negative.")


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

    def __post_init__(self):
        if self.entry <= 0:
            raise ValueError("entry must be greater than zero.")

        if self.stop_loss <= 0:
            raise ValueError("stop_loss must be greater than zero.")

        if self.target <= 0:
            raise ValueError("target must be greater than zero.")

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero.")

        if self.risk_reward <= 0:
            raise ValueError("risk_reward must be greater than zero.")

        if not (0 <= self.confidence <= 100):
            raise ValueError("confidence must be between 0 and 100.")

        if self.score < 0:
            raise ValueError("score cannot be negative.")
