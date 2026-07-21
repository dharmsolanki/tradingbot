"""
market_data.py

Handles all market data requests from the Upstox API.
"""

from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime, timedelta


import requests

from app.core.exceptions import AuthenticationError, MarketDataError


class MarketData:
    """Client for fetching market data from the Upstox API."""

    BASE_URL = "https://api.upstox.com"

    def __init__(self, timeout: int = 10) -> None:
        """
        Initialize the MarketData client.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update({"Accept": "application/json"})

    def _get(
        self,
        endpoint: str,
        token: str,
        params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Send a GET request to the Upstox API.

        Args:
            endpoint: API endpoint (e.g. /v3/market-quote/ltp)
            token: Upstox access token
            params: Query parameters

        Returns:
            Parsed JSON response.

        Raises:
            ValueError: If the API request fails.
        """

        url = f"{self.BASE_URL}{endpoint}"

        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = self.session.get(
                url=url,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise MarketDataError(f"GET {url} | Request timed out.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise MarketDataError(f"GET {url} | Connection failed.") from exc
        except requests.exceptions.RequestException as exc:
            raise MarketDataError(f"GET {url} | Request failed: {exc}") from exc

        if response.status_code == 401:
            raise AuthenticationError(
                f"GET {response.url} | Invalid or expired token."
            )

        if response.status_code != 200:
            raise MarketDataError(
                f"GET {response.url} | "
                f"Status: {response.status_code} | "
                f"Response: {response.text}"
            )

        return response.json()

    def get_ltp(
        self,
        token: str,
        instrument_key: str,
    ) -> float:
        """
        Get the latest traded price (LTP) for an instrument.
        """

        data = self._get(
            endpoint="/v3/market-quote/ltp",
            token=token,
            params={"instrument_key": instrument_key},
        )

        market_data = data.get("data", {})

        if not market_data:
            raise ValueError("No market data returned.")

        # API returns only one item for one instrument
        first_item = next(iter(market_data.values()))

        return float(first_item["last_price"])

    def get_intraday_candles(
        self,
        token: str,
        instrument_key: str,
        unit: str = "minutes",
        interval: int = 5,
    ) -> List[List[Any]]:
        """
        Get intraday candle data.
        """

        data = self._get(
            endpoint=(
                f"/v3/historical-candle/intraday/" f"{instrument_key}/{unit}/{interval}"
            ),
            token=token,
        )

        return data.get("data", {}).get("candles", [])

    def get_option_chain(
        self,
        token: str,
        instrument_key: str,
        expiry_date: str,
    ) -> List[Dict[str, Any]]:
        """
        Get option chain for an instrument.

        Args:
            token: Upstox access token.
            instrument_key: Underlying instrument key.
            expiry_date: Expiry date in YYYY-MM-DD format.

        Returns:
            List of option chain entries.
        """

        data = self._get(
            endpoint="/v2/option/chain",
            token=token,
            params={
                "instrument_key": instrument_key,
                "expiry_date": expiry_date,
            },
        )

        chain = data.get("data", [])

        if not chain:
            raise ValueError("No option chain returned.")

        return chain

    def get_option_contracts(
        self,
        token: str,
        instrument_key: str,
    ) -> List[Dict[str, Any]]:
        """
        Get option contracts for an underlying instrument.
        """

        data = self._get(
            endpoint="/v2/option/contract",
            token=token,
            params={
                "instrument_key": instrument_key,
            },
        )

        contracts = data.get("data", [])

        if not contracts:
            raise ValueError("No option contracts returned.")

        return contracts

    def get_historical_candles(
        self,
        token,
        instrument_key,
        unit="minutes",
        interval=5,
        days=5,
    ):
        """
        Get historical candles.

        Returns:
            list
        """

        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        endpoint = (
            f"/v3/historical-candle/"
            f"{instrument_key}/"
            f"{unit}/"
            f"{interval}/"
            f"{to_date}/"
            f"{from_date}"
        )

        data = self._get(
            endpoint=endpoint,
            token=token,
        )

        return data.get("data", {}).get("candles", [])

    def get_latest_candles(
        self,
        token,
        instrument_key,
        unit="minutes",
        interval=5,
    ):
        """
        Returns latest candles.

        Weekday:
            Intraday

        Weekend/Holiday:
            Historical
        """

        candles = self.get_intraday_candles(
            token,
            instrument_key,
            unit,
            interval,
        )

        if candles:
            return candles

        return self.get_historical_candles(
            token,
            instrument_key,
            unit,
            interval,
        )

    def get_continuous_candles(
        self,
        token: str,
        instrument_key: str,
        unit: str = "minutes",
        interval: int = 5,
        lookback_days: int = 5,
    ) -> List[List[Any]]:
        """
        Return a chronologically continuous candle series: recent
        historical candles (for indicator lookback) + today's intraday
        candles, deduplicated by timestamp and sorted ascending.

        Without this, indicators needing a long period (e.g. EMA_SLOW=50)
        cannot be calculated for the first few hours after market open,
        since intraday-only data starts empty at 09:15 and only builds
        up minute by minute.
        """

        historical = self.get_historical_candles(
            token=token,
            instrument_key=instrument_key,
            unit=unit,
            interval=interval,
            days=lookback_days,
        )

        intraday = self.get_intraday_candles(
            token=token,
            instrument_key=instrument_key,
            unit=unit,
            interval=interval,
        )

        by_timestamp = {}

        for candle in historical:
            by_timestamp[candle[0]] = candle

        for candle in intraday:
            by_timestamp[candle[0]] = candle

        return [by_timestamp[ts] for ts in sorted(by_timestamp.keys())]

    def get_multi_timeframe_candles(
        self,
        token: str,
        instrument_key: str,
    ) -> dict:
        """
        Fetch both 5-minute and 15-minute candles.

        Returns
        -------
        {
            "5m": [...],
            "15m": [...]
        }
        """

        return {
            "5m": self.get_continuous_candles(
                token=token,
                instrument_key=instrument_key,
                unit="minutes",
                interval=5,
            ),
            "15m": self.get_continuous_candles(
                token=token,
                instrument_key=instrument_key,
                unit="minutes",
                interval=15,
            ),
        }
