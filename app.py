import streamlit as st
import pandas as pd
import extra_streamlit_components as stx
import datetime
import time

# --- 引入自訂模組 ---
import utils_data as ud
import utils_style as us
import utils_chart as uc

# --- 1. 頁面初始化 ---
st.set_page_config(page_title="戰略指揮中心", layout="wide", page_icon="🏯")
us.apply_css() # 載入 CSS

# --- 2. 狀態與 Cookie ---
cookie_manager = stx.CookieManager()

# 初始化 Session State
if 'last_selected_member' not in st.session_state: st.session_state.last_selected_member = None
default_vals = {'q_merit_op': '大於 >=', 'q_merit_val': 0, 'q_power_op': '大於 >=', 'q_power_val': 0, 'q_eff_op': '大於 >=', 'q_eff_val': 0.0, 'q_rank': 300}
for k, v in default_vals.items(): 
    if k not in st.session_state: st.session_state[k] = v

# Cookie 讀取與設定
cookies_font_size = cookie_manager.get(cookie="font_size")
cookies_frontline = cookie_manager.get(cookie="frontline_regions")
if 'font_size' not in st.session_state: st.session_state.font_size = int(cookies_font_size) if cookies_font_size else 18
if 'frontline_regions' not in st.session_state: st.session_state.frontline_regions = cookies_frontline.split(',') if cookies_frontline else []

def update_font_cookie(): cookie_manager.set("font_size", st.session_state.font_size_slider); st.session_state.font_size = st.session_state.font_size_slider
def update_frontline_cookie(): cookie_manager.set("frontline_regions", ",".join(st.session_state.frontline_select)); st.session_state.frontline_regions = st.session_state.frontline_select

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
                time.sleep(1)
                placeholder.empty()
                st.rerun()
            else: st.error("⛔ 密碼錯誤"); st.stop()
        else: st.stop()

check_password()

# --- 4. 輔助函數 (互動相關) ---
def set_preset(ptype):
    cfg = ud.RADAR_CONFIG.get(ptype, {})
    updates = {
        'q_merit_op': cfg.get('merit_op', '大於 >='), 'q_merit_val': cfg.get('merit_val', 0),
        'q_power_op': cfg.get('power_op', '大於 >='), 'q_power_val': cfg.get('power_val', 0),
        'q_eff_op': cfg.get('eff_op', '大於 >='), 'q_eff_val': cfg.get('eff_val', 0.0)
    }
    if ptype == 'reset': updates['q_rank'] = 300
    for k, v in updates.items(): st.session_state[k] = v

@st.dialog("王牌戰略檔案", width="large")
def show_member_popup(member_name, raw_df, g_max_m, g_max_p, g_min_p, merit_threshold):
    # 臨時計算個人歷史數據 (可考慮移至 ud 但在此處計算較靈活)
    member_data = raw_df[raw_df['成員'] == member_name].copy()
    member_data['date_only'] = member_data['紀錄時間'].dt.date
    history = member_data.sort_values('紀錄時間').groupby('date_only').tail(1)
    
    # 局部計算差分
    history['time_diff'] = history['紀錄時間'].diff().dt.total_seconds() / 86400
    history['merit_diff'] = history['戰功總量'].diff()
    history['power_diff'] = history['勢力值'].diff()
    history['daily_merit_growth'] = (history['merit_diff'] / history['time_diff']).fillna(0)
    history['daily_power_growth'] = (history['power_diff'] / history['time_diff']).fillna(0)
    
    curr = history.iloc[-1]
    
    # 樣式
    s_merit = us.get_merit_style(curr['戰功總量'], merit_threshold)
    s_power = us.get_power_style(curr['勢力值'])
    s_eff = us.get_eff_style(curr['戰功效率'])
    if "00FF55" in s_merit: s_merit += "; text-shadow: 0 0 20px rgba(0, 255, 85, 0.6);"
    if "00FF55" in s_eff: s_eff += "; text-shadow: 0 0 15px rgba(0, 255, 85, 0.3);"

    col_left, col_right = st.columns([1.2, 2.8], gap="large")
    with col_left:
        st.markdown(f"## {member_name}")
        st.caption(f"📍 {curr['所屬勢力']} | 🏷️ {curr['分組']}")
        st.markdown("---")
        st.markdown(us.generate_ace_table_html(curr, s_merit, s_power, s_eff), unsafe_allow_html=True)
        
    with col_right:
        st.markdown("##### 🚀 戰力加速度 (日均成長速率)")
        st.altair_chart(uc.get_ace_profile_chart(history, g_max_m, g_max_p, g_min_p), use_container_width=True)

