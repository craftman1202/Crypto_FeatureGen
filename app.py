import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime, timedelta
import threading
import requests
import pandas as pd
import numpy as np
import os
import time


def run_crypto_pipeline(from_date, to_date, output_dir, interval="1hour"):
    """
    Main cryptocurrency data pipeline with GMO Coin API
    
    Args:
        from_date: Start datetime
        to_date: End datetime
        output_dir: Output directory path
        interval: Time interval (1min, 5min, 10min, 15min, 30min, 1hour, 4hour, 8hour, 12hour, 1day, 1week, 1month)
    """
    valid_start_date = datetime(2019, 1, 1)
    effective_from_date = max(from_date, valid_start_date)
    if to_date < valid_start_date:
        raise ValueError('End date must be 2019-01-01 or later.')

    endPoint = 'https://api.coin.z.com/public'
    klines_path = '/v1/klines'

    period = to_date - effective_from_date
    loop = period.days + 1

    def fetch_cryptocurrency_data(symbol, interval, from_date, loop):
        """Fetch klines data from GMO Coin API"""
        df_list = []
        for i in range(loop):
            date = (from_date + timedelta(days=i)).strftime('%Y%m%d')
            params = {
                'symbol': symbol,
                'interval': interval,
                'date': date
            }
            try:
                r = requests.get(endPoint + klines_path, params=params, timeout=10)
                if r.status_code != 200:
                    continue
                data = r.json().get('data', [])
                if data:
                    df_list.append(pd.DataFrame(data))
            except Exception as e:
                print(f"Warning: Failed to fetch {symbol} for {date}: {e}")
                continue

        if not df_list:
            raise ValueError(f"No data for {symbol}")
        return pd.concat(df_list, ignore_index=True)

    def process_and_prefix_df(df, symbol):
        """Process and add prefix to dataframe columns"""
        df = df.astype(float)
        df['openTime'] = pd.to_datetime(
            df['openTime'].astype('datetime64[ms]'),
            utc=True
        ).dt.tz_convert('Asia/Tokyo')
        df.set_index('openTime', inplace=True)
        df['Performance'] = (df['close'] - df['open']) / df['open']
        df.columns = [f"{symbol}_{c}" for c in df.columns]
        return df

    def fetch_gmo_ticker_data():
        """Fetch current ticker/exchange information from GMO Coin API"""
        ticker_path = '/v1/ticker'
        
        try:
            r = requests.get(endPoint + ticker_path, timeout=10)
            if r.status_code == 200:
                ticker_data = r.json().get('data', [])
                records = []
                for ticker in ticker_data:
                    records.append({
                        'symbol': ticker.get('symbol'),
                        'bid': float(ticker.get('bid', 0)),
                        'ask': float(ticker.get('ask', 0)),
                        'last': float(ticker.get('last', 0)),
                        'volume': float(ticker.get('volume', 0)),
                        'spread': float(ticker.get('ask', 0)) - float(ticker.get('bid', 0))
                    })
                if records:
                    return pd.DataFrame(records)
        except Exception as e:
            print(f"Warning: Failed to fetch ticker data: {e}")
        
        return pd.DataFrame()

    def fetch_gmo_orderbook_data():
        """Fetch orderbook (board) information from GMO Coin API"""
        orderbook_path = '/v1/orderbooks'
        
        try:
            symbols = ['BTC_JPY', 'ETH_JPY', 'XRP_JPY', 'LTC_JPY', 'BCH_JPY']
            all_orderbook_data = []
            
            for symbol in symbols:
                params = {'symbol': symbol}
                r = requests.get(endPoint + orderbook_path, params=params, timeout=10)
                
                if r.status_code == 200:
                    ob_data = r.json().get('data', {})
                    
                    asks = ob_data.get('asks', [])
                    bids = ob_data.get('bids', [])
                    
                    if asks:
                        ask_volume = sum([float(a[1]) for a in asks[:5]])
                        all_orderbook_data.append({
                            'symbol': symbol,
                            'side': 'ask',
                            'top_ask_price': float(asks[0][0]) if asks else None,
                            'top_ask_volume': float(asks[0][1]) if asks else 0,
                            'total_ask_volume_top5': ask_volume
                        })
                    
                    if bids:
                        bid_volume = sum([float(b[1]) for b in bids[:5]])
                        all_orderbook_data.append({
                            'symbol': symbol,
                            'side': 'bid',
                            'top_bid_price': float(bids[0][0]) if bids else None,
                            'top_bid_volume': float(bids[0][1]) if bids else 0,
                            'total_bid_volume_top5': bid_volume
                        })
                
                time.sleep(0.5)
            
            if all_orderbook_data:
                return pd.DataFrame(all_orderbook_data)
        except Exception as e:
            print(f"Warning: Failed to fetch orderbook data: {e}")
        
        return pd.DataFrame()

    # Fetch cryptocurrency data
    symbols = ['BTC_JPY', 'ETH_JPY', 'XRP_JPY', 'LTC_JPY', 'BCH_JPY']
    dfs = []

    for s in symbols:
        raw = fetch_cryptocurrency_data(s, interval, effective_from_date, loop)
        dfs.append(process_and_prefix_df(raw, s.replace('_', '')))

    combined_df = pd.concat(dfs, axis=1)

    # Fetch and add GMO Coin ticker data (exchange rate information)
    ticker_df = fetch_gmo_ticker_data()
    if not ticker_df.empty:
        combined_df['GMO_Ticker_Summary'] = str(ticker_df[['symbol', 'bid', 'ask', 'spread']].values)

    # Fetch and add GMO Coin orderbook data (board information)
    orderbook_df = fetch_gmo_orderbook_data()
    if not orderbook_df.empty:
        combined_df['GMO_Orderbook_Summary'] = str(orderbook_df[['symbol', 'side', 'top_bid_price']].values)

    combined_df.fillna(0.0, inplace=True)

    # ===============================
    # Previous Period Features
    # ===============================
    symbols_simple = ['BTCJPY', 'ETHJPY', 'XRPJPY', 'LTCJPY', 'BCHJPY']

    for s in symbols_simple:
        combined_df[f'{s}_PriceMoving_Previous'] = (
            (combined_df[f'{s}_close'].shift(1) - combined_df[f'{s}_open'].shift(1))
            / combined_df[f'{s}_open'].shift(1)
        )

        combined_df[f'{s}_volumeMoving_Previous'] = (
            (combined_df[f'{s}_volume'].shift(1) - combined_df[f'{s}_volume'].shift(2))
            / combined_df[f'{s}_volume'].shift(1)
        )

        combined_df[f'{s}_volume_prev'] = combined_df[f'{s}_volume'].shift(1)

        combined_df[f'{s}_low2high_prev'] = (
            combined_df[f'{s}_high'].shift(1) - combined_df[f'{s}_low'].shift(1)
        ).abs()

    # Action flags
    threshold = 0.002
    for s in symbols_simple:
        combined_df[f'{s}_ActionFlag'] = np.where(
            combined_df[f'{s}_Performance'] >= threshold, 1,
            np.where(combined_df[f'{s}_Performance'] <= -threshold, -1, 0)
        )

    # Output CSV with interval
    start_str = effective_from_date.strftime('%Y%m%d')
    end_str = to_date.strftime('%Y%m%d')
    interval_str = interval.replace('hour', 'h').replace('min', 'm')

    filename = f'AllFeatures_{start_str}_{end_str}_{interval_str}.csv'
    out_path = os.path.join(output_dir, filename)

    combined_df.to_csv(out_path)
    return out_path


