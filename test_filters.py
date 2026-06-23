"""
test_filters.py
===============
Unit tests for filters.py predicates: is_excluded, is_valid_pay_tx,
is_valid_deposit.

Run with:
    python -m pytest test_filters.py -v
"""

import os
import pytest

# ── Ensure EXCLUDED_IDS is set before importing filters ──────────────────────
os.environ.setdefault("EXCLUDED_IDS", "111111111,222222222")

from filters import is_excluded, is_valid_deposit, is_valid_pay_tx


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _pay_tx(
    wallet_type: int = 1,
    currency: str = "USDT",
    payer_id: str = "999999999",
    receiver_id: str = "888888888",
) -> dict:
    """Returns a minimal Pay transaction dict."""
    return {
        "walletType": wallet_type,
        "currency": currency,
        "payerInfo": {"binanceId": payer_id},
        "receiverInfo": {"binanceId": receiver_id},
    }


def _deposit(coin: str = "USDT") -> dict:
    """Returns a minimal deposit dict."""
    return {"coin": coin}


# ── is_valid_pay_tx ───────────────────────────────────────────────────────────


class TestIsValidPayTx:

    def test_usdt_funding_wallet_is_valid(self):
        assert is_valid_pay_tx(_pay_tx(wallet_type=1, currency="USDT")) is True

    def test_usdc_funding_wallet_is_valid(self):
        assert is_valid_pay_tx(_pay_tx(wallet_type=1, currency="USDC")) is True

    def test_wrong_wallet_type_is_invalid(self):
        # walletType != 1 should be rejected regardless of currency
        assert is_valid_pay_tx(_pay_tx(wallet_type=2, currency="USDT")) is False

    def test_non_stablecoin_is_invalid(self):
        assert is_valid_pay_tx(_pay_tx(wallet_type=1, currency="BNB")) is False

    def test_btc_is_invalid(self):
        assert is_valid_pay_tx(_pay_tx(wallet_type=1, currency="BTC")) is False

    def test_empty_currency_is_invalid(self):
        assert is_valid_pay_tx(_pay_tx(wallet_type=1, currency="")) is False

    def test_wrong_wallet_and_wrong_currency_is_invalid(self):
        assert is_valid_pay_tx(_pay_tx(wallet_type=0, currency="ETH")) is False


# ── is_valid_deposit ──────────────────────────────────────────────────────────


class TestIsValidDeposit:

    def test_usdt_deposit_is_valid(self):
        assert is_valid_deposit(_deposit("USDT")) is True

    def test_usdc_deposit_is_valid(self):
        assert is_valid_deposit(_deposit("USDC")) is True

    def test_bnb_deposit_is_invalid(self):
        assert is_valid_deposit(_deposit("BNB")) is False

    def test_empty_coin_is_invalid(self):
        assert is_valid_deposit({"coin": ""}) is False

    def test_missing_coin_key_is_invalid(self):
        # .get("coin") returns None when key is absent → not in STABLECOINS
        assert is_valid_deposit({}) is False


# ── is_excluded ───────────────────────────────────────────────────────────────


class TestIsExcluded:

    # These IDs are set via os.environ at the top of this file
    EXCLUDED_PAYER = "111111111"
    EXCLUDED_RECEIVER = "222222222"
    SAFE_ID = "333333333"

    def test_excluded_payer_is_rejected(self):
        tx = _pay_tx(payer_id=self.EXCLUDED_PAYER, receiver_id=self.SAFE_ID)
        assert is_excluded(tx) is True

    def test_excluded_receiver_is_rejected(self):
        tx = _pay_tx(payer_id=self.SAFE_ID, receiver_id=self.EXCLUDED_RECEIVER)
        assert is_excluded(tx) is True

    def test_both_excluded_is_rejected(self):
        tx = _pay_tx(payer_id=self.EXCLUDED_PAYER, receiver_id=self.EXCLUDED_RECEIVER)
        assert is_excluded(tx) is True

    def test_both_safe_is_not_rejected(self):
        tx = _pay_tx(payer_id=self.SAFE_ID, receiver_id=self.SAFE_ID)
        assert is_excluded(tx) is False

    def test_empty_excluded_ids_never_rejects(self, monkeypatch):
        # Simulate an environment with no EXCLUDED_IDS configured
        monkeypatch.setattr("filters.EXCLUDED_IDS", set())
        tx = _pay_tx(payer_id=self.EXCLUDED_PAYER, receiver_id=self.EXCLUDED_RECEIVER)
        assert is_excluded(tx) is False

    def test_missing_payer_info_does_not_crash(self):
        tx = {"receiverInfo": {"binanceId": self.SAFE_ID}}
        assert is_excluded(tx) is False

    def test_missing_receiver_info_does_not_crash(self):
        tx = {"payerInfo": {"binanceId": self.SAFE_ID}}
        assert is_excluded(tx) is False

    def test_completely_empty_tx_does_not_crash(self):
        assert is_excluded({}) is False