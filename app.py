import streamlit as st
import pandas as pd
import extra_streamlit_components as stx
import datetime
import time

# --- Custom Modules ---
import utils_data as ud
import utils_style as us
import utils_chart as uc

# --- 1. Page Initialization ---
st.set_page_config(page_title="戰略指揮中心", layout="wide", page_icon="🏯")
us.apply_css()

# --- 2. State & Cookie Management ---
cookie_manager = stx.CookieManager()

# Initialize Session State
if 'last_selected_member' not in st.session_state:
    st.session_state.last_selected_member = None

DEFAULT_FILTERS = {
    'q_merit_op': '大於 >=', 'q_merit_val': 0,
    'q_power_op': '大於 >=', 'q_power_val': 0,
    'q_eff_op': '大於 >=', 'q_eff_val': 0.0,
    'q_rank': 300
}

for key, value in DEFAULT_FILTERS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Cookie Reading & Setting
cookies_font_size = cookie_manager.get(cookie="font_size")
cookies_frontline = cookie_manager.get(cookie="frontline_regions")

if 'font_size' not in st.session_state:
    st.session_state.font_size = int(cookies_font_size) if cookies_font_size else 18
if 'frontline_regions' not in st.session_state:
    st.session_state.frontline_regions = cookies_frontline.split(',') if cookies_frontline else []

def update_font_cookie():
    cookie_manager.set("font_size", st.session_state.font_size_slider)
    st.session_state.font_size = st.session_state.font_size_slider

def update_frontline_cookie():
    cookie_manager.set("frontline_regions", ",".join(st.session_state.frontline_select))
    st.session_state.frontline_regions = st.session_state.frontline_select

# --- 3. Authentication ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    
    auth_token = cookie_manager.get("auth_token")
    if auth_token == "valid":
        st.session_state["password_correct"] = True
        return True
    
    if "password" not in st.secrets:
        # Development mode bypass or warning
        # st.warning("⚠️ 未設定密碼 (st.secrets)，已繞過驗證。")
        return True

    placeholder = st.empty()
    with placeholder.container():
        st.markdown("### 🔒 指揮官權限驗證")
        pwd = st.text_input("請輸入密碼", type="password", key="login_pwd")
        if pwd:
            if pwd == st.secrets["password"]:
                st.session_state["password_correct"] = True
                expires = datetime.datetime.now() + datetime.timedelta(hours=1)
                cookie_manager.set("auth_token", "valid", expires_at=expires)
                time.sleep(1)
                placeholder.empty()
                st.rerun()
            else:
                st.error("⛔ 密碼錯誤")
                st.stop()
        else:
            st.stop()

check_password()

# --- 4. Helper Functions (Interaction) ---
def set_preset(preset_type):
    config = ud.RADAR_CONFIG.get(preset_type, {})
    updates = {
        'q_merit_op': config.get('merit_op', '大於 >='),
        'q_merit_val': config.get('merit_val', 0),
        'q_power_op': config.get('power_op', '大於 >='),
        'q_power_val': config.get('power_val', 0),
        'q_eff_op': config.get('eff_op', '大於 >='),
        'q_eff_val': config.get('eff_val', 0.0)
    }
    if preset_type == 'reset':
        updates['q_rank'] = 300
        
    for key, value in updates.items():
        st.session_state[key] = value

@st.dialog("王牌戰略檔案", width="large")
def show_member_popup(member_name, raw_df, g_max_m, g_max_p, g_min_p, merit_threshold):
    # Calculate individual history
    member_data = raw_df[raw_df['成員'] == member_name].copy()
    member_data['date_only'] = member_data['紀錄時間'].dt.date
    history = member_data.sort_values('紀錄時間').groupby('date_only').tail(1)
    
    # Calculate differences
    history['time_diff'] = history['紀錄時間'].diff().dt.total_seconds() / 86400
    history['merit_diff'] = history['戰功總量'].diff()
    history['power_diff'] = history['勢力值'].diff()
    history['daily_merit_growth'] = (history['merit_diff'] / history['time_diff']).fillna(0)
    history['daily_power_growth'] = (history['power_diff'] / history['time_diff']).fillna(0)
    
    current_stats = history.iloc[-1]
    
    # Styles
    s_merit = us.get_merit_style(current_stats['戰功總量'], merit_threshold)
    s_power = us.get_power_style(current_stats['勢力值'])
    s_eff = us.get_eff_style(current_stats['戰功效率'])
    
    # Add text shadow for high tier
    if "00FF55" in s_merit: s_merit += "; text-shadow: 0 0 20px rgba(0, 255, 85, 0.6);"
    if "00FF55" in s_eff: s_eff += "; text-shadow: 0 0 15px rgba(0, 255, 85, 0.3);"

    col_left, col_right = st.columns([1.2, 2.8], gap="large")
    with col_left:
        st.markdown(f"## {member_name}")
        st.caption(f"📍 {current_stats['所屬勢力']} | 🏷️ {current_stats['分組']}")
        st.markdown("---")
        st.markdown(us.generate_ace_table_html(current_stats, s_merit, s_power, s_eff), unsafe_allow_html=True)
        
    with col_right:
        st.markdown("##### 🚀 戰力加速度 (日均成長速率)")
        st.altair_chart(uc.get_ace_profile_chart(history, g_max_m, g_max_p, g_min_p), use_container_width=True)

