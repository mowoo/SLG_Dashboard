import pandas as pd
import os
import re
import datetime

# --- 配置 ---
DATA_FOLDER = "盟戰資料庫"
EXCLUDE_GROUPS = ['小號', '未分組']
RADAR_CONFIG = {
    'slave':  {'desc': '👮‍♂️ 抓地奴', 'merit_op': '小於 <=', 'merit_val': 10000, 'power_op': '大於 >=', 'power_val': 25000, 'eff_op': '小於 <=', 'eff_val': 2.0},
    'elite':  {'desc': '⚔️ 找戰神', 'merit_op': '大於 >=', 'merit_val': 100000, 'power_op': '大於 >=', 'power_val': 0, 'eff_op': '大於 >=', 'eff_val': 10.0},
    'newbie': {'desc': '👶 找萌新', 'merit_op': '小於 <=', 'merit_val': 5000, 'power_op': '小於 <=', 'power_val': 10000, 'eff_op': '大於 >=', 'eff_val': 0.0},
    'reset':  {'desc': '🔄 重置', 'merit_op': '大於 >=', 'merit_val': 0, 'power_op': '大於 >=', 'power_val': 0, 'eff_op': '大於 >=', 'eff_val': 0.0}
}

# --- IO 函數 ---
def save_uploaded_file(uploaded_file):
    if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
    try:
        with open(os.path.join(DATA_FOLDER, uploaded_file.name), "wb") as f: f.write(uploaded_file.getbuffer())
        return True
    except: return False

def load_data_from_folder():
    if not os.path.exists(DATA_FOLDER): return pd.DataFrame()
    all_data = []
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    if not files: return pd.DataFrame()
    
    for filename in files:
        try:
            df = pd.read_csv(os.path.join(DATA_FOLDER, filename))
            df.columns = df.columns.str.strip()
            
            # 清洗
            for col in ['戰功總量', '勢力值']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

            # 解析時間
            match = re.search(r'(\d{4})年(\d{2})月(\d{2})日(\d{2})[时|時](\d{2})分(\d{2})秒', filename)
            record_date = pd.to_datetime(f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)}:{match.group(5)}:{match.group(6)}") if match else pd.Timestamp.now()
            df['紀錄時間'] = record_date
            all_data.append(df)
        except: pass
        
    if not all_data: return pd.DataFrame()
    
    full_df = pd.concat(all_data, ignore_index=True).sort_values('紀錄時間')
    full_df['勢力值'] = full_df['勢力值'].replace(0, 1)
    full_df['戰功效率'] = (full_df['戰功總量'] / full_df['勢力值']).round(2)
    full_df = full_df[~full_df['分組'].isin(EXCLUDE_GROUPS)]
    return full_df

# --- 計算函數 ---
def calculate_daily_velocity(df, group_col=None):
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

def get_individual_global_max(raw_df):
    temp_df = calculate_daily_velocity(raw_df, group_col='成員')
    g_max_m = temp_df['daily_merit_growth'].max()
    g_max_p = temp_df['daily_power_growth'].max()
    g_min_p = temp_df['daily_power_growth'].min()
    return g_max_m, g_max_p, g_min_p