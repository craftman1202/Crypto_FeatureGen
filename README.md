# Crypto Feature Generator

Desktop GUI tool (Python + tkinter) for downloading cryptocurrency market data from GMO Coin Public API, generating feature columns, and exporting a single CSV for model training or strategy research.

## Overview

This application:

- fetches OHLCV candle data for multiple JPY crypto pairs
- supports multiple time intervals (`1min` to `1month`)
- generates derived features (performance, lag features, action flags)
- exports all symbols merged on one time index
- can be built into a standalone Windows executable

## Supported Symbols

- `BTC_JPY`
- `ETH_JPY`
- `XRP_JPY`
- `LTC_JPY`
- `BCH_JPY`

## Supported Intervals

- `1min`
- `5min`
- `10min`
- `15min`
- `30min`
- `1hour`
- `4hour`
- `8hour`
- `12hour`
- `1day`
- `1week`
- `1month`

## Requirements

- Windows 10 or 11 (primary target)
- Python 3.10+ recommended
- Internet access (for GMO Coin API)

Python dependencies are listed in `requirements.txt`:

- `requests`
- `pandas`
- `numpy`
- `pyinstaller` (for EXE packaging)

## Setup (Development)

1. Create and activate a virtual environment.

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Run the app.

```bash
python app.py
```

## GUI Usage

1. Enter start date (`YYYY-MM-DD`).
2. Enter end date (`YYYY-MM-DD`).
3. Select interval.
4. Choose destination folder.
5. Click `Export Data`.

The app runs the export in a background thread and shows a completion dialog with the output file path.

## Output File

The exported file name format is:

```text
AllFeatures_<start_yyyymmdd>_<end_yyyymmdd>_<interval>.csv
```

Examples:

- `AllFeatures_20260101_20260131_1h.csv`
- `AllFeatures_20260401_20260407_5m.csv`

Notes:

- Index is `openTime` converted to `Asia/Tokyo` timezone.
- Missing values are filled with `0.0` before export.

## Feature Engineering Details

For each symbol, base columns from API are prefixed (example: `BTCJPY_open`, `BTCJPY_close`, ...).

### 1. Performance

For each candle:

$$
	ext{Performance} = \frac{\text{close} - \text{open}}{\text{open}}
$$

Column example:

- `BTCJPY_Performance`

### 2. Previous-Candle Features

Generated per symbol:

- `<SYMBOL>_PriceMoving_Previous`

$$
\frac{\text{close}_{t-1} - \text{open}_{t-1}}{\text{open}_{t-1}}
$$

- `<SYMBOL>_volumeMoving_Previous`

$$
\frac{\text{volume}_{t-1} - \text{volume}_{t-2}}{\text{volume}_{t-1}}
$$

- `<SYMBOL>_volume_prev`

$$
	ext{volume}_{t-1}
$$

- `<SYMBOL>_low2high_prev`

$$
\left|\text{high}_{t-1} - \text{low}_{t-1}\right|
$$

### 3. Action Flag

Threshold is fixed to `0.002` (0.2%).

- if `Performance >= 0.002` -> `1`
- if `Performance <= -0.002` -> `-1`
- otherwise -> `0`

Column example:

- `BTCJPY_ActionFlag`

## Extra API Snapshots

The pipeline also fetches current snapshot data and stores it as summary columns:

- `GMO_Ticker_Summary`
- `GMO_Orderbook_Summary`

These are stringified summaries and are identical for all rows in a single run.

## Validation Rules

- End date must be `2019-01-01` or later.
- Start date can be earlier, but internally clamped to `2019-01-01`.
- Start date must be less than or equal to end date.
- Destination folder and interval are required.

## Build as Standalone EXE

From project root:

```bash
pyinstaller --onefile --windowed --icon=assets/app.ico --add-data "assets/app.ico;assets" app.py
```

Output:

```text
dist\app.exe
```

## Project Structure

```text
FeatureGenerator/
├─ app.py
├─ requirements.txt
├─ README.md
├─ assets/
│  └─ app.ico
├─ build/
└─ dist/
```

## Troubleshooting

- If no data is returned for a date range, shorten the range and verify symbol/interval availability.
- If API access fails intermittently, retry export later (network/API-side issue).
- If EXE build fails, ensure the active environment has `pyinstaller` installed.

## Disclaimer

This tool is for data processing and research workflows. It does not provide investment advice.


