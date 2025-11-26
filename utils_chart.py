import altair as alt

def get_dual_axis_growth_chart(data, max_merit, max_power, min_power):
    """繪製勢力(線)與戰功(面)的雙軸圖"""
    base = alt.Chart(data).encode(x=alt.X('紀錄時間', axis=alt.Axis(format='%m/%d', title=None)))
    
    line = base.mark_line(interpolate='basis', color='#00FF55', strokeWidth=2).encode(
        y=alt.Y('daily_power_growth', title='勢力(綠)', axis=alt.Axis(format='.2s', titleColor='#00FF55'), scale=alt.Scale(domain=[min_power, max_power])), 
        tooltip=['紀錄時間', alt.Tooltip('daily_power_growth', format=',.0f', title="勢力增長")]
    )
    
    area = base.mark_area(interpolate='basis', line={'color':'#FFE100'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='rgba(255, 225, 0, 0.5)', offset=0), alt.GradientStop(color='rgba(255, 225, 0, 0.1)', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(
        y=alt.Y('daily_merit_growth', title='戰功(黃)', axis=alt.Axis(format='.2s', titleColor='#FFE100', orient='right'), scale=alt.Scale(domain=[0, max_merit])), 
        tooltip=['紀錄時間', alt.Tooltip('daily_merit_growth', format=',.0f', title="戰功增長")]
    )
    
    return (line + area).resolve_scale(y='independent')

def get_ace_profile_chart(history, g_max_m, g_max_p, g_min_p):
    """王牌個人檔案的詳細圖表"""
    base = alt.Chart(history).encode(x=alt.X('紀錄時間', axis=alt.Axis(format='%m/%d', title=None)))
    
    line = base.mark_line(interpolate='basis', color='#00FF55', strokeWidth=3).encode(
        y=alt.Y('daily_power_growth', title='日增勢力 (綠)', axis=alt.Axis(titleColor='#00FF55', format='.2s'), scale=alt.Scale(domain=[g_min_p, g_max_p])), 
        tooltip=['紀錄時間', alt.Tooltip('daily_power_growth', format=',.0f', title='日增勢力')]
    )
    
    area = base.mark_area(interpolate='basis', line={'color':'#FFE100'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='rgba(255, 225, 0, 0.5)', offset=0), alt.GradientStop(color='rgba(255, 225, 0, 0.1)', offset=1)], x1=1, x2=1, y1=1, y2=0)).encode(
        y=alt.Y('daily_merit_growth', title='日增戰功 (黃)', axis=alt.Axis(titleColor='#FFE100', orient='right', format='.2s'), scale=alt.Scale(domain=[0, g_max_m])), 
        tooltip=['紀錄時間', alt.Tooltip('daily_merit_growth', format=',.0f', title='日增戰功')]
    )
    
    return (line + area).resolve_scale(y='independent').properties(height=600, padding={"left": 20, "right": 20, "top": 10, "bottom": 10}).interactive()

def get_warzone_bar_chart(rc):
    """戰區分佈長條圖"""
    chart = alt.Chart(rc).mark_bar().encode(
        x=alt.X('人數', title=None), 
        y=alt.Y('地區', sort='-x', title=None), 
        color=alt.Color('狀態', scale=alt.Scale(domain=['🔥 前線', '💤 後方'], range=['#D4AF37', '#444']), legend=None), 
        tooltip=['地區', '人數']
    ).properties(height=150)
    return chart