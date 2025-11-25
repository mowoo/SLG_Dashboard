import streamlit as st
import pandas as pd
import altair as alt
import re
import os
import extra_streamlit_components as stx
import datetime

# --- 1. 頁面配置與 CSS ---
st.set_page_config(page_title="戰略指揮中心", layout="wide", page_icon="🏯")

st.markdown("""
<style>
    /* 全域背景 */
    .stApp { background-color: #121212; color: #E0E0E0; }
    
    /* 緊湊版面 */
    .block-container {
        max_width: 1024px !important;
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    
    div[data-testid="column"] { gap: 0.5rem; }
    
    /* 標題 */
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 400; margin: 0 0 0.5rem 0 !important; letter-spacing: 1px; }
    
    /* 側邊欄 */
    section[data-testid="stSidebar"] { background-color: #0d0d0d; border-right: 1px solid #333; }
    
    /* KPI 卡片 */
    .kpi-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 6px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100%;
    }
    .kpi-label { color: #888; font-size: 0.85rem; margin-bottom: 5px; }
    .kpi-value { color: #FFF; font-size: 1.6rem; font-weight: bold; font-family: 'Arial Black', sans-serif; }
    
    /* 戰術分級色票 */
    .tier-s { color: #00FF55 !important; text-shadow: 0 0 15px rgba(0, 255, 85, 0.3); }
    .tier-a { color: #00E5FF !important; text-shadow: 0 0 10px rgba(0, 229, 255, 0.3); }
    .tier-b { color: #E0E0E0 !important; }

    /* 卡片 */
    .dashboard-card { background-color: #1E1E1E; border: 1px solid #333; border-radius: 6px; padding: 15px; margin-bottom: 15px; }
    .card-cyan { border-top: 3px solid #00E5FF; }
    .card-red { border-top: 3px solid #D04F4F; }
    .card-blue { border-top: 3px solid #4F8CD0; }
    .card-purple { border-top: 3px solid #9B4FD0; }
    .card-gold { border-top: 3px solid #D4AF37; }

    /* 列表表格 */
    .clean-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    .clean-table th { text-align: right; padding: 8px; color: #888; border-bottom: 1px solid #444; font-weight: normal; }
    .clean-table th:first-child { text-align: left; }
    .clean-table td { text-align: right; padding: 8px; color: #DDD; border-bottom: 1px solid #2A2A2A; }
    .clean-table td:first-child { text-align: left; color: #FFF; font-weight: bold; }
    .clean-table tr:hover { background-color: #2A2A2A; }

    /* 元件 */
    .stSelectbox, .stNumberInput, .stTextInput { margin-bottom: 0px !important; }
    div[data-testid="stSelectbox"] > div > div { background-color: #262626; border-color: #444; color: #DDD; min-height: 35px; }
    div[data-testid="stNumberInput"] > div > div > input { background-color: #262626; color: #DDD; min-height: 35px; }
    div.stButton > button { width: 100%; background-color: #262626; color: #AAA; border: 1px solid #444; border-radius: 4px; padding: 0.3rem; }
    div.stButton > button:hover { border-color: #777; color: #FFF; background-color: #333; }
    
    /* 彈窗 */
    div[role="dialog"] { 
        background-color: #000 !important; 
        border: 1px solid #555; 
        width: 72vw !important; 
        max-width: 1200px !important;
    }
    
    /* 王牌檔案樣式 */
    .ace-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .ace-table td { padding: 5px 0; vertical-align: bottom; border-bottom: 1px solid #333; }
    .ace-label-col { width: 1%; white-space: nowrap; font-size: 1.1rem; color: #888; text-transform: uppercase; padding-right: 15px !important; font-weight: bold; letter-spacing: 1px; }
    .ace-value-col { font-family: 'Arial Black', 'Helvetica Black', sans-serif; font-size: 48px; font-weight: 900; line-height: 1; color: #E0E0E0; text-align: left; }
    .val-elite { color: #FFE100; text-shadow: 0 0 20px rgba(255, 225, 0, 0.5); }
    .val-front { color: #00FF55; text-shadow: 0 0 15px rgba(0, 255, 85, 0.4); }
    @media (min-width: 1400px) { .ace-value-col { font-size: 64px; } }
    
    /* 版本浮水印 */
    .version-tag {
        position: fixed;
        bottom: 10px;
        left: 10px;
        background-color: rgba(0, 0, 0, 0.7);
        color: #555;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 0.8rem;
        z-index: 9999;
        pointer-events: none;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Cookie & Data ---
cookie_manager = stx.CookieManager()
DATA_FOLDER = "盟戰資料庫"
if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)

def save_uploaded_file(uploaded_file):
    try:
        with open(os.path.join(DATA_FOLDER, uploaded_file.name), "wb") as f: f.write(uploaded_file.getbuffer())
        return True
    except: return False

def load_data_from_folder():
    all_data = []
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    if not files: return pd.DataFrame()
    for filename in files:
        try:
            df = pd.read_csv(os.path.join(DATA_FOLDER, filename))
            df.columns = df.columns.str.strip()
            match = re.search(r'(\d{4})年(\d{2})月(\d{2})日(\d{2})[时|時](\d{2})分(\d{2})秒', filename)
            record_date = pd.to_datetime(f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)}:{match.group(5)}:{match.group(6)}") if match else pd.Timestamp.now()
            df['紀錄時間'] = record_date
            all_data.append(df)
        except: pass
    if not all_data: return pd.DataFrame()
    full_df = pd.concat(all_data, ignore_index=True).sort_values('紀錄時間')
    full_df['勢力值'] = full_df['勢力值'].replace(0, 1)
    full_df['戰功效率'] = (full_df['戰功總量'] / full_df['勢力值']).round(2)
    return full_df

# --- 3. 智慧門禁 ---
def check_password():
    if st.session_state.get("password_correct", False): return True
    auth_token = cookie_manager.get("auth_token")
    if auth_token == "valid":
        st.session_state["password_correct"] = True
        return True
    if "password" not in st.secrets: return True

    placeholder = st.empty()
    with placeholder.container():
        st.markdown("### 🔒 指揮官權限驗證")
        pwd = st.text_input("請輸入密碼", type="password", key="login_pwd")
        if pwd:
            if pwd == st.secrets["password"]:
                st.session_state["password_correct"] = True
                expires = datetime.datetime.now() + datetime.timedelta(hours=1)
                cookie_manager.set("auth_token", "valid", expires_at=expires)
                placeholder.empty()
                st.rerun()
            else:
                st.error("⛔ 密碼錯誤")
                st.stop()
        else:
            st.stop()

check_password()

# --- 4. 數據運算 (日均成長) ---
def calculate_daily_velocity(df, group_col=None):
    df['date_only'] = df['紀錄時間'].dt.date
    daily_snapshots = df.groupby('date_only')['紀錄時間'].max().reset_index()
    df_daily = pd.merge(df, daily_snapshots, on=['date_only', '紀錄時間'], how='inner')
    
    if group_col:
        agged = df_daily.groupby(['紀錄時間', group_col])[['戰功總量', '勢力值']].sum().reset_index()
        agged = agged.sort_values(['分組', '紀錄時間'])
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

# [NEW] 計算全域個人成長極值 (用於鎖定圖表 Y 軸)
def get_global_individual_max(df):
    # 為了效能，這裡做一次全表計算，只取必要欄位
    temp_df = df[['成員', '紀錄時間', '戰功總量', '勢力值']].copy()
    temp_df['date_only'] = temp_df['紀錄時間'].dt.date
    # 每日快照
    daily_df = temp_df.sort_values('紀錄時間').groupby(['成员', 'date_only']).tail(1) # 修正欄位名稱
    # 注意：groupby 欄位要是 '成員'
    daily_df = temp_df.sort_values(['成員', '紀錄時間']).groupby(['成員', 'date_only']).tail(1)
    
    daily_df['time_diff'] = daily_df.groupby('成員')['紀錄時間'].diff().dt.total_seconds() / 86400
    daily_df['merit_diff'] = daily_df.groupby('成員')['戰功總量'].diff()
    daily_df['power_diff'] = daily_df.groupby('成員')['勢力值'].diff()
    
    daily_df['daily_merit'] = (daily_df['merit_diff'] / daily_df['time_diff']).fillna(0)
    daily_df['daily_power'] = (daily_df['power_diff'] / daily_df['time_diff']).fillna(0)
    
    # 排除異常值 (例如第一天或數據錯誤導致的無限大)
    # 這裡簡單取 99.9% 分位數作為上限，避免一個極端值毀了整張圖，或者直接取 Max
    # 為求真實，先取 Max，若圖表壞掉再調整
    max_merit = daily_df['daily_merit'].max()
    max_power = daily_df['daily_power'].max()
    min_power = daily_df['daily_power'].min() # 勢力可能負成長
    
    return max_merit, max_power, min_power

# --- 5. 狀態與 Cookie ---
if 'last_selected_member' not in st.session_state: st.session_state.last_selected_member = None
cookies_font_size = cookie_manager.get(cookie="font_size")
cookies_frontline = cookie_manager.get(cookie="frontline_regions")
if 'font_size' not in st.session_state: st.session_state.font_size = int(cookies_font_size) if cookies_font_size else 18
if 'frontline_regions' not in st.session_state: st.session_state.frontline_regions = cookies_frontline.split(',') if cookies_frontline else []

default_vals = {'q_merit_op': '大於 >=', 'q_merit_val': 0, 'q_power_op': '大於 >=', 'q_power_val': 0, 'q_eff_op': '大於 >=', 'q_eff_val': 0.0, 'q_rank': 300}
for k, v in default_vals.items(): 
    if k not in st.session_state: st.session_state[k] = v

def set_preset(ptype):
    updates = {'slave':{'q_merit_op':'小於 <=','q_merit_val':10000,'q_power_op':'大於 >=','q_power_val':25000,'q_eff_op':'小於 <=','q_eff_val':2.0},
               'elite':{'q_merit_op':'大於 >=','q_merit_val':100000,'q_power_op':'大於 >=','q_power_val':0,'q_eff_op':'大於 >=','q_eff_val':10.0},
               'newbie':{'q_merit_op':'小於 <=','q_merit_val':5000,'q_power_op':'小於 <=','q_power_val':10000,'q_eff_op':'大於 >=','q_eff_val':0.0},
               'reset':{'q_merit_op':'大於 >=','q_merit_val':0,'q_power_op':'大於 >=','q_power_val':0,'q_eff_op':'大於 >=','q_eff_val':0.0}}
    for k, v in updates.get(ptype, {}).items(): st.session_state[k] = v

def update_font_cookie(): cookie_manager.set("font_size", st.session_state.font_size_slider); st.session_state.font_size = st.session_state.font_size_slider
def update_frontline_cookie(): cookie_manager.set("frontline_regions", ",".join(st.session_state.frontline_select)); st.session_state.frontline_regions = st.session_state.frontline_select

def get_eff_color_style(val):
    if val > 10: return "color: #00FF55"
    if val >= 5: return "color: #00E5FF"
    return "color: #E0E0E0"

def get_eff_class(val):
    if val > 10: return "tier-s"
    if val >= 5: return "tier-a"
    return "tier-b"

@st.dialog("王牌戰略檔案", width="large")
def show_member_popup(member_name, raw_df, global_max_merit, global_max_power, global_min_power):
    member_data = raw_df[raw_df['成員'] == member_name].copy()
    member_data['date_only'] = member_data['紀錄時間'].dt.date
    history = member_data.sort_values('紀錄時間').groupby('date_only').tail(1)
    
    history['time_diff'] = history['紀錄時間'].diff().dt.total_seconds() / 86400
    history['merit_diff'] = history['戰功總量'].diff()
    history['power_diff'] = history['勢力值'].diff()
    history['daily_merit_growth'] = (history['merit_diff'] / history['time_diff']).fillna(0)
    history['daily_power_growth'] = (history['power_diff'] / history['time_diff']).fillna(0)
    
    curr = history.iloc[-1]
    latest_df = raw_df[raw_df['紀錄時間'] == raw_df['紀錄時間'].max()]
    rank = curr['貢獻排行']
    total = len(latest_df)
    
    val_class_merit = "color: #FFE100; text-shadow: 0 0 20px rgba(255, 225, 0, 0.6);" if rank <= total * 0.1 else ("color: #00FF55; text-shadow: 0 0 15px rgba(0, 255, 85, 0.5);" if rank <= total * 0.3 else "color: #E0E0E0;")
    val_style_eff = get_eff_color_style(curr['戰功效率'])
    if curr['戰功效率'] > 10: val_style_eff += "; text-shadow: 0 0 15px rgba(0, 255, 85, 0.3);"
    elif curr['戰功效率'] >= 5: val_style_eff += "; text-shadow: 0 0 10px rgba(0, 229, 255, 0.3);"

    col_left, col_right = st.columns([1.2, 2.8], gap="large")
    with col_left:
        st.markdown(f"## {member_name}")
        st.caption(f"📍 {curr['所屬勢力']} | 🏷️ {curr['分組']}")
        st.markdown("---")
        st.markdown(f"""<table class="ace-table">
            <tr><td class="ace-label-col">⚔️ 戰功</td><td class="ace-value-col" style="{val_class_merit}">{int(curr['戰功總量']):,}</td></tr>
            <tr><td class="ace-label-col">🏰 勢力</td><td class="ace-value-col" style="color: #E0E0E0;">{int(curr['勢力值']):,}</td></tr>
            <tr><td class="ace-label-col">⚡ 效率</td><td class="ace-value-col" style="{val_style_eff}">{curr['戰功效率']}</td></tr>
            <tr><td class="ace-label-col">🏅 排名</td><td class="ace-value-col" style="color: #E0E0E0;">#{curr['貢獻排行']}</td></tr>
        </table>""", unsafe_allow_html=True)
        
    with col_right:
        st.markdown("##### 🚀 戰力加速度 (日均成長速率)")
        base = alt.Chart(history).encode(x=alt.X('紀錄時間', axis=alt.Axis(format='%m/%d', title=None)))
        
        # [核心修正] 
        # 1. Y軸 Scale 鎖定全域最大值
        # 2. 圖例互換：戰功 (黃, Area) 放右軸, 勢力 (綠, Line) 放左軸
        # 3. Axis 標題顏色匹配
        
        # 勢力 (Line) - 放左軸
        line = base.mark_line(interpolate='basis', color='#00FF55', strokeWidth=3).encode(
            y=alt.Y('daily_power_growth', 
                    title='日增勢力 (綠)', 
                    axis=alt.Axis(titleColor='#00FF55'),
                    scale=alt.Scale(domain=[global_min_power, global_max_power])), 
            tooltip=['紀錄時間', alt.Tooltip('daily_power_growth', format=',.0f')]
        )
        
        # 戰功 (Area) - 放右軸
        area = base.mark_area(interpolate='basis', line={'color':'#FFE100'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='rgba(255, 225, 0, 0.5)', offset=0), alt.GradientStop(color='rgba(255, 225, 0, 0.1)', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(
            y=alt.Y('daily_merit_growth', 
                    title='日增戰功 (黃)', 
                    axis=alt.Axis(titleColor='#FFE100', orient='right'),
                    scale=alt.Scale(domain=[0, global_max_merit])), 
            tooltip=['紀錄時間', alt.Tooltip('daily_merit_growth', format=',.0f')]
        )
        
        st.altair_chart((line + area).resolve_scale(y='independent').properties(height=600, padding={"left": 20, "right": 20, "top": 10, "bottom": 10}).interactive(), use_container_width=True)

# --- 6. 主程式 ---
st.sidebar.title("🎛️ 指揮台")
up = st.sidebar.file_uploader("📥 上傳", type=['csv'], accept_multiple_files=True)
if up: 
    if sum([save_uploaded_file(f) for f in up]): st.sidebar.success("已存檔")

raw_df = load_data_from_folder()
if raw_df.empty: st.warning("無資料"); st.stop()

latest_df = raw_df[raw_df['紀錄時間'] == raw_df['紀錄時間'].max()].copy()
latest_time_str = latest_df['紀錄時間'].iloc[0].strftime('%Y/%m/%d %H:%M')
st.sidebar.caption(f"📅 {latest_time_str}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"<div style='text-align: center; color: #666; font-size: 0.8rem;'>戰略指揮中心 v46.0<br>Updated: {latest_time_str}</div>", unsafe_allow_html=True)

grps = list(latest_df['分組'].unique())
sel_grps = st.sidebar.multiselect("分組", grps, default=grps)
filt_df = latest_df[latest_df['分組'].isin(sel_grps)]

# [預先計算全域極值] - 在主程式層級計算一次，傳給彈窗使用
# 為了避免每次彈窗都重算，這裡算好變數
# (注意：這裡只算了一次全域的，效能較佳)
# 重新實作簡單版的 max 計算以確保變數存在
temp_all = raw_df.copy()
temp_all['date_only'] = temp_all['紀錄時間'].dt.date
temp_daily = temp_all.sort_values(['成員', '紀錄時間']).groupby(['成員', 'date_only']).tail(1)
temp_daily['t_diff'] = temp_daily.groupby('成員')['紀錄時間'].diff().dt.total_seconds() / 86400
temp_daily['m_diff'] = temp_daily.groupby('成員')['戰功總量'].diff()
temp_daily['p_diff'] = temp_daily.groupby('成員')['勢力值'].diff()
temp_daily['v_m'] = (temp_daily['m_diff'] / temp_daily['t_diff']).fillna(0)
temp_daily['v_p'] = (temp_daily['p_diff'] / temp_daily['t_diff']).fillna(0)
G_MAX_MERIT = temp_daily['v_m'].max()
G_MAX_POWER = temp_daily['v_p'].max()
G_MIN_POWER = temp_daily['v_p'].min()

st.sidebar.markdown("---")
kw = st.sidebar.text_input("搜索", placeholder="關鍵字...")
if kw:
    m = filt_df[filt_df['成員'].str.contains(kw, na=False)]['成員'].unique()
    if len(m) > 0:
        t = st.sidebar.selectbox("結果", m)
        if st.sidebar.button("調用"):
            show_member_popup(t, raw_df, G_MAX_MERIT, G_MAX_POWER, G_MIN_POWER)
    else:
        st.sidebar.warning("無結果")

st.markdown("<h2 style='color:#DDD;'>🏯 戰略指揮中心</h2>", unsafe_allow_html=True)

avg_eff = filt_df['戰功效率'].mean()
eff_class = get_eff_class(avg_eff)
k1, k2, k3, k4 = st.columns(4)
with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>總戰功</div><div class='kpi-value'>{int(filt_df['戰功總量'].sum()):,}</div></div>", unsafe_allow_html=True)
with k2: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>總勢力</div><div class='kpi-value'>{int(filt_df['勢力值'].sum()):,}</div></div>", unsafe_allow_html=True)
with k3: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>活躍人數</div><div class='kpi-value'>{len(filt_df):,}</div></div>", unsafe_allow_html=True)
with k4: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>平均效率</div><div class='kpi-value {eff_class}'>{avg_eff:.2f}</div></div>", unsafe_allow_html=True)

st.markdown(f"""<div class="version-tag">v46.0 | {latest_time_str}</div>""", unsafe_allow_html=True)

# 0. 動能
st.markdown("<div class='dashboard-card card-cyan'>", unsafe_allow_html=True)
st.markdown("### 📈 戰略動能分析")
ct1, ct2 = st.columns(2)
# [修正] 全盟與分組圖表也鎖定最大值 (使用前面計算的 G_MAX_MERIT 可能太大，因為那是個人的，這裡應該用全盟/分組的 MAX)
# 為了保持簡單，這裡先維持自動縮放或使用各自的邏輯，用戶需求主要是針對「個人彈窗」
with ct1:
    st.caption("🌍 全盟")
    av = calculate_daily_velocity(raw_df)
    # 全盟圖表鎖定 (全盟 Max)
    am_max_m = av['daily_merit_growth'].max()
    am_max_p = av['daily_power_growth'].max()
    ba = alt.Chart(av).encode(x=alt.X('紀錄時間', axis=alt.Axis(format='%m/%d', title=None)))
    aa = ba.mark_area(interpolate='basis', line={'color':'#00E5FF'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='rgba(0, 229, 255, 0.5)', offset=0), alt.GradientStop(color='rgba(0, 229, 255, 0.1)', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(y=alt.Y('daily_merit_growth', title='日增戰功', scale=alt.Scale(domain=[0, am_max_m])), tooltip=['紀錄時間', alt.Tooltip('daily_merit_growth', format=',.0f')])
    la = ba.mark_line(interpolate='basis', color='#FF00FF', strokeWidth=2).encode(y=alt.Y('daily_power_growth', title='日增勢力', scale=alt.Scale(domain=[av['daily_power_growth'].min(), am_max_p])), tooltip=['紀錄時間', alt.Tooltip('daily_power_growth', format=',.0f')])
    st.altair_chart((aa + la).resolve_scale(y='independent').interactive(), use_container_width=True)
with ct2:
    st.caption("🚩 分組")
    tg = st.selectbox("選擇分組", grps, key="tgs", label_visibility="collapsed")
    gv_all = calculate_daily_velocity(raw_df, group_col='分組')
    gv = gv_all[gv_all['分組'] == tg]
    # 分組圖表鎖定 (所有分組中的 Max)
    grp_max_m = gv_all['daily_merit_growth'].max()
    grp_max_p = gv_all['daily_power_growth'].max()
    bg = alt.Chart(gv).encode(x=alt.X('紀錄時間', axis=alt.Axis(format='%m/%d', title=None)))
    ag = bg.mark_area(interpolate='basis', line={'color':'#FFE100'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='rgba(255, 225, 0, 0.5)', offset=0), alt.GradientStop(color='rgba(255, 225, 0, 0.1)', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(y=alt.Y('daily_merit_growth', title='日增戰功', scale=alt.Scale(domain=[0, grp_max_m])), tooltip=['紀錄時間', alt.Tooltip('daily_merit_growth', format=',.0f')])
    lg = bg.mark_line(interpolate='basis', color='#00FF55', strokeWidth=2).encode(y=alt.Y('daily_power_growth', title='日增勢力', scale=alt.Scale(domain=[gv_all['daily_power_growth'].min(), grp_max_p])), tooltip=['紀錄時間', alt.Tooltip('daily_power_growth', format=',.0f')])
    st.altair_chart((ag + lg).resolve_scale(y='independent').interactive(), use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# 1. 集團軍
st.markdown("<div class='dashboard-card card-red'>", unsafe_allow_html=True)
c1, c2 = st.columns([4, 1])
with c1: st.markdown("### 🏳️ 集團軍情報")
with c2: fs = st.slider("字體", 14, 30, value=st.session_state.font_size, key="font_size_slider", on_change=update_font_cookie, label_visibility="collapsed")
gs = filt_df.groupby('分組').agg(n=('成員','count'), wm=('戰功總量','sum'), awm=('戰功總量','mean'), p=('勢力值','sum'), ap=('勢力值','mean')).reset_index().sort_values('wm', ascending=False)
html_content = f"<style>.clean-table td, .clean-table th {{ font-size: {fs}px; }}</style><table class='clean-table'><thead><tr><th>分組</th><th>人數</th><th>總戰功</th><th>平均戰功</th><th>總勢力</th><th>平均勢力</th></tr></thead><tbody>"
for _, r in gs.iterrows(): html_content += f"<tr><td>{r['分組']}</td><td>{r['n']}</td><td>{int(r['wm']):,}</td><td>{int(r['awm']):,}</td><td>{int(r['p']):,}</td><td>{int(r['ap']):,}</td></tr>"
html_content += "</tbody></table>"
st.markdown(html_content, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 2. 重點名單
st.markdown("<div class='dashboard-card card-blue'>", unsafe_allow_html=True)
c1, c2 = st.columns([4, 1])
with c1: st.markdown("### 🏆 重點人員名單")
with c2: nr = st.number_input("行數", 5, 50, 10, step=5, label_visibility="collapsed")
cl1, cl2, cl3 = st.columns(3)
tm = None
def style_eff_col(s): return [get_eff_color_style(v) for v in s]
with cl1:
    st.caption("🔥 十大戰功")
    d1 = filt_df.nlargest(nr, '戰功總量')[['成員','分組','戰功總量']]
    e1 = st.dataframe(d1, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="t1", column_config={"戰功總量": st.column_config.ProgressColumn(" ", format="%d", max_value=int(latest_df['戰功總量'].max()))})
    if len(e1.selection['rows']): tm = d1.iloc[e1.selection['rows'][0]]['成員']
with cl2:
    st.caption("⚡ 十大效率")
    d2 = filt_df[filt_df['勢力值']>10000].nlargest(nr, '戰功效率')[['成員','分組','戰功效率']]
    s2 = d2.style.format({"戰功效率": "{:.2f}"}).apply(style_eff_col, subset=["戰功效率"])
    e2 = st.dataframe(s2, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="t2")
    if len(e2.selection['rows']): tm = d2.iloc[e2.selection['rows'][0]]['成員']
with cl3:
    st.caption("🐢 遲緩名單")
    avg = latest_df['勢力值'].mean()
    d3 = filt_df[filt_df['勢力值']>avg].nsmallest(nr, '戰功效率')[['成員','勢力值','戰功效率']]
    s3 = d3.style.format({"勢力值": "{:,}", "戰功效率": "{:.2f}"}).apply(style_eff_col, subset=["戰功效率"])
    e3 = st.dataframe(s3, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="t3")
    if len(e3.selection['rows']): tm = d3.iloc[e3.selection['rows'][0]]['成員']
st.markdown("</div>", unsafe_allow_html=True)

# 3. 雷達
st.markdown("<div class='dashboard-card card-purple'>", unsafe_allow_html=True)
st.markdown("### 🛰️ 戰術搜索雷達")
cb1, cb2, cb3, cb4 = st.columns(4)
if cb1.button("👮‍♂️ 抓地奴"): set_preset('slave')
if cb2.button("⚔️ 找戰神"): set_preset('elite')
if cb3.button("👶 找萌新"): set_preset('newbie')
if cb4.button("🔄 重置"): set_preset('reset')
cq1, cq2, cq3, cq4 = st.columns([1.2, 1.2, 0.8, 0.8])
with cq1: st.caption("戰功"); st.selectbox("", ["大於 >=", "小於 <="], key="q_merit_op", label_visibility="collapsed"); st.number_input("", step=10000, key="q_merit_val", label_visibility="collapsed")
with cq2: st.caption("勢力"); st.selectbox("", ["大於 >=", "小於 <="], key="q_power_op", label_visibility="collapsed"); st.number_input("", step=5000, key="q_power_val", label_visibility="collapsed")
with cq3: st.caption("效率篩選"); st.selectbox("", ["大於 >=", "小於 <="], key="q_eff_op", label_visibility="collapsed"); st.number_input("", step=1.0, key="q_eff_val", label_visibility="collapsed")
with cq4: st.caption("Top N"); st.number_input("", step=10, key="q_rank", label_visibility="collapsed")
qdf = filt_df.copy()
if "大於" in st.session_state.q_merit_op: qdf = qdf[qdf['戰功總量'] >= st.session_state.q_merit_val]
else: qdf = qdf[qdf['戰功總量'] <= st.session_state.q_merit_val]
if "大於" in st.session_state.q_power_op: qdf = qdf[qdf['勢力值'] >= st.session_state.q_power_val]
else: qdf = qdf[qdf['勢力值'] <= st.session_state.q_power_val]
if "大於" in st.session_state.q_eff_op: qdf = qdf[qdf['戰功效率'] >= st.session_state.q_eff_val]
else: qdf = qdf[qdf['戰功效率'] <= st.session_state.q_eff_val]
qdf = qdf[qdf['貢獻排行'] <= st.session_state.q_rank].sort_values('貢獻排行')
st.markdown(f"<div style='margin-top:10px;color:#AAA'>🎯 鎖定 {len(qdf)} 目標</div>", unsafe_allow_html=True)
qdd = qdf[['成員', '分組', '貢獻排行', '戰功總量', '勢力值', '戰功效率']].copy()
sq = qdd.style.format({"戰功總量": "{:,}", "勢力值": "{:,}", "戰功效率": "{:.2f}"}).apply(style_eff_col, subset=["戰功效率"])
eq = st.dataframe(sq, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="t4")
if len(eq.selection['rows']): tm = qdf.iloc[eq.selection['rows'][0]]['成員']
st.markdown("</div>", unsafe_allow_html=True)

# 4. 戰區
st.markdown("<div class='dashboard-card card-gold'>", unsafe_allow_html=True)
st.markdown("### 🗺️ 戰區部署監控")
cr1, cr2 = st.columns([1, 2])
ar = list(filt_df['所屬勢力'].unique())
with cr1: st.caption("📍 前線區域"); fl = st.multiselect("", ar, key="frontline_select", default=st.session_state.frontline_regions, on_change=update_frontline_cookie, label_visibility="collapsed")
with cr2:
    rc = filt_df['所屬勢力'].value_counts().reset_index(); rc.columns = ['地區', '人數']
    rc['狀態'] = rc['地區'].apply(lambda x: '🔥 前線' if x in fl else '💤 後方')
    chart = alt.Chart(rc).mark_bar().encode(x=alt.X('人數', title=None), y=alt.Y('地區', sort='-x', title=None), color=alt.Color('狀態', scale=alt.Scale(domain=['🔥 前線', '💤 後方'], range=['#D4AF37', '#444']), legend=None), tooltip=['地區', '人數']).properties(height=150)
    st.altair_chart(chart, use_container_width=True)
if fl:
    infl = filt_df[filt_df['所屬勢力'].isin(fl)]; nofl = filt_df[~filt_df['所屬勢力'].isin(fl)]; r = len(infl)/len(filt_df)*100
    cz1, cz2 = st.columns(2); cz1.metric("前線", f"{len(infl)}", delta=f"{r:.1f}%"); cz2.metric("滯留", f"{len(nofl)}", delta="-未到", delta_color="inverse")
    with st.expander(f"📋 滯留名單 ({len(nofl)}人)"): nd = nofl[['成員', '分組', '所屬勢力', '勢力值']].copy(); nd['勢力值'] = nd['勢力值'].apply(lambda x: f"{int(x):,}"); st.dataframe(nd, use_container_width=True, hide_index=True)
else: st.info("請勾選前線")
st.markdown("</div>", unsafe_allow_html=True)

if tm and tm != st.session_state.last_selected_member:
    st.session_state.last_selected_member = tm
    show_member_popup(tm, raw_df, G_MAX_MERIT, G_MAX_POWER, G_MIN_POWER)