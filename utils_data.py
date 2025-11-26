import pandas as pd
import os
import re
import datetime
import streamlit as st
from typing import Optional, Tuple

# --- Configuration ---
DATA_FOLDER = "盟戰資料庫"
EXCLUDE_GROUPS = ['小號', '未分組']
RADAR_CONFIG = {
    'slave':  {'desc': '👮‍♂️ 抓地奴', 'merit_op': '小於 <=', 'merit_val': 10000, 'power_op': '大於 >=', 'power_val': 25000, 'eff_op': '小於 <=', 'eff_val': 2.0},
    'elite':  {'desc': '⚔️ 找戰神', 'merit_op': '大於 >=', 'merit_val': 100000, 'power_op': '大於 >=', 'power_val': 0, 'eff_op': '大於 >=', 'eff_val': 10.0},
    'newbie': {'desc': '👶 找萌新', 'merit_op': '小於 <=', 'merit_val': 5000, 'power_op': '小於 <=', 'power_val': 10000, 'eff_op': '大於 >=', 'eff_val': 0.0},
    'reset':  {'desc': '🔄 重置', 'merit_op': '大於 >=', 'merit_val': 0, 'power_op': '大於 >=', 'power_val': 0, 'eff_op': '大於 >=', 'eff_val': 0.0}
}

# --- IO Functions ---
def save_uploaded_file(uploaded_file) -> bool:
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    try:
        file_path = os.path.join(DATA_FOLDER, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except Exception as e:
        st.error(f"Error saving file {uploaded_file.name}: {e}")
        return False

@st.cache_data(ttl=300)
def load_data_from_folder() -> pd.DataFrame:
    if not os.path.exists(DATA_FOLDER):
        return pd.DataFrame()
    
    all_data_frames = []
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    
    for filename in files:
        file_path = os.path.join(DATA_FOLDER, filename)
        df = pd.DataFrame()
        
        # 1. 嘗試多種編碼讀取
        encodings_to_try = ['utf-8-sig', 'utf-8', 'big5', 'gbk']
        for enc in encodings_to_try:
            try:
                df = pd.read_csv(file_path, encoding=enc)
                break
            except:
                continue
        
        if df.empty:
            st.warning(f"⚠️ 無法讀取檔案 {filename} (編碼失敗)")
            continue

        # 2. 清洗欄位名稱 (去除空白)
        df.columns = df.columns.str.strip()

        # 3. 欄位別名自動對應 (Mapping)
        # 如果 CSV 是簡體或別名，自動轉回標準名稱
        column_mapping = {
            '势力值': '勢力值', '势力': '勢力值', 'Power': '勢力值',
            '战功总量': '戰功總量', '战功': '戰功總量', 'Merit': '戰功總量',
            '分组': '分組', 'Group': '分組',
            '成员': '成員', 'Member': '成員',
            '所属势力': '所屬勢力', 'Region': '所屬勢力'
        }
        df.rename(columns=column_mapping, inplace=True)

        # 4. 讀取時間戳
        match = re.search(r'(\d{4})年(\d{2})月(\d{2})日(\d{2})[时|時](\d{2})分(\d{2})秒', filename)
        if match:
            dt_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)}:{match.group(5)}:{match.group(6)}"
            df['紀錄時間'] = pd.to_datetime(dt_str)
        else:
            # 檔名沒時間，跳過
            continue

        all_data_frames.append(df)
        
    if not all_data_frames:
        return pd.DataFrame()
    
    full_df = pd.concat(all_data_frames, ignore_index=True)
    if '紀錄時間' in full_df.columns:
        full_df = full_df.sort_values('紀錄時間')
        
    # 5. 最終檢查與除錯輸出
    required_cols = ['勢力值', '戰功總量', '分組']
    missing_cols = [col for col in required_cols if col not in full_df.columns]
    
    if missing_cols:
        st.error("❌ CSV 欄位讀取失敗")
        st.markdown(f"**缺少的欄位:** `{missing_cols}`")
        st.markdown(f"**實際讀到的欄位 (前5個):** `{list(full_df.columns)[:5]} ...`")
        st.warning("請截圖此畫面，或檢查 CSV 標題是否為亂碼 (Big5/GBK)。")
        return pd.DataFrame()
        
    # Data Cleaning
    for col in ['勢力值', '戰功總量']:
        full_df[col] = pd.to_numeric(full_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    full_df['勢力值'] = full_df['勢力值'].replace(0, 1)
    full_df['戰功效率'] = (full_df['戰功總量'] / full_df['勢力值']).round(2)
    full_df = full_df[~full_df['分組'].isin(EXCLUDE_GROUPS)]
    
    return full_df

# --- Calculation Functions ---
@st.cache_data(ttl=300)
def calculate_daily_velocity(df: pd.DataFrame, group_col: Optional[str] = None) -> pd.DataFrame:
    df = df.copy()
    df['date_only'] = df['紀錄時間'].dt.date
    
    daily_snapshots = df.groupby('date_only')['紀錄時間'].max().reset_index()
    df_daily = pd.merge(df, daily_snapshots, on=['date_only', '紀錄時間'], how='inner')
    
    if group_col:
        agged = df_daily.groupby(['紀錄時間', group_col])[['戰功總量', '勢力值']].sum().reset_index()
        agged = agged.sort_values([group_col, '紀錄時間'])
        agged['time_diff'] = agged.groupby(group_col)['紀錄時間'].diff().dt.total_seconds() / 86400
        agged['merit_diff'] = agged.groupby(group_col)['戰功總量'].diff()
        agged['power_diff'] = agged.groupby(group_col)['勢力值'].diff()
    else:
        agged = df_daily.groupby('紀錄時間')[['戰功總量', '勢力值']].sum().reset_index()
        agged = agged.sort_values('紀錄時間')
        agged['time_diff'] = agged['紀錄時間'].diff().dt.total_seconds() / 86400
        agged['merit_diff'] = agged['戰功總量'].diff()
        agged['power_diff'] = agged['勢力值'].diff()
        
    agged['daily_merit_growth'] = (agged['merit_diff'] / agged['time_diff']).fillna(0)
    agged['daily_power_growth'] = (agged['power_diff'] / agged['time_diff']).fillna(0)
    
    return agged

def get_individual_global_max(raw_df: pd.DataFrame) -> Tuple[float, float, float]:
    temp_df = calculate_daily_velocity(raw_df, group_col='成員')
    g_max_m = temp_df['daily_merit_growth'].max()
    g_max_p = temp_df['daily_power_growth'].max()
    g_min_p = temp_df['daily_power_growth'].min()
    return g_max_m, g_max_p, g_min_p