from app import strategy
from app.core.exceptions import RiskValidationError


def calculate_position_size(capital, risk_per_unit, lot_size):
    """
    Determine how many lots to trade based on capital and risk per trade.

    Never assumes lot size — caller must pass the live lot_size fetched
    from the option contract.

    Parameters
    ----------
    capital : float
        Current available virtual capital.
    risk_per_unit : float
        Rupee risk (premium - stop_loss) per single unit.
    lot_size : int
        Live lot size for the instrument, from Upstox contract data.

    Returns
    -------
    int
        Number of lots to trade (minimum 1, 0 if capital insufficient
        even for a single lot).
    """

    if capital <= 0:
        return 0

    if risk_per_unit <= 0 or lot_size <= 0:
        raise RiskValidationError("risk_per_unit and lot_size must be positive.")

    max_risk_rupees = capital * strategy.MAX_RISK_PER_TRADE / 100

    risk_per_lot = risk_per_unit * lot_size

    if risk_per_lot > max_risk_rupees:
        return 0

    return int(max_risk_rupees // risk_per_lot)


def check_daily_loss_limit(realized_pnl_today, capital):
    """
    Check whether the daily loss limit has been breached.

    Parameters
    ----------
    realized_pnl_today : float
        Sum of net_pnl for all trades closed today (negative = loss).
    capital : float
        Starting capital for the day.

    Returns
    -------
    dict
        {"breached": bool, "loss_percent": float}
    """

    if capital <= 0:
        raise RiskValidationError("capital must be positive.")

    loss_percent = (-realized_pnl_today / capital) * 100 if realized_pnl_today < 0 else 0.0

    return {
        "breached": loss_percent >= strategy.MAX_DAILY_LOSS_PERCENT,
        "loss_percent": round(loss_percent, 2),
    }


def check_trade_count_limit(trades_today_count):
    """
    Check whether the maximum number of trades for the day is reached.
    """

    return trades_today_count >= strategy.MAX_TRADES_PER_DAY


def update_trailing_stop(option_type, entry, current_stop_loss, current_premium, risk):
    """
    Move stop loss to breakeven once the trade has moved favourably by
    TRAILING_TRIGGER_RR × risk. Never moves stop loss backward.

    Parameters
    ----------
    option_type : str
        "CE" or "PE" (informational only; both are long-premium trades).
    entry : float
        Entry premium.
    current_stop_loss : float
        Current stop loss level.
    current_premium : float
        Latest live premium (LTP) of the open position.
    risk : float
        Original rupee risk per unit (entry - initial stop loss).

    Returns
    -------
    float
        Updated stop loss (unchanged if trigger not yet reached).
    """

    if risk <= 0:
        return current_stop_loss

    trigger_price = entry + (risk * strategy.TRAILING_TRIGGER_RR)

    if current_premium >= trigger_price:
        return max(current_stop_loss, entry)

    return current_stop_loss


def calculate_trade_levels(signal, option):
    """
    Create a complete trade plan using option premium.

    Parameters
    ----------
    signal : dict
        Output from generate_signal()

    option : dict
        Output from OptionService.get_option()

    Returns
    -------
    dict
    """

    if signal["signal"] != "BUY":
        return {
            "trade": False,
            "reason": "No trade signal.",
        }

    premium = option.get("ltp")

    if premium is None or premium <= 0:
        raise ValueError("Invalid option premium.")

    risk = premium * strategy.STOP_LOSS_PERCENT / 100

    reward = premium * strategy.TARGET_PERCENT / 100

    entry = premium

    if option["option_type"] == "CE":

        stop_loss = entry - risk
        target = entry + reward

    else:

        # Premium increases when PE moves in our favour.
        # Same calculation because we are buying the option.

        stop_loss = entry - risk
        target = entry + reward

    return {
        "trade": True,
        "symbol": f"{option['strike']} {option['option_type']}",
        "instrument_key": option["instrument_key"],
        "option_type": option["option_type"],
        "expiry": option["expiry"],
        "strike": option["strike"],
        "entry": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "target": round(target, 2),
        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "risk_reward": strategy.RISK_REWARD_RATIO,
        "quantity": strategy.DEFAULT_QUANTITY,
        "confidence": signal["confidence"],
        "score": signal["score"],
        "reason": signal["reasons"],
    }


def calculate_target_2(entry, risk):
    """
    Calculate a second, further target for published recommendations.

    Target 1 (from calculate_trade_levels) uses RISK_REWARD_RATIO.
    Target 2 uses the wider RISK_REWARD_RATIO_2, for a "book partial /
    let the rest run" style recommendation, matching how professional
    call sheets publish two targets.

    Parameters
    ----------
    entry : float
        Entry premium.
    risk : float
        Rupee risk per unit (entry - stop_loss), as returned by
        calculate_trade_levels().

    Returns
    -------
    float
        Target 2 price.
    """

    if risk <= 0:
        raise RiskValidationError("risk must be positive to calculate target_2.")

    reward_2 = risk * strategy.RISK_REWARD_RATIO_2

    return round(entry + reward_2, 2)


def calculate_entry_range(entry):
    """
    Return a published entry band around the actual entry premium,
    e.g. entry=146.5 -> (143.6, 149.4), reflecting realistic fill
    variance rather than a single exact price.

    Parameters
    ----------
    entry : float
        Entry premium.

    Returns
    -------
    tuple[float, float]
        (entry_low, entry_high)
    """

    if entry <= 0:
        raise RiskValidationError("entry must be positive to calculate entry range.")

    half_band = entry * (strategy.ENTRY_RANGE_PERCENT / 100) / 2

    return (round(entry - half_band, 2), round(entry + half_band, 2))
