import utils_data as ud
import pandas as pd

try:
    print("Attempting to load data...")
    df = ud.load_data_from_folder()
    
    if df.empty:
        print("DataFrame is empty. Check if CSV files exist in '盟戰資料庫'.")
    else:
        print(f"Loaded DataFrame with shape: {df.shape}")
        if '紀錄時間' in df.columns:
            print("'紀錄時間' column found.")
            print("First 5 timestamps:")
            print(df['紀錄時間'].head())
            print("Last 5 timestamps:")
            print(df['紀錄時間'].tail())
            
            # Verify sorting
            if df['紀錄時間'].is_monotonic_increasing:
                print("Data is sorted by '紀錄時間'.")
            else:
                print("Data is NOT sorted by '紀錄時間'.")
        else:
            print("ERROR: '紀錄時間' column NOT found.")

except Exception as e:
    print(f"An error occurred: {e}")