# --- 5. 主程式 ---
st.sidebar.title("🎛️ 指揮台")
up = st.sidebar.file_uploader("📥 上傳", type=['csv'], accept_multiple_files=True)
if up: 
    if sum([ud.save_uploaded_file(f) for f in up]): st.sidebar.success("已存檔")

raw_df = ud.load_data_from_folder()
if raw_df.empty: st.warning("無資料 - 請上傳 CSV 至 '盟戰資料庫'"); st.stop()

latest_df = raw_df[raw_df['紀錄時間'] == raw_df['紀錄時間'].max()].copy()
latest_time_str = latest_df['紀錄時間'].iloc[0].strftime('%Y/%m/%d %H:%M')
st.sidebar.caption(f"📅 {latest_time_str}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"<div style='text-align: center; color: #666; font-size: 0.8rem;'>戰略指揮中心 v57.0 (Refactor)<br>Updated: {latest_time_str}</div>", unsafe_allow_html=True)

grps = list(latest_df['分組'].unique())
sel_grps = st.sidebar.multiselect("分組", grps, default=grps)
filt_df = latest_df[latest_df['分組'].isin(sel_grps)]

MERIT_THRESHOLD_95 = filt_df['戰功總量'].quantile(0.95)
G_MAX_M, G_MAX_P, G_MIN_P = ud.get_individual_global_max(raw_df)

st.sidebar.markdown("---")
kw = st.sidebar.text_input("搜索", placeholder="關鍵字...")
tm = None # Target Member
if kw:
    m = filt_df[filt_df['成員'].str.contains(kw, na=False)]['成員'].unique()
    if len(m) > 0:
        t = st.sidebar.selectbox("結果", m)
        if st.sidebar.button("調用"):
            show_member_popup(t, raw_df, G_MAX_M, G_MAX_P, G_MIN_P, MERIT_THRESHOLD_95)
    else: st.sidebar.warning("無結果")

st.markdown("<h2 style='color:#DDD;'>🏯 戰略指揮中心</h2>", unsafe_allow_html=True)

# KPI
avg_eff = filt_df['戰功效率'].mean()
eff_class = us.get_eff_class(avg_eff)
k1, k2, k3, k4 = st.columns(4)
with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>總戰功</div><div class='kpi-value'>{us.format_k(filt_df['戰功總量'].sum())}</div></div>", unsafe_allow_html=True)
with k2: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>總勢力</div><div class='kpi-value'>{us.format_k(filt_df['勢力值'].sum())}</div></div>", unsafe_allow_html=True)
with k3: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>活躍人數</div><div class='kpi-value'>{len(filt_df):,}</div></div>", unsafe_allow_html=True)
with k4: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>平均效率</div><div class='kpi-value {eff_class}'>{avg_eff:.2f}</div></div>", unsafe_allow_html=True)

st.markdown(f"""<div class="version-tag">v57.0 | {latest_time_str}</div>""", unsafe_allow_html=True)

# 戰略動能
gv_all_data = ud.calculate_daily_velocity(raw_df, group_col='分組')
grp_max_m = gv_all_data['daily_merit_growth'].max()
grp_max_p = gv_all_data['daily_power_growth'].max()
grp_min_p = gv_all_data['daily_power_growth'].min()
av_data = ud.calculate_daily_velocity(raw_df)
av_max_m = av_data['daily_merit_growth'].max()
av_max_p = av_data['daily_power_growth'].max()
av_min_p = av_data['daily_power_growth'].min()

st.markdown("<div class='dashboard-card card-cyan'>", unsafe_allow_html=True)
st.markdown("### 📈 戰略動能")
ct1, ct2 = st.columns(2)
with ct1:
    st.caption("🌍 全盟")
    st.altair_chart(uc.get_dual_axis_growth_chart(av_data, av_max_m, av_max_p, av_min_p).configure_legend(orient='top').interactive(), use_container_width=True)
with ct2:
    st.caption("🚩 分組")
    tg = st.selectbox("分組", grps, key="tgs", label_visibility="collapsed")
    gv = gv_all_data[gv_all_data['分組'] == tg]
    st.altair_chart(uc.get_dual_axis_growth_chart(gv, grp_max_m, grp_max_p, grp_min_p).configure_legend(orient='top').interactive(), use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# 集團軍
st.markdown("<div class='dashboard-card card-red'>", unsafe_allow_html=True)
c1, c2 = st.columns([4, 1])
with c1: st.markdown("### 🏳️ 集團軍情報")
with c2: fs = st.slider("字體", 14, 30, value=st.session_state.font_size, key="font_size_slider", on_change=update_font_cookie, label_visibility="collapsed")
gs = filt_df.groupby('分組').agg(n=('成員','count'), wm=('戰功總量','sum'), awm=('戰功總量','mean'), p=('勢力值','sum'), ap=('勢力值','mean')).reset_index().sort_values('wm', ascending=False)
html_content = f"<style>.clean-table td, .clean-table th {{ font-size: {fs}px; }}</style><table class='clean-table'><thead><tr><th>分組</th><th>人數</th><th>總戰功</th><th>平均戰功</th><th>總勢力</th><th>平均勢力</th></tr></thead><tbody>"
for _, r in gs.iterrows():
    html_content += f"<tr><td>{r['分組']}</td><td>{r['n']}</td><td>{us.format_k(r['wm'])}</td><td>{us.format_k(r['awm'])}</td><td>{us.format_k(r['p'])}</td><td>{us.format_k(r['ap'])}</td></tr>"
html_content += "</tbody></table>"
st.markdown(html_content, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 重點名單
st.markdown("<div class='dashboard-card card-blue'>", unsafe_allow_html=True)
c1, c2 = st.columns([4, 1])
with c1: st.markdown("### 🏆 重點人員")
with c2: nr = st.number_input("行數", 5, 50, 10, step=5, label_visibility="collapsed")
cl1, cl2, cl3 = st.columns(3)

with cl1:
    st.caption("🔥 十大戰功")
    d1 = filt_df.nlargest(nr, '戰功總量')[['成員','分組','戰功總量']]
    if not d1.empty:
        s1 = us.style_df_full(d1, MERIT_THRESHOLD_95)
        e1 = st.dataframe(s1, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="t1")
        if len(e1.selection['rows']): tm = d1.iloc[e1.selection['rows'][0]]['成員']
with cl2:
    st.caption("⚡ 十大效率")
    d2 = filt_df[filt_df['勢力值']>10000].nlargest(nr, '戰功效率')[['成員','分組','戰功效率']]
    if not d2.empty:
        s2 = d2.style.format({"戰功效率": "{:.2f}"}).map(us.get_eff_style, subset=['戰功效率'])
        e2 = st.dataframe(s2, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="t2")
        if len(e2.selection['rows']): tm = d2.iloc[e2.selection['rows'][0]]['成員']
with cl3:
    st.caption("🐢 遲緩名單")
    avg = latest_df['勢力值'].mean()
    d3 = filt_df[filt_df['勢力值']>avg].nsmallest(nr, '戰功效率')[['成員','勢力值','戰功效率']]
    if not d3.empty:
        e3 = st.dataframe(us.style_df_slow(d3), hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="t3")
        if len(e3.selection['rows']): tm = d3.iloc[e3.selection['rows'][0]]['成員']
st.markdown("</div>", unsafe_allow_html=True)

# 戰術雷達
st.markdown("<div class='dashboard-card card-purple'>", unsafe_allow_html=True)
st.markdown("### 🛰️ 戰術雷達")
cb1, cb2, cb3, cb4 = st.columns(4)
for k, v in ud.RADAR_CONFIG.items():
    if k == 'reset':
        if cb4.button(v['desc']): set_preset(k)
    elif k == 'slave':
        if cb1.button(v['desc']): set_preset(k)
    elif k == 'elite':
        if cb2.button(v['desc']): set_preset(k)
    elif k == 'newbie':
        if cb3.button(v['desc']): set_preset(k)

cq1, cq2, cq3, cq4 = st.columns([1.2, 1.2, 0.8, 0.8])
with cq1: st.caption("戰功"); st.selectbox("", ["大於 >=", "小於 <="], key="q_merit_op", label_visibility="collapsed"); st.number_input("", step=10000, key="q_merit_val", label_visibility="collapsed")
with cq2: st.caption("勢力"); st.selectbox("", ["大於 >=", "小於 <="], key="q_power_op", label_visibility="collapsed"); st.number_input("", step=5000, key="q_power_val", label_visibility="collapsed")
with cq3: st.caption("效率"); st.selectbox("", ["大於 >=", "小於 <="], key="q_eff_op", label_visibility="collapsed"); st.number_input("", step=1.0, key="q_eff_val", label_visibility="collapsed")
with cq4: st.caption("Top N"); st.number_input("", step=10, key="q_rank", label_visibility="collapsed")

qdf = filt_df.copy()
# 篩選邏輯 (保持簡單，不移至 utils 因為涉及大量 st.session_state)
if "大於" in st.session_state.q_merit_op: qdf = qdf[qdf['戰功總量'] >= st.session_state.q_merit_val]
else: qdf = qdf[qdf['戰功總量'] <= st.session_state.q_merit_val]
if "大於" in st.session_state.q_power_op: qdf = qdf[qdf['勢力值'] >= st.session_state.q_power_val]
else: qdf = qdf[qdf['勢力值'] <= st.session_state.q_power_val]
if "大於" in st.session_state.q_eff_op: qdf = qdf[qdf['戰功效率'] >= st.session_state.q_eff_val]
else: qdf = qdf[qdf['戰功效率'] <= st.session_state.q_eff_val]
qdf = qdf[qdf['貢獻排行'] <= st.session_state.q_rank].sort_values('貢獻排行')

st.markdown(f"<div style='margin-top:10px;color:#AAA'>🎯 鎖定 {len(qdf)} 目標</div>", unsafe_allow_html=True)
if not qdf.empty:
    qdd = qdf[['成員', '分組', '貢獻排行', '戰功總量', '勢力值', '戰功效率']].copy()
    eq = st.dataframe(us.style_df_full(qdd, MERIT_THRESHOLD_95), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="t4")
    if len(eq.selection['rows']): tm = qdf.iloc[eq.selection['rows'][0]]['成員']
st.markdown("</div>", unsafe_allow_html=True)

# 戰區監控
st.markdown("<div class='dashboard-card card-gold'>", unsafe_allow_html=True)
st.markdown("### 🗺️ 戰區監控")
cr1, cr2 = st.columns([1, 2])
ar = list(filt_df['所屬勢力'].unique())
with cr1: st.caption("📍 前線"); fl = st.multiselect("", ar, key="frontline_select", default=st.session_state.frontline_regions, on_change=update_frontline_cookie, label_visibility="collapsed")
with cr2:
    rc = filt_df['所屬勢力'].value_counts().reset_index(); rc.columns = ['地區', '人數']
    rc['狀態'] = rc['地區'].apply(lambda x: '🔥 前線' if x in fl else '💤 後方')
    st.altair_chart(uc.get_warzone_bar_chart(rc), use_container_width=True)
    
if fl:
    infl = filt_df[filt_df['所屬勢力'].isin(fl)]; nofl = filt_df[~filt_df['所屬勢力'].isin(fl)]; r = len(infl)/len(filt_df)*100
    cz1, cz2 = st.columns(2); cz1.metric("前線", f"{len(infl)}", delta=f"{r:.1f}%"); cz2.metric("滯留", f"{len(nofl)}", delta="-未到", delta_color="inverse")
    with st.expander(f"📋 滯留名單 ({len(nofl)}人)"): 
        nd = nofl[['成員', '分組', '所屬勢力', '勢力值']].copy()
        if not nd.empty: st.dataframe(nd.style.format({"勢力值": us.format_k}).map(us.get_power_style, subset=['勢力值']), use_container_width=True, hide_index=True)
else: st.info("請勾選前線")
st.markdown("</div>", unsafe_allow_html=True)

# 最後觸發彈窗
if tm and tm != st.session_state.last_selected_member:
    st.session_state.last_selected_member = tm
    show_member_popup(tm, raw_df, G_MAX_M, G_MAX_P, G_MIN_P, MERIT_THRESHOLD_95)