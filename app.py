import streamlit as st
import pandas as pd
import altair as alt
import re
import os
import extra_streamlit_components as stx

# --- 1. 頁面配置與 CSS ---
st.set_page_config(page_title="戰略指揮中心", layout="wide", page_icon="🏯")

st.markdown("""
<style>
    /* 全域背景 */
    .stApp { background-color: #121212; color: #E0E0E0; }
    .block-container { padding: 1rem 1.5rem; }
    div[data-testid="column"] { gap: 0.5rem; }
    
    /* 標題 */
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 400; margin: 0 0 0.5rem 0 !important; letter-spacing: 1px; }
    
    /* 側邊欄 */
    section[data-testid="stSidebar"] { background-color: #0d0d0d; border-right: 1px solid #333; }
    
    /* KPI */
    div[data-testid="stMetric"] { background-color: #1E1E1E; border: 1px solid #333; padding: 10px; border-radius: 4px; }
    div[data-testid="stMetricLabel"] { color: #888 !important; font-size: 0.8rem; }
    div[data-testid="stMetricValue"] { color: #FFF !important; font-size: 1.3rem; }

    /* 卡片 */
    .dashboard-card { background-color: #1E1E1E; border: 1px solid #333; border-radius: 6px; padding: 15px; margin-bottom: 15px; }
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
    
    /* 彈窗 (Dialog Box) */
    div[role="dialog"] { 
        background-color: #000 !important; 
        border: 1px solid #555; 
        width: 72vw !important; 
        max-width: 1200px !important;
    }
    
    /* --- [王牌檔案] 表格佈局樣式 --- */
    .ace-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }
    .ace-table td {
        padding: 5px 0;
        vertical-align: bottom; /* 底部對齊 */
        border-bottom: 1px solid #333;
    }
    .ace-label-col {
        width: 1%; /* 讓欄位盡可能窄 */
        white-space: nowrap;
        font-size: 1.1rem;
        color: #888;
        text-transform: uppercase;
        padding-right: 15px !important;
        font-weight: bold;
        letter-spacing: 1px;
    }
    .ace-value-col {
        font-family: 'Arial Black', 'Helvetica Black', sans-serif;
        font-size: 48px; /* 安全尺寸 */
        font-weight: 900;
        line-height: 1;
        color: #E0E0E0;
        text-align: left;
    }
    
    .val-elite { color: #FFE100; text-shadow: 0 0 20px rgba(255, 225, 0, 0.5); }
    .val-front { color: #00FF55; text-shadow: 0 0 15px rgba(0, 255, 85, 0.4); }
    
    @media (min-width: 1400px) {
        .ace-value-col { font-size: 64px; }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Cookie 管理器與資料庫核心 ---
cookie_manager = stx.CookieManager()

DATA_FOLDER = "盟戰資料庫"
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

def save_uploaded_file(uploaded_file):
    try:
        with open(os.path.join(DATA_FOLDER, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except:
        return False

def load_data_from_folder():
    all_data = []
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    if not files:
        return pd.DataFrame()
    for filename in files:
        try:
            df = pd.read_csv(os.path.join(DATA_FOLDER, filename))
            df.columns = df.columns.str.strip()
            match = re.search(r'(\d{4})年(\d{2})月(\d{2})日(\d{2})[时|時](\d{2})分(\d{2})秒', filename)
            record_date = pd.to_datetime(f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)}:{match.group(5)}:{match.group(6)}") if match else pd.Timestamp.now()
            df['紀錄時間'] = record_date
            all_data.append(df)
        except:
            pass
    if not all_data:
        return pd.DataFrame()
    full_df = pd.concat(all_data, ignore_index=True).sort_values('紀錄時間')
    full_df['勢力值'] = full_df['勢力值'].replace(0, 1)
    full_df['戰功效率'] = (full_df['戰功總量'] / full_df['勢力值']).round(2)
    return full_df

# --- 3. 狀態與 Cookie 同步 ---

if 'last_selected_member' not in st.session_state:
    st.session_state.last_selected_member = None

cookies_font_size = cookie_manager.get(cookie="font_size")
cookies_frontline = cookie_manager.get(cookie="frontline_regions")

if 'font_size' not in st.session_state:
    st.session_state.font_size = int(cookies_font_size) if cookies_font_size else 18

if 'frontline_regions' not in st.session_state:
    if cookies_frontline:
        try:
            st.session_state.frontline_regions = cookies_frontline.split(',')
        except:
            st.session_state.frontline_regions = []
    else:
        st.session_state.frontline_regions = []

default_vals = {'q_merit_op': '大於 >=', 'q_merit_val': 0, 'q_power_op': '大於 >=', 'q_power_val': 0, 'q_eff_max': 999.0, 'q_rank': 300}
for k, v in default_vals.items(): 
    if k not in st.session_state: st.session_state[k] = v

def set_preset(ptype):
    updates = {}
    if ptype == 'slave': updates = {'q_merit_op': '小於 <=', 'q_merit_val': 10000, 'q_power_op': '大於 >=', 'q_power_val': 25000, 'q_eff_max': 50.0}
    elif ptype == 'elite': updates = {'q_merit_op': '大於 >=', 'q_merit_val': 100000, 'q_power_op': '大於 >=', 'q_power_val': 0, 'q_eff_max': 999.0}
    elif ptype == 'newbie': updates = {'q_merit_op': '小於 <=', 'q_merit_val': 5000, 'q_power_val': 10000, 'q_power_op': '小於 <=', 'q_eff_max': 999.0}
    elif ptype == 'reset': updates = default_vals
    for k, v in updates.items(): st.session_state[k] = v

def update_font_cookie():
    cookie_manager.set("font_size", st.session_state.font_size_slider)
    st.session_state.font_size = st.session_state.font_size_slider

def update_frontline_cookie():
    regions_str = ",".join(st.session_state.frontline_select)
    cookie_manager.set("frontline_regions", regions_str)
    st.session_state.frontline_regions = st.session_state.frontline_select

@st.dialog("王牌戰略檔案", width="large")
def show_member_popup(member_name, raw_df):
    # 1. 篩選該成員資料
    member_data = raw_df[raw_df['成員'] == member_name].copy()
    
    # 2. [核心修正] 每日快照邏輯 (Daily Snapshot)
    # 取出日期部分
    member_data['date_only'] = member_data['紀錄時間'].dt.date
    # 針對每一天，只保留時間最晚的那一筆 (Last Record of the Day)
    history = member_data.sort_values('紀錄時間').groupby('date_only').tail(1)
    
    curr = history.iloc[-1]
    latest_df = raw_df[raw_df['紀錄時間'] == raw_df['紀錄時間'].max()]
    rank = curr['貢獻排行']
    total = len(latest_df)
    
    # 3. 計算「日均成長」 (Velocity)
    # 因為已經是每日一筆，diff() 就直接代表日與日之間的變化
    # 但為了更精確（防止有漏掉幾天沒傳數據的情況），我們還是除以天數差
    history['time_diff_days'] = history['紀錄時間'].diff().dt.total_seconds() / 86400
    history['merit_diff'] = history['戰功總量'].diff()
    history['power_diff'] = history['勢力值'].diff()
    
    # 計算速率 (Velocity)
    history['daily_merit_growth'] = (history['merit_diff'] / history['time_diff_days']).fillna(0)
    history['daily_power_growth'] = (history['power_diff'] / history['time_diff_days']).fillna(0)
    
    # 4. UI 呈現
    val_class = ""
    if rank <= total * 0.1: val_class = "color: #FFE100; text-shadow: 0 0 20px rgba(255, 225, 0, 0.6);"
    elif rank <= total * 0.3: val_class = "color: #00FF55; text-shadow: 0 0 15px rgba(0, 255, 85, 0.5);"
    else: val_class = "color: #E0E0E0;"
        
    col_left, col_right = st.columns([1.2, 2.8], gap="large")
    
    with col_left:
        st.markdown(f"## {member_name}")
        st.caption(f"📍 {curr['所屬勢力']} | 🏷️ {curr['分組']}")
        st.markdown("---")
        
        html_stats = f"""
        <table class="ace-table">
            <tr>
                <td class="ace-label-col">⚔️ 戰功</td>
                <td class="ace-value-col {val_class}">{int(curr['戰功總量']):,}</td>
            </tr>
            <tr>
                <td class="ace-label-col">🏰 勢力</td>
                <td class="ace-value-col">{int(curr['勢力值']):,}</td>
            </tr>
            <tr>
                <td class="ace-label-col">⚡ 效率</td>
                <td class="ace-value-col">{curr['戰功效率']}</td>
            </tr>
            <tr>
                <td class="ace-label-col">🏅 排名</td>
                <td class="ace-value-col">#{curr['貢獻排行']}</td>
            </tr>
        </table>
        """
        st.markdown(html_stats, unsafe_allow_html=True)
        
    with col_right:
        st.markdown("##### 🚀 戰力加速度 (每日最新快照)")
        
        base = alt.Chart(history).encode(x=alt.X('紀錄時間', axis=alt.Axis(format='%m/%d', title=None)))
        
        area = base.mark_area(
            interpolate='basis', 
            line={'color':'#FFE100'}, 
            color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='rgba(255, 225, 0, 0.5)', offset=0), alt.GradientStop(color='rgba(255, 225, 0, 0.1)', offset=1)], x1=1, x2=1, y1=1, y2=0)
        ).encode(
            y=alt.Y('daily_merit_growth', title='日均戰功 (活躍度)'),
            tooltip=['紀錄時間', alt.Tooltip('daily_merit_growth', format=',.0f', title='日增戰功'), '戰功總量']
        )
        
        line = base.mark_line(
            interpolate='basis', 
            color='#00FF55', 
            strokeWidth=3
        ).encode(
            y=alt.Y('daily_power_growth', title='日均勢力變化'),
            tooltip=['紀錄時間', alt.Tooltip('daily_power_growth', format=',.0f', title='日增勢力'), '勢力值']
        )
        
        chart = (area + line).resolve_scale(y='independent').properties(
            height=600,
            padding={"left": 20, "right": 20, "top": 10, "bottom": 10}
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)

# --- 4. 主程式 ---
st.sidebar.title("🎛️ 指揮台")
up = st.sidebar.file_uploader("📥 上傳", type=['csv'], accept_multiple_files=True)
if up: 
    if sum([save_uploaded_file(f) for f in up]):
        st.sidebar.success("已存檔")

raw_df = load_data_from_folder()
if raw_df.empty:
    st.warning("無資料")
    st.stop()

latest_df = raw_df[raw_df['紀錄時間'] == raw_df['紀錄時間'].max()].copy()
st.sidebar.caption(f"📅 {latest_df['紀錄時間'].iloc[0].strftime('%m/%d %H:%M')}")

grps = list(latest_df['分組'].unique())
sel_grps = st.sidebar.multiselect("分組", grps, default=grps)
filt_df = latest_df[latest_df['分組'].isin(sel_grps)]

st.sidebar.markdown("---")
kw = st.sidebar.text_input("搜索", placeholder="關鍵字...")
if kw:
    m = filt_df[filt_df['成員'].str.contains(kw, na=False)]['成員'].unique()
    if len(m) > 0:
        t = st.sidebar.selectbox("結果", m)
        if st.sidebar.button("調用"):
            show_member_popup(t, raw_df)
    else:
        st.sidebar.warning("無結果")

st.markdown("<h2 style='color:#DDD;'>🏯 戰略指揮中心</h2>", unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)
k1.metric("總戰功", f"{int(filt_df['戰功總量'].sum()):,}")
k2.metric("總勢力", f"{int(filt_df['勢力值'].sum()):,}")
k3.metric("活躍", f"{len(filt_df):,}")
k4.metric("效率", f"{filt_df['戰功效率'].mean():.2f}")

# 1. 集團軍
st.markdown("<div class='dashboard-card card-red'>", unsafe_allow_html=True)
c1, c2 = st.columns([4, 1])
with c1: st.markdown("### 🏳️ 集團軍情報")
with c2: fs = st.slider("字體", 14, 30, value=st.session_state.font_size, key="font_size_slider", on_change=update_font_cookie, label_visibility="collapsed")

gs = filt_df.groupby('分組').agg(n=('成員','count'), wm=('戰功總量','sum'), awm=('戰功總量','mean'), p=('勢力值','sum'), ap=('勢力值','mean')).reset_index().sort_values('wm', ascending=False)
html_content = f"<style>.clean-table td, .clean-table th {{ font-size: {fs}px; }}</style><table class='clean-table'><thead><tr><th>分組</th><th>人數</th><th>總戰功</th><th>平均戰功</th><th>總勢力</th><th>平均勢力</th></tr></thead><tbody>"
for _, r in gs.iterrows():
    html_content += f"<tr><td>{r['分組']}</td><td>{r['n']}</td><td>{int(r['wm']):,}</td><td>{int(r['awm']):,}</td><td>{int(r['p']):,}</td><td>{int(r['ap']):,}</td></tr>"
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
with cl1:
    st.caption("🔥 十大戰功")
    d1 = filt_df.nlargest(nr, '戰功總量')[['成員','分組','戰功總量']]
    e1 = st.dataframe(d1, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="t1", column_config={"戰功總量": st.column_config.ProgressColumn(" ", format="%d", max_value=int(latest_df['戰功總量'].max()))})
    if len(e1.selection['rows']): tm = d1.iloc[e1.selection['rows'][0]]['成員']
with cl2:
    st.caption("⚡ 十大效率")
    d2 = filt_df[filt_df['勢力值']>10000].nlargest(nr, '戰功效率')[['成員','分組','戰功效率']]
    e2 = st.dataframe(d2, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="t2", column_config={"戰功效率": st.column_config.NumberColumn(" ", format="%.2f")})
    if len(e2.selection['rows']): tm = d2.iloc[e2.selection['rows'][0]]['成員']
with cl3:
    st.caption("🐢 遲緩名單")
    avg = latest_df['勢力值'].mean()
    d3 = filt_df[filt_df['勢力值']>avg].nsmallest(nr, '戰功效率')[['成員','勢力值','戰功效率']]
    d3d = d3.copy(); d3d['勢力值'] = d3d['勢力值'].apply(lambda x: f"{int(x):,}")
    e3 = st.dataframe(d3d, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="t3")
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
with cq3: st.caption("效率上限"); st.number_input("", step=10.0, key="q_eff_max", label_visibility="collapsed")
with cq4: st.caption("Top N"); st.number_input("", step=10, key="q_rank", label_visibility="collapsed")
qdf = filt_df.copy()
if "大於" in st.session_state.q_merit_op: qdf = qdf[qdf['戰功總量'] >= st.session_state.q_merit_val]
else: qdf = qdf[qdf['戰功總量'] <= st.session_state.q_merit_val]
if "大於" in st.session_state.q_power_op: qdf = qdf[qdf['勢力值'] >= st.session_state.q_power_val]
else: qdf = qdf[qdf['勢力值'] <= st.session_state.q_power_val]
qdf = qdf[(qdf['戰功效率'] <= st.session_state.q_eff_max) & (qdf['貢獻排行'] <= st.session_state.q_rank)].sort_values('貢獻排行')
st.markdown(f"<div style='margin-top:10px;color:#AAA'>🎯 鎖定 {len(qdf)} 目標</div>", unsafe_allow_html=True)
qdd = qdf[['成員', '分組', '貢獻排行', '戰功總量', '勢力值', '戰功效率']].copy()
qdd['戰功總量'] = qdd['戰功總量'].apply(lambda x: f"{int(x):,}")
qdd['勢力值'] = qdd['勢力值'].apply(lambda x: f"{int(x):,}")
eq = st.dataframe(qdd, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="t4")
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
    show_member_popup(tm, raw_df)