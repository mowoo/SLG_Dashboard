import pandas as pd
import streamlit as st

# --- CSS 定義 ---
MAIN_CSS = """
<style>
    /* 全域背景 */
    .stApp { background-color: #121212; color: #E0E0E0; }
    .block-container { max_width: 1024px !important; padding: 1rem 1.5rem 3rem 1.5rem !important; margin: 0 auto !important; }
    div[data-testid="column"] { gap: 0.5rem; }
    
    /* 標題與文字 */
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 400; margin: 0 0 0.5rem 0 !important; letter-spacing: 1px; }
    
    /* 側邊欄 */
    section[data-testid="stSidebar"] { background-color: #0d0d0d; border-right: 1px solid #333; }
    
    /* KPI Card */
    .kpi-card { background-color: #1E1E1E; border: 1px solid #333; padding: 15px; border-radius: 6px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; }
    .kpi-label { color: #888; font-size: 0.85rem; margin-bottom: 5px; }
    .kpi-value { color: #FFF; font-size: 1.6rem; font-weight: bold; font-family: 'Arial Black', sans-serif; }
    
    /* 色票 Classes */
    .tier-s { color: #00FF55 !important; text-shadow: 0 0 15px rgba(0, 255, 85, 0.3); }
    .tier-a { color: #00E5FF !important; text-shadow: 0 0 10px rgba(0, 229, 255, 0.3); }
    .tier-b { color: #E0E0E0 !important; }

    /* Dashboard Cards */
    .dashboard-card { background-color: #1E1E1E; border: 1px solid #333; border-radius: 6px; padding: 15px; margin-bottom: 15px; }
    .card-cyan { border-top: 3px solid #00E5FF; }
    .card-red { border-top: 3px solid #D04F4F; }
    .card-blue { border-top: 3px solid #4F8CD0; }
    .card-purple { border-top: 3px solid #9B4FD0; }
    .card-gold { border-top: 3px solid #D4AF37; }

    /* Tables */
    .clean-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    .clean-table th { text-align: right; padding: 8px; color: #888; border-bottom: 1px solid #444; font-weight: normal; }
    .clean-table th:first-child { text-align: left; }
    .clean-table td { text-align: right; padding: 8px; color: #DDD; border-bottom: 1px solid #2A2A2A; }
    .clean-table td:first-child { text-align: left; color: #FFF; font-weight: bold; }
    .clean-table tr:hover { background-color: #2A2A2A; }

    /* Components Override */
    .stSelectbox, .stNumberInput, .stTextInput { margin-bottom: 0px !important; }
    div[data-testid="stSelectbox"] > div > div { background-color: #262626; border-color: #444; color: #DDD; min-height: 35px; }
    div[data-testid="stNumberInput"] > div > div > input { background-color: #262626; color: #DDD; min-height: 35px; }
    div.stButton > button { width: 100%; background-color: #262626; color: #AAA; border: 1px solid #444; border-radius: 4px; padding: 0.3rem; }
    div.stButton > button:hover { border-color: #777; color: #FFF; background-color: #333; }
    div[role="dialog"] { background-color: #000 !important; border: 1px solid #555; width: 72vw !important; max-width: 1200px !important; }
    
    /* 王牌檔案 Table */
    .ace-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .ace-table td { padding: 5px 0; vertical-align: bottom; border-bottom: 1px solid #333; }
    .ace-label-col { width: 1%; white-space: nowrap; font-size: 1.1rem; color: #888; text-transform: uppercase; padding-right: 15px !important; font-weight: bold; letter-spacing: 1px; }
    
    /* Version Tag */
    .version-tag { position: fixed; bottom: 10px; left: 10px; background-color: rgba(0, 0, 0, 0.7); color: #555; padding: 5px 10px; border-radius: 5px; font-size: 0.8rem; z-index: 9999; pointer-events: none; }
</style>
"""

def apply_css():
    st.markdown(MAIN_CSS, unsafe_allow_html=True)

# --- 格式化 Helper ---
def format_k(num):
    if pd.isna(num): return "0"
    try:
        num = float(num)
    except:
        return "0"
    if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
    if num >= 1_000: return f"{num/1_000:.1f}K"
    return f"{int(num)}"

def get_eff_style(val):
    if pd.isna(val): return "color: #E0E0E0"
    if val >= 10: return "color: #00FF55"
    if val >= 5: return "color: #00E5FF"
    return "color: #E0E0E0"

def get_eff_class(val):
    if pd.isna(val): return "tier-b"
    if val >= 10: return "tier-s"
    if val >= 5: return "tier-a"
    return "tier-b"

def get_merit_style(val, threshold):
    if pd.isna(val): return "color: #E0E0E0"
    if val >= threshold: return "color: #00FF55"
    return "color: #E0E0E0"

def get_power_style(val):
    if pd.isna(val): return "color: #E0E0E0"
    if val >= 30000: return "color: #00FF55"
    if val >= 15000: return "color: #00E5FF"
    return "color: #E0E0E0"

def style_df_full(df, merit_threshold):
    fmt = {}
    if '戰功總量' in df.columns: fmt['戰功總量'] = format_k
    if '勢力值' in df.columns: fmt['勢力值'] = format_k
    if '戰功效率' in df.columns: fmt['戰功效率'] = "{:.2f}"
    
    s = df.style.format(fmt)
    
    if '戰功總量' in df.columns:
        s = s.map(lambda x: get_merit_style(x, merit_threshold), subset=pd.IndexSlice[:, ['戰功總量']])
    if '勢力值' in df.columns:
        s = s.map(get_power_style, subset=pd.IndexSlice[:, ['勢力值']])
    if '戰功效率' in df.columns:
        s = s.map(get_eff_style, subset=pd.IndexSlice[:, ['戰功效率']])
    return s

def generate_ace_table_html(curr, s_merit, s_power, s_eff):
    return f"""<table class="ace-table">
            <tr><td class="ace-label-col">⚔️ 戰功</td><td class="ace-value-col" style="{s_merit}">{format_k(curr['戰功總量'])}</td></tr>
            <tr><td class="ace-label-col">🏰 勢力</td><td class="ace-value-col" style="{s_power}">{format_k(curr['勢力值'])}</td></tr>
            <tr><td class="ace-label-col">⚡ 效率</td><td class="ace-value-col" style="{s_eff}">{curr['戰功效率']}</td></tr>
            <tr><td class="ace-label-col">🏅 排名</td><td class="ace-value-col" style="color: #E0E0E0;">#{curr['貢獻排行']}</td></tr>
        </table>"""