# --- 5. Main Application ---
st.sidebar.title("🎛️ 指揮台")
uploaded_files = st.sidebar.file_uploader("📥 上傳", type=['csv'], accept_multiple_files=True)
if uploaded_files:
    if sum([ud.save_uploaded_file(f) for f in uploaded_files]):
        st.sidebar.success("已存檔")

raw_df = ud.load_data_from_folder()
if raw_df.empty:
    st.warning("無資料 - 請上傳 CSV 至 '盟戰資料庫'")
    st.stop()

latest_df = raw_df[raw_df['紀錄時間'] == raw_df['紀錄時間'].max()].copy()
latest_time_str = latest_df['紀錄時間'].iloc[0].strftime('%Y/%m/%d %H:%M')
st.sidebar.caption(f"📅 {latest_time_str}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"<div style='text-align: center; color: #666; font-size: 0.8rem;'>戰略指揮中心 v57.0 (Refactor)<br>Updated: {latest_time_str}</div>", unsafe_allow_html=True)

all_groups = list(latest_df['分組'].unique())
selected_groups = st.sidebar.multiselect("分組", all_groups, default=all_groups)
filtered_df = latest_df[latest_df['分組'].isin(selected_groups)]

MERIT_THRESHOLD_95 = filtered_df['戰功總量'].quantile(0.95)
G_MAX_M, G_MAX_P, G_MIN_P = ud.get_individual_global_max(raw_df)

st.sidebar.markdown("---")
search_keyword = st.sidebar.text_input("搜索", placeholder="關鍵字...")
target_member = None

if search_keyword:
    matched_members = filtered_df[filtered_df['成員'].str.contains(search_keyword, na=False)]['成員'].unique()
    if len(matched_members) > 0:
        selected_member = st.sidebar.selectbox("結果", matched_members)
        if st.sidebar.button("調用"):
            show_member_popup(selected_member, raw_df, G_MAX_M, G_MAX_P, G_MIN_P, MERIT_THRESHOLD_95)
    else:
        st.sidebar.warning("無結果")

st.markdown("<h2 style='color:#DDD;'>🏯 戰略指揮中心</h2>", unsafe_allow_html=True)

# --- KPI Section ---
avg_efficiency = filtered_df['戰功效率'].mean()
eff_class = us.get_eff_class(avg_efficiency)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>總戰功</div><div class='kpi-value'>{us.format_k(filtered_df['戰功總量'].sum())}</div></div>", unsafe_allow_html=True)
with kpi2: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>總勢力</div><div class='kpi-value'>{us.format_k(filtered_df['勢力值'].sum())}</div></div>", unsafe_allow_html=True)
with kpi3: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>活躍人數</div><div class='kpi-value'>{len(filtered_df):,}</div></div>", unsafe_allow_html=True)
with kpi4: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>平均效率</div><div class='kpi-value {eff_class}'>{avg_efficiency:.2f}</div></div>", unsafe_allow_html=True)

st.markdown(f"""<div class="version-tag">v57.0 | {latest_time_str}</div>""", unsafe_allow_html=True)

# --- Strategic Velocity Section ---
velocity_all_data = ud.calculate_daily_velocity(raw_df, group_col='分組')
grp_max_m = velocity_all_data['daily_merit_growth'].max()
grp_max_p = velocity_all_data['daily_power_growth'].max()
grp_min_p = velocity_all_data['daily_power_growth'].min()

avg_velocity_data = ud.calculate_daily_velocity(raw_df)
av_max_m = avg_velocity_data['daily_merit_growth'].max()
av_max_p = avg_velocity_data['daily_power_growth'].max()
av_min_p = avg_velocity_data['daily_power_growth'].min()

st.markdown("<div class='dashboard-card card-cyan'>", unsafe_allow_html=True)
st.markdown("### 📈 戰略動能")
chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.caption("🌍 全盟")
    st.altair_chart(uc.get_dual_axis_growth_chart(avg_velocity_data, av_max_m, av_max_p, av_min_p).configure_legend(orient='top').interactive(), use_container_width=True)
with chart_col2:
    st.caption("🚩 分組")
    target_group = st.selectbox("分組", all_groups, key="target_group_select", label_visibility="collapsed")
    group_velocity = velocity_all_data[velocity_all_data['分組'] == target_group]
    st.altair_chart(uc.get_dual_axis_growth_chart(group_velocity, grp_max_m, grp_max_p, grp_min_p).configure_legend(orient='top').interactive(), use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- Group Intelligence Section ---
st.markdown("<div class='dashboard-card card-red'>", unsafe_allow_html=True)
header_col1, header_col2 = st.columns([4, 1])
with header_col1: st.markdown("### 🏳️ 集團軍情報")
with header_col2: font_size = st.slider("字體", 14, 30, value=st.session_state.font_size, key="font_size_slider", on_change=update_font_cookie, label_visibility="collapsed")

group_stats = filtered_df.groupby('分組').agg(
    n=('成員','count'), 
    wm=('戰功總量','sum'), 
    awm=('戰功總量','mean'), 
    p=('勢力值','sum'), 
    ap=('勢力值','mean')
).reset_index().sort_values('wm', ascending=False)

html_content = f"<style>.clean-table td, .clean-table th {{ font-size: {font_size}px; }}</style><table class='clean-table'><thead><tr><th>分組</th><th>人數</th><th>總戰功</th><th>平均戰功</th><th>總勢力</th><th>平均勢力</th></tr></thead><tbody>"
for _, row in group_stats.iterrows():
    html_content += f"<tr><td>{row['分組']}</td><td>{row['n']}</td><td>{us.format_k(row['wm'])}</td><td>{us.format_k(row['awm'])}</td><td>{us.format_k(row['p'])}</td><td>{us.format_k(row['ap'])}</td></tr>"
html_content += "</tbody></table>"
st.markdown(html_content, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- Key Personnel Section ---
st.markdown("<div class='dashboard-card card-blue'>", unsafe_allow_html=True)
header_col1, header_col2 = st.columns([4, 1])
with header_col1: st.markdown("### 🏆 重點人員")
with header_col2: num_rows = st.number_input("行數", 5, 50, 10, step=5, label_visibility="collapsed")

col1, col2 = st.columns(2)

with col1:
    st.caption("🔥 十大戰功")
    top_merit = filtered_df.nlargest(num_rows, '戰功總量')[['成員','分組','戰功總量']]
    if not top_merit.empty:
        styled_merit = us.style_df_full(top_merit, MERIT_THRESHOLD_95)
        event_merit = st.dataframe(styled_merit, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="table_merit")
        if len(event_merit.selection['rows']): target_member = top_merit.iloc[event_merit.selection['rows'][0]]['成員']

with col2:
    st.caption("⚡ 十大效率")
    top_efficiency = filtered_df[filtered_df['勢力值']>10000].nlargest(num_rows, '戰功效率')[['成員','分組','戰功效率']]
    if not top_efficiency.empty:
        styled_eff = top_efficiency.style.format({"戰功效率": "{:.2f}"}).map(us.get_eff_style, subset=pd.IndexSlice[:, ['戰功效率']])
        event_eff = st.dataframe(styled_eff, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="table_eff")
        if len(event_eff.selection['rows']): target_member = top_efficiency.iloc[event_eff.selection['rows'][0]]['成員']

st.markdown("</div>", unsafe_allow_html=True)

# --- Tactical Radar Section ---
st.markdown("<div class='dashboard-card card-purple'>", unsafe_allow_html=True)
st.markdown("### 🛰️ 戰術雷達")

# Preset Buttons
preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
with preset_col1:
    if st.button(ud.RADAR_CONFIG['slave']['desc'], use_container_width=True): set_preset('slave')
with preset_col2:
    if st.button(ud.RADAR_CONFIG['newbie']['desc'], use_container_width=True): set_preset('newbie')
with preset_col3:
    if st.button(ud.RADAR_CONFIG['elite']['desc'], use_container_width=True): set_preset('elite')
with preset_col4:
    if st.button(ud.RADAR_CONFIG['reset']['desc'], use_container_width=True): set_preset('reset')

st.markdown("---")

# Filter Controls
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.2, 1.2, 0.8, 0.8])
with filter_col1: 
    st.caption("戰功")
    st.selectbox("", ["大於 >=", "小於 <="], key="q_merit_op", label_visibility="collapsed")
    st.number_input("", step=10000, key="q_merit_val", label_visibility="collapsed")
with filter_col2: 
    st.caption("勢力")
    st.selectbox("", ["大於 >=", "小於 <="], key="q_power_op", label_visibility="collapsed")
    st.number_input("", step=5000, key="q_power_val", label_visibility="collapsed")
with filter_col3: 
    st.caption("效率")
    st.selectbox("", ["大於 >=", "小於 <="], key="q_eff_op", label_visibility="collapsed")
    st.number_input("", step=1.0, key="q_eff_val", label_visibility="collapsed")
with filter_col4: 
    st.caption("Top N")
    st.number_input("", step=10, key="q_rank", label_visibility="collapsed")

# Apply Filters
query_df = filtered_df.copy()

if "大於" in st.session_state.q_merit_op:
    query_df = query_df[query_df['戰功總量'] >= st.session_state.q_merit_val]
else:
    query_df = query_df[query_df['戰功總量'] <= st.session_state.q_merit_val]

if "大於" in st.session_state.q_power_op:
    query_df = query_df[query_df['勢力值'] >= st.session_state.q_power_val]
else:
    query_df = query_df[query_df['勢力值'] <= st.session_state.q_power_val]

if "大於" in st.session_state.q_eff_op:
    query_df = query_df[query_df['戰功效率'] >= st.session_state.q_eff_val]
else:
    query_df = query_df[query_df['戰功效率'] <= st.session_state.q_eff_val]

query_df = query_df[query_df['貢獻排行'] <= st.session_state.q_rank].sort_values('貢獻排行')

st.markdown(f"<div style='margin-top:10px;color:#AAA'>🎯 鎖定 {len(query_df)} 目標</div>", unsafe_allow_html=True)
if not query_df.empty:
    display_cols = ['成員', '分組', '貢獻排行', '戰功總量', '勢力值', '戰功效率']
    query_display_df = query_df[display_cols].copy()
    event_query = st.dataframe(us.style_df_full(query_display_df, MERIT_THRESHOLD_95), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="table_query")
    if len(event_query.selection['rows']): target_member = query_df.iloc[event_query.selection['rows'][0]]['成員']
st.markdown("</div>", unsafe_allow_html=True)

# --- Warzone Monitoring Section ---
st.markdown("<div class='dashboard-card card-gold'>", unsafe_allow_html=True)
st.markdown("### 🗺️ 戰區監控")
war_col1, war_col2 = st.columns([1, 2])
all_regions = list(filtered_df['所屬勢力'].unique())

with war_col1: 
    st.caption("📍 前線")
    frontline_regions = st.multiselect("", all_regions, key="frontline_select", default=st.session_state.frontline_regions, on_change=update_frontline_cookie, label_visibility="collapsed")

with war_col2:
    region_counts = filtered_df['所屬勢力'].value_counts().reset_index()
    region_counts.columns = ['地區', '人數']
    region_counts['狀態'] = region_counts['地區'].apply(lambda x: '🔥 前線' if x in frontline_regions else '💤 後方')
    st.altair_chart(uc.get_warzone_bar_chart(region_counts), use_container_width=True)
    
if frontline_regions:
    in_frontline = filtered_df[filtered_df['所屬勢力'].isin(frontline_regions)]
    not_in_frontline = filtered_df[~filtered_df['所屬勢力'].isin(frontline_regions)]
    participation_rate = len(in_frontline) / len(filtered_df) * 100
    
    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("前線", f"{len(in_frontline)}", delta=f"{participation_rate:.1f}%")
    metric_col2.metric("滯留", f"{len(not_in_frontline)}", delta="-未到", delta_color="inverse")
    
    with st.expander(f"📋 滯留名單 ({len(not_in_frontline)}人)"): 
        slacker_data = not_in_frontline[['成員', '分組', '所屬勢力', '勢力值']].copy()
        if not slacker_data.empty:
            st.dataframe(slacker_data.style.format({"勢力值": us.format_k}).map(us.get_power_style, subset=pd.IndexSlice[:, ['勢力值']]), use_container_width=True, hide_index=True)
else:
    st.info("請勾選前線")
st.markdown("</div>", unsafe_allow_html=True)

# --- Final Popup Trigger ---
if target_member and target_member != st.session_state.last_selected_member:
    st.session_state.last_selected_member = target_member
    show_member_popup(target_member, raw_df, G_MAX_M, G_MAX_P, G_MIN_P, MERIT_THRESHOLD_95)