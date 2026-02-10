# Crypto Feature Generator

A **Windows desktop application built with tkinter** that retrieves cryptocurrency  
1-hour OHLCV data from the **GMO Coin Public API**, generates trading features,  
and exports them as CSV files.

The application can be bundled into a standalone `.exe`, allowing it to run  
on machines without Python installed.

---

## Features

- Simple tkinter GUI
- Specify date range and output directory
- Fetch OHLCV data from GMO Coin Public API
- Merge multiple cryptocurrencies on a unified time index
- Generate price- and volume-based features
- Export features to CSV
- Build as a standalone Windows executable

---

## Project Structure

```text
FeatureGenerator/
├─ app.py                 # GUI and feature generation logic
├─ requirements.txt       # Python dependencies
├─ assets/
│  └─ app.ico             # Application icon
├─ README.md
└─ .gitignore
```

## Setup (For Development)

### 1. Create a virtual environment (Anaconda recommended)

```bash
conda create -n Crypto_FeatureGenerator python=3.10
conda activate Crypto_FeatureGenerator
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the GUI application
```bash
python app.py
```

## Building the Executable (Windows)

### Requirements

- Windows 10 / 11
- Python installed via python.org or Anaconda  
  **Microsoft Store Python is not supported**
- PyInstaller installed

---

### Build Command

```bash
pyinstaller --onefile --windowed --icon=assets/app.ico --add-data "assets/app.ico;assets" app.py
```

### Output

```text
dist/
└─ app.exe
```
Distribute app.exe to run the application on machines without Python.

## Feature Generation Logic

### Data Source

- GMO Coin Public API endpoint: `/v1/klines`
- Interval: `1hour`
- Supported symbols:
  - BTC_JPY
  - ETH_JPY
  - XRP_JPY
  - LTC_JPY
  - BCH_JPY

---

### Preprocessing

- Convert `openTime` from UTC to Asia/Tokyo timezone
- Set `openTime` as the DataFrame index
- Prefix all columns with symbol names  
  (e.g. `BTCJPY_open`, `ETHJPY_close`)

---

### Core Feature: Price Performance

```text
Performance = (close - open) / open
```

---
## Trading Action Flags

threshold = 0.002 (0.2%)

| Condition                       | ActionFlag |
|---------------------------------|------------|
| Performance ≥ threshold         | 1 (Buy)    |
| Performance ≤ -threshold        | -1 (Sell)  |
| Otherwise                       | 0 (Hold)   |

Generated column examples:

- BTCJPY_ActionFlag_hour
- ETHJPY_ActionFlag_hour
- XRPJPY_ActionFlag_hour
- LTCJPY_ActionFlag_hour
- BCHJPY_ActionFlag_hour

---

## Lag-Based Features (Previous Hour)

### Price Movement

Price change rate of the previous hourly candle:

(close[t-1] - open[t-1]) / open[t-1]

---

### Volume Change Rate

Volume change rate compared to the previous hour:

(volume[t-1] - volume[t-2]) / volume[t-1]

---

### Previous Hour Volume

Raw volume of the previous hour:

volume[t-1]

---

### High–Low Range

Price range of the previous hour:

abs(high[t-1] - low[t-1])

---

## Output

- Index: openTime (JST)
- Feature columns for all trading pairs are horizontally concatenated
- Output is directly usable for:
  - Machine learning model training
  - Backtesting trading strategies
  - Live inference pipelines

---

## Notes

- Data availability depends on the GMO Coin API status
- Longer date ranges increase API calls and execution time
- Execution time grows approximately linearly with the specified period
- This tool does not provide investment advice

---


