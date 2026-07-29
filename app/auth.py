"""
auth.py

Handles reading and validating the Upstox access token stored locally.
"""

from __future__ import annotations

import json
import os
from typing import Optional


class UpstoxAuth:
    """
    Utility class for loading and validating the Upstox access token.
    """

    def __init__(self, token_file: str = "token.json") -> None:
        self.token_file = token_file

    def is_valid(self) -> bool:
        """
        Check whether the token file exists and contains a non-empty access token.

        Returns:
            bool: True if a valid token exists, otherwise False.
        """
        if not os.path.isfile(self.token_file):
            return False

        try:
            with open(self.token_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            token = data.get("access_token")

            return isinstance(token, str) and token.strip() != ""

        except (json.JSONDecodeError, OSError):
            return False

    def get_token(self) -> str:
        """
        Returns the access token.

        Raises:
            FileNotFoundError:
                If token.json does not exist.

            ValueError:
                If JSON is invalid or access_token is missing/empty.
        """
        if not os.path.isfile(self.token_file):
            raise FileNotFoundError(f"Token file not found: {self.token_file}")

        try:
            with open(self.token_file, "r", encoding="utf-8") as file:
                data = json.load(file)

        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON inside token file.") from exc

        except OSError as exc:
            raise ValueError(f"Unable to read token file: {self.token_file}") from exc

        token: Optional[str] = data.get("access_token")

        if not isinstance(token, str) or not token.strip():
            raise ValueError("access_token is missing or empty.")

        return token.strip()

    def save_token(self, token: str) -> None:
        """
        Save access token to token.json.
        """

        token = token.strip()

        if not token:
            raise ValueError("Access token cannot be empty.")

        data = {"access_token": token}

        with open(self.token_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def get_masked_token(self) -> str:
        """
        Returns masked access token.
        Example:
        ************abcd
        """

        token = self.get_token()

        if len(token) <= 4:
            return "*" * len(token)

        return "*" * (len(token) - 4) + token[-4:]