def run_clicked():
    try:
        from_date = datetime.strptime(from_entry.get(), "%Y-%m-%d")
        to_date = datetime.strptime(to_entry.get(), "%Y-%m-%d")
        output_dir = path_var.get()
        interval = interval_var.get()
        valid_start_date = datetime(2019, 1, 1)

        if from_date > to_date:
            raise ValueError('Start date must be earlier than or equal to end date.')

        if to_date < valid_start_date:
            raise ValueError('End date must be 2019-01-01 or later.')

        if not output_dir:
            raise ValueError("Please select a destination folder.")

        if not interval:
            raise ValueError("Please select an interval.")

        status_var.set("Now processing...")
        threading.Thread(
            target=run_job,
            args=(from_date, to_date, output_dir, interval),
            daemon=True
        ).start()

    except Exception as e:
        messagebox.showerror("Error:", str(e))
        status_var.set("Error")

def run_job(from_date, to_date, output_dir, interval):
    try:
        out = run_crypto_pipeline(from_date, to_date, output_dir, interval)
        status_var.set(f"Done: {out}")
        messagebox.showinfo("Success", f"Data exported successfully:\n{out}")
    except Exception as e:
        status_var.set("Error")
        messagebox.showerror("Error while performing crypto data export:", str(e))

def browse_dir():
    path = filedialog.askdirectory()
    if path:
        path_var.set(path)


# GUI Setup
root = tk.Tk()
root.title("Crypto Data Exporter with GMO Coin API")
root.geometry("550x380")

# From date
tk.Label(root, text="Start date (YYYY-MM-DD)", font=("Arial", 10)).pack(pady=5)
from_entry = tk.Entry(root, width=30)
from_entry.pack()

# To date
tk.Label(root, text="End date (YYYY-MM-DD)", font=("Arial", 10)).pack(pady=5)
to_entry = tk.Entry(root, width=30)
to_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
to_entry.pack()

# Interval selector
tk.Label(root, text="Data Interval", font=("Arial", 10)).pack(pady=5)
interval_var = tk.StringVar(value="1hour")
interval_options = ['1min', '5min', '10min', '15min', '30min', 
                    '1hour', '4hour', '8hour', '12hour', '1day', '1week', '1month']
interval_combo = ttk.Combobox(root, textvariable=interval_var, 
                             values=interval_options, state="readonly", width=27)
interval_combo.pack()

# Output directory
tk.Label(root, text="Destination folder", font=("Arial", 10)).pack(pady=5)
path_var = tk.StringVar()
path_entry = tk.Entry(root, textvariable=path_var, width=30)
path_entry.pack()
tk.Button(root, text="Browse", command=browse_dir, bg="lightblue").pack(pady=5)

# Execute button
tk.Button(root, text="Export Data", command=run_clicked, 
         bg="green", fg="white", font=("Arial", 12, "bold")).pack(pady=15)

# Status label
status_var = tk.StringVar(value="Idle")
status_label = tk.Label(root, textvariable=status_var, font=("Arial", 9), fg="blue")
status_label.pack(pady=10)

# Info label
info_text = tk.Label(root, 
                    text="Features:\n- GMO Coin API (Ticker & Orderbook)\n- Configurable interval (1min - 1month)\n- No CryptoPanic dependency", 
                    font=("Arial", 8), justify=tk.LEFT, fg="gray")
info_text.pack(pady=5)

root.mainloop()
