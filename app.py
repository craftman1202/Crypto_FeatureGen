import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timedelta
import threading
import requests
import pandas as pd
import numpy as np
import os


def run_crypto_pipeline(from_date, to_date, output_dir):
    endPoint = 'https://api.coin.z.com/public'
    path = '/v1/klines'

    period = to_date - from_date
    loop = period.days + 1

    def fetch_cryptocurrency_data(symbol, interval, from_date, loop):
        df_list = []
        for i in range(loop):
            date = (from_date + timedelta(days=i)).strftime('%Y%m%d')
            params = {
                'symbol': symbol,
                'interval': interval,
                'date': date
            }
            r = requests.get(endPoint + path, params=params)
            if r.status_code != 200:
                continue
            data = r.json().get('data', [])
            if data:
                df_list.append(pd.DataFrame(data))

        if not df_list:
            raise ValueError(f"No data for {symbol}")
        return pd.concat(df_list, ignore_index=True)

    def process_and_prefix_df(df, symbol):
        df = df.astype(float)
        df['openTime'] = pd.to_datetime(
            df['openTime'].astype('datetime64[ms]'),
            utc=True
        ).dt.tz_convert('Asia/Tokyo')
        df.set_index('openTime', inplace=True)
        df['Performance'] = (df['close'] - df['open']) / df['open']
        df.columns = [f"{symbol}_{c}" for c in df.columns]
        return df

    symbols = ['BTC_JPY', 'ETH_JPY', 'XRP_JPY', 'LTC_JPY', 'BCH_JPY']
    dfs = []

    for s in symbols:
        raw = fetch_cryptocurrency_data(s, '1hour', from_date, loop)
        dfs.append(process_and_prefix_df(raw, s.replace('_', '')))

    combined_df = pd.concat(dfs, axis=1)

    # ===============================
    # Previous Hour Features
    # ===============================
    symbols_simple = ['BTCJPY', 'ETHJPY', 'XRPJPY', 'LTCJPY', 'BCHJPY']

    for s in symbols_simple:
        combined_df[f'{s}_PriceMoving_PreviousHour'] = (
            (combined_df[f'{s}_close'].shift(1) - combined_df[f'{s}_open'].shift(1))
            / combined_df[f'{s}_open'].shift(1)
        )

        combined_df[f'{s}_volumeMoving_PreviousHour'] = (
            (combined_df[f'{s}_volume'].shift(1) - combined_df[f'{s}_volume'].shift(2))
            / combined_df[f'{s}_volume'].shift(1)
        )

        combined_df[f'{s}_volume_prev'] = combined_df[f'{s}_volume'].shift(1)

        combined_df[f'{s}_low2high_prev'] = (
            combined_df[f'{s}_high'].shift(1) - combined_df[f'{s}_low'].shift(1)
        ).abs()

    # フラグ
    threshold = 0.002
    for s in symbols_simple:
        combined_df[f'{s}_ActionFlag_hour'] = np.where(
            combined_df[f'{s}_Performance'] >= threshold, 1,
            np.where(combined_df[f'{s}_Performance'] <= -threshold, -1, 0)
        )

    # 出力
    start_str = from_date.strftime('%Y%m%d')
    end_str = to_date.strftime('%Y%m%d')

    filename = f'AllFeatures_{start_str}_{end_str}.csv'
    out_path = os.path.join(output_dir, filename)

    combined_df.to_csv(out_path)
    return out_path


def run_clicked():
    try:
        from_date = datetime.strptime(from_entry.get(), "%Y-%m-%d")
        to_date = datetime.strptime(to_entry.get(), "%Y-%m-%d")
        output_dir = path_var.get()

        if not output_dir:
            raise ValueError("Please select a destination folder.")

        status_var.set("Now processing...")
        threading.Thread(
            target=run_job,
            args=(from_date, to_date, output_dir),
            daemon=True
        ).start()

    except Exception as e:
        messagebox.showerror("Error:", str(e))

def run_job(from_date, to_date, output_dir):
    try:
        out = run_crypto_pipeline(from_date, to_date, output_dir)
        status_var.set(f"Done: {out}")
    except Exception as e:
        status_var.set("Error")
        messagebox.showerror("Error while performing crypto data export:", str(e))

def browse_dir():
    path = filedialog.askdirectory()
    if path:
        path_var.set(path)

root = tk.Tk()
root.title("Crypto Data Exporter")
root.geometry("500x250")

tk.Label(root, text="Start date (YYYY-MM-DD)").pack()
from_entry = tk.Entry(root)
from_entry.pack()

tk.Label(root, text="End date (YYYY-MM-DD)").pack()
to_entry = tk.Entry(root)
to_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
to_entry.pack()

tk.Label(root, text="Destination folder").pack()
path_var = tk.StringVar()
tk.Entry(root, textvariable=path_var, width=50).pack()
tk.Button(root, text="refer", command=browse_dir).pack()

tk.Button(root, text="Perform", command=run_clicked, bg="green", fg="white").pack(pady=10)

status_var = tk.StringVar(value="Idle")
tk.Label(root, textvariable=status_var).pack()

root.mainloop()
