from datetime import datetime

from app.market_data import MarketData


class OptionService:

    def __init__(self):
        self.market = MarketData()

    @staticmethod
    def get_available_expiries(contracts):
        """
        Return sorted unique expiry dates.
        """

        if not contracts:
            raise ValueError("Contracts list is empty.")

        expiries = sorted({contract["expiry"] for contract in contracts})

        return expiries

    @staticmethod
    def get_nearest_expiry(contracts):
        """
        Return nearest expiry from option contracts (today or later only —
        contract master data can include already-expired expiries).
        """

        expiries = OptionService.get_available_expiries(contracts)

        today = datetime.now().strftime("%Y-%m-%d")

        future_expiries = [e for e in expiries if e >= today]

        if not future_expiries:
            raise ValueError("No active (non-expired) expiry found in contracts.")

        return future_expiries[0]

    def get_option_chain(
        self,
        token,
        instrument_key,
    ):
        contracts = self.market.get_option_contracts(
            token=token,
            instrument_key=instrument_key,
        )

        expiry = self.get_nearest_expiry(contracts)

        lot_size_map = {
            c["instrument_key"]: c["lot_size"]
            for c in contracts
            if c.get("instrument_key") and c.get("lot_size")
        }

        chain = self.market.get_option_chain(
            token=token,
            instrument_key=instrument_key,
            expiry_date=expiry,
        )

        return chain, lot_size_map

    @staticmethod
    def get_atm_option(chain):
        """
        Return the ATM option from the option chain.
        """

        if not chain:
            raise ValueError("Option chain is empty.")

        spot = chain[0]["underlying_spot_price"]

        atm = min(
            chain,
            key=lambda option: abs(option["strike_price"] - spot),
        )

        return {
            "spot": spot,
            "expiry": atm["expiry"],
            "strike": atm["strike_price"],
            "call": {
                "instrument_key": atm["call_options"]["instrument_key"],
                "market_data": atm["call_options"]["market_data"],
                "option_greeks": atm["call_options"]["option_greeks"],
            },
            "put": {
                "instrument_key": atm["put_options"]["instrument_key"],
                "market_data": atm["put_options"]["market_data"],
                "option_greeks": atm["put_options"]["option_greeks"],
            },
        }

    @staticmethod
    def get_option(
        chain,
        option_type="CE",
        moneyness="ATM",
        steps=1,
        lot_size_map=None,
    ):
        """
        Returns ATM / ITM / OTM option.

        Parameters
        ----------
        chain : list
            Option chain returned by Upstox API.

        option_type : str
            "CE" or "PE"

        moneyness : str
            "ATM", "ITM" or "OTM"

        steps : int
            Number of strikes away from ATM.

        Returns
        -------
        dict
            Selected option details.
        """

        # ---------- Input Validation ----------

        if option_type not in ("CE", "PE"):
            raise ValueError("option_type must be 'CE' or 'PE'.")

        if moneyness not in ("ATM", "ITM", "OTM"):
            raise ValueError("moneyness must be 'ATM', 'ITM' or 'OTM'.")

        if not isinstance(steps, int) or steps < 1:
            raise ValueError("steps must be an integer >= 1.")

        if not chain:
            raise ValueError("Option chain is empty.")

        # ---------- Spot Price ----------

        spot = chain[0].get("underlying_spot_price")

        if spot is None:
            raise ValueError("Underlying spot price not found.")

        # ---------- Sort Chain ----------

        sorted_chain = sorted(
            chain,
            key=lambda option: option["strike_price"],
        )

        # ---------- Find ATM Strike ----------

        atm_index = min(
            range(len(sorted_chain)),
            key=lambda i: abs(sorted_chain[i]["strike_price"] - spot),
        )

        index = atm_index

        # ---------- ITM / OTM Selection ----------

        if moneyness != "ATM":

            if option_type == "CE":

                if moneyness == "ITM":
                    index -= steps

                elif moneyness == "OTM":
                    index += steps

            else:  # PE

                if moneyness == "ITM":
                    index += steps

                elif moneyness == "OTM":
                    index -= steps

        # ---------- Boundary Check ----------

        if index < 0 or index >= len(sorted_chain):
            raise ValueError("Requested strike is outside available option chain.")

        option = sorted_chain[index]

        side = option["call_options"] if option_type == "CE" else option["put_options"]

        market = side.get("market_data", {})
        greeks = side.get("option_greeks", {})

        # ---------- Basic Validation ----------

        instrument_key = side.get("instrument_key")

        if not instrument_key:
            raise ValueError("Instrument key missing for selected option.")

        # ---------- Return ----------

        lot_size = None

        if lot_size_map and instrument_key:
            lot_size = lot_size_map.get(instrument_key)

        if not lot_size:
            raise ValueError(
                f"lot_size not found for instrument_key={instrument_key}. "
                "Verify option contracts API returned lot_size."
            )

        return {
            "spot": spot,
            "expiry": option.get("expiry"),
            "strike": option.get("strike_price"),
            "option_type": option_type,
            "moneyness": moneyness,
            "instrument_key": instrument_key,
            "lot_size": lot_size,
            # Market Data
            "ltp": market.get("ltp"),
            "bid": market.get("bid_price"),
            "ask": market.get("ask_price"),
            "volume": market.get("volume"),
            "oi": market.get("oi"),
            # Greeks
            "delta": greeks.get("delta"),
            "gamma": greeks.get("gamma"),
            "theta": greeks.get("theta"),
            "vega": greeks.get("vega"),
            "iv": greeks.get("iv"),
        }

    @staticmethod
    def check_liquidity(
        option,
        min_oi=500,
        min_volume=0,
        max_spread_percent=5.0,
    ):
        """
        Validate that a selected option is liquid enough to trade safely.

        Uses only fields already present on the option dict returned by
        get_option() — all live from the Upstox option chain, nothing
        hardcoded or assumed.

        Parameters
        ----------
        option : dict
            Output of get_option().
        min_oi : int
            Minimum acceptable open interest.
        min_volume : int
            Minimum acceptable traded volume.
        max_spread_percent : float
            Maximum acceptable bid-ask spread as % of LTP.

        Returns
        -------
        dict
            {"liquid": bool, "reasons": list[str]}
        """

        reasons = []

        ltp = option.get("ltp")
        bid = option.get("bid")
        ask = option.get("ask")
        oi = option.get("oi")
        volume = option.get("volume")

        if ltp is None or ltp <= 0:
            reasons.append("LTP unavailable or invalid.")
            return {"liquid": False, "reasons": reasons}

        if oi is None or oi < min_oi:
            reasons.append(f"OI too low ({oi}) < {min_oi}.")

        if volume is not None and volume < min_volume:
            reasons.append(f"Volume too low ({volume}) < {min_volume}.")

        if bid is not None and ask is not None and bid > 0 and ask > 0:
            spread_percent = ((ask - bid) / ltp) * 100

            if spread_percent > max_spread_percent:
                reasons.append(
                    f"Spread too wide ({spread_percent:.2f}%) "
                    f"> {max_spread_percent}%."
                )
        else:
            reasons.append("Bid/Ask unavailable to evaluate spread.")

        return {"liquid": len(reasons) == 0, "reasons": reasons}
