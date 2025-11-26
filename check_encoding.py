import pandas as pd
import os

file_path = r"c:\Users\mowoo\OneDrive\文件\SLG_Dashboard\盟戰資料庫\同盟統計2025年11月25日21时24分54秒.csv"

encodings = ['utf-8', 'big5', 'gbk', 'utf-16']

for enc in encodings:
    try:
        print(f"--- Trying encoding: {enc} ---")
        df = pd.read_csv(file_path, encoding=enc, nrows=2)
        print("Columns:", df.columns.tolist())
        print("First row:", df.iloc[0].tolist())
        print("Success!\n")
    except Exception as e:
        print(f"Failed with {enc}: {e}\n")
