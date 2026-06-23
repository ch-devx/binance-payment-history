"""
api.py
======
Binance API layer: HMAC signing, signed GET requests, monthly window
pagination, and the two data-fetching functions (Pay + BEP20 deposits).

Imports from filters.py:
  - START_DT         → lower bound for iter_windows()
  - is_valid_pay_tx  → row-level filter applied after each Pay page
  - is_valid_deposit → row-level filter applied after each deposit page
"""

import calendar
import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from filters import START_DT, is_valid_deposit, is_valid_pay_tx, is_valid_withdrawal

# ── Credentials ───────────────────────────────────────────────────────────────

load_dotenv()

API_KEY: str = os.getenv("API_KEY", "")
API_SECRET: str = os.getenv("API_SECRET", "")

if not API_KEY or not API_SECRET:
    raise SystemExit(
        "Error: API_KEY and/or API_SECRET not found in the .env file."
    )

BASE_URL = "https://api.binance.com"

# ── Signing & HTTP ────────────────────────────────────────────────────────────


def sign(params: dict) -> str:
    """Returns the HMAC-SHA256 signature for the given query parameters."""
    query = urlencode(params)
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()


def api_get(endpoint: str, params: dict) -> dict | list:
    """
    Injects timestamp + recvWindow, signs the request, and performs a
    GET against BASE_URL + endpoint. Raises RuntimeError on HTTP errors.
    """
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 10000
    params["signature"] = sign(params)
    headers = {"X-MBX-APIKEY": API_KEY}
    r = requests.get(BASE_URL + endpoint, params=params, headers=headers, timeout=10)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code} on {endpoint}: {r.text}")
    return r.json()


# ── Pagination ────────────────────────────────────────────────────────────────


def iter_windows():
    """
    Yields exact monthly windows from START_DT to now (UTC).
    Each window spans from the 1st to the last second of the month.

    Yields:
        (start_ms: int, end_ms: int, window_start: datetime, window_end: datetime)
    """
    end_dt = datetime.now(timezone.utc)
    cursor = START_DT
    while cursor < end_dt:
        year, month = cursor.year, cursor.month
        last_day = calendar.monthrange(year, month)[1]
        win_end = min(
            datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc),
            end_dt,
        )
        yield (
            int(cursor.timestamp() * 1000),
            int(win_end.timestamp() * 1000),
            cursor,
            win_end,
        )
        # Advance to the 1st of the next month
        if month == 12:
            cursor = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            cursor = datetime(year, month + 1, 1, tzinfo=timezone.utc)


# ── Fetchers ──────────────────────────────────────────────────────────────────


def fetch_all_pay() -> list[dict]:
    """
    Returns all stablecoin Pay transactions from the funding wallet across
    all monthly windows since START_DT.

    Positive amount  → received
    Negative amount  → sent
    """
    all_transactions: list[dict] = []
    for start_ms, end_ms, cursor, win_end in iter_windows():
        print(
            f"  [Pay]    {cursor.strftime('%Y-%m-%d')} -> {win_end.strftime('%Y-%m-%d')} ...",
            end=" ",
            flush=True,
        )
        body = api_get(
            "/sapi/v1/pay/transactions",
            {"startTime": start_ms, "endTime": end_ms, "limit": 100},
        )
        if isinstance(body, dict) and body.get("code") != "000000":
            raise RuntimeError(f"Pay API error: {body}")
        txs = body.get("data", []) if isinstance(body, dict) else []
        filtered = [tx for tx in txs if is_valid_pay_tx(tx)]
        print(f"{len(txs)} total, {len(filtered)} stablecoins")
        if len(txs) >= 100:
            print(
                f"  ⚠️  Warning: window {cursor.strftime('%Y-%m')} returned "
                f"{len(txs)} results — the page limit may have been reached."
            )
        all_transactions.extend(filtered)
    return all_transactions


def fetch_all_deposits() -> list[dict]:
    """
    Returns all completed BEP20 stablecoin deposits (status=1) across
    all monthly windows since START_DT.
    """
    all_deposits: list[dict] = []
    for start_ms, end_ms, cursor, win_end in iter_windows():
        print(
            f"  [BEP20 deposit] {cursor.strftime('%Y-%m-%d')} -> {win_end.strftime('%Y-%m-%d')} ...",
            end=" ",
            flush=True,
        )
        deposits = api_get(
            "/sapi/v1/capital/deposit/hisrec",
            {
                "network": "BSC",
                "status": 1,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            },
        )
        filtered = [d for d in deposits if is_valid_deposit(d)]
        print(f"{len(deposits)} total, {len(filtered)} stablecoins")
        all_deposits.extend(filtered)
    return all_deposits

def fetch_all_withdrawals() -> list[dict]:
    """
    Returns all completed BEP20 stablecoin withdrawals (status=6) across
    all monthly windows since START_DT.
    """
    all_withdrawals: list[dict] = []
    for start_ms, end_ms, cursor, win_end in iter_windows():
        print(
            f"  [BEP20 withdraw] {cursor.strftime('%Y-%m-%d')} -> {win_end.strftime('%Y-%m-%d')} ...",
            end=" ",
            flush=True,
        )
        withdrawals = api_get(
            "/sapi/v1/capital/withdraw/history",
            {
                "network": "BSC",
                "status": 6,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            },
        )
        filtered = [w for w in withdrawals if is_valid_withdrawal(w)]
        print(f"{len(withdrawals)} total, {len(filtered)} stablecoins")
        all_withdrawals.extend(filtered)
    return all_withdrawals