# Binance Pay History — Net Stablecoin Balance

A command-line script that calculates the net balance of payments received and sent via **Binance Pay**, also including **deposits received through the BEP20 network (BSC)**. Only accounts for **USDC** and **USDT**, starting from **December 1, 2025**.

## What it does

- Queries the `/sapi/v1/pay/transactions` endpoint to fetch all C2C payments received and sent via Binance Pay.
- Queries `/sapi/v1/capital/deposit/hisrec` to include on-chain deposits received through the BEP20 network.
- Automatically filters:
  - Only **USDC** and **USDT** currencies.
  - Only movements from the **funding wallet**.
  - Excludes `CRYPTO_BOX` transactions (red envelopes / rewards).
  - Allows manually excluding transactions from specific Binance IDs (e.g. payments from friends or contacts unrelated to the business).
- Generates a report with:
  - Chronological breakdown of income and expenses.
  - Monthly balance (income, expenses, and net per month).
  - Full historical balance.

## Requirements

- Python 3.10+
- A Binance API Key with read permissions (no trading or withdrawal permissions required).

## Installation

1. Clone or download this repository.
2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   ```

   **Windows:**
   ```bat
   .venv\Scripts\activate.bat
   pip install -r requirements.txt
   ```

   **Linux / macOS:**
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root (see next section).

## Configuration (`.env`)

Create a `.env` file in the same directory as `main.py`:

```env
API_KEY=your_binance_api_key
API_SECRET=your_binance_api_secret
EXCLUDED_IDS=123456789,987654321
```

| Variable | Required | Description |
|---|---|---|
| `API_KEY` | Yes | API Key generated on Binance (read-only). |
| `API_SECRET` | Yes | Corresponding API Secret. |
| `EXCLUDED_IDS` | No | Comma-separated list of `binanceId` values to exclude from the calculation (e.g. payments from friends or personal contacts). |

> ⚠️ The `.env` file should never be committed to a repository. It is already included in `.gitignore`.

## Usage

### Windows

Double-click `run.bat`, or from a terminal:

```bat
.venv\Scripts\python.exe main.py
```

### Linux / macOS

```bash
./run.sh
```

or directly:

```bash
.venv/bin/python main.py
```

### Available options

| Flag | Description |
|---|---|
| `--pay-tipo {C2C,PAY,ALL}` | Filter Pay transactions by order type. Default: `ALL`. |
| `--debug` | Prints the raw JSON of the first Pay transactions (useful for inspecting fields like `binanceId`). |
| `--debug-limit N` | Number of transactions to show in `--debug` mode. Default: `5`. |

Examples:

```bash
# Full report
python main.py

# C2C transactions only
python main.py --pay-tipo C2C

# Inspect the raw JSON of the first 10 transactions
python main.py --debug --debug-limit 10
```

## How to find someone's `binanceId` to exclude them

1. Run the program with `--debug`.
2. Look in the printed JSON for the `payerInfo.binanceId` and `receiverInfo.binanceId` fields of the transaction you want to exclude.
3. Add that number to `EXCLUDED_IDS` in your `.env`, comma-separated if there are multiple.

## How monthly windowing works

Binance Pay's API returns a maximum of 100 results per call. To avoid silently missing transactions, this script splits the date range into **exact monthly windows** (from the 1st to the last day of each month) and queries each one separately. This is especially important for high-volume months — and the script will warn you if any window returns 100 results, since that may indicate the limit was hit.

## Technical notes

- `recvWindow=10000` is used to tolerate small clock differences between your machine and Binance's servers.
- BEP20 **withdrawals** are not counted; only Binance Pay outgoing payments are subtracted, and BEP20 incoming deposits are added.

## Project structure

```
binance-pay-history/
├── main.py          # Main script
├── requirements.txt # Python dependencies
├── .env             # Credentials (not versioned)
├── .gitignore
├── run.sh           # Linux/macOS launcher
└── README.md
```