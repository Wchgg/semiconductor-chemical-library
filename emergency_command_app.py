from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from emergency_app.core import (
    build_command_roster,
    build_resource_board,
    build_sector_status,
    build_task_board,
    calculate_incident_score,
    classify_response_level,
    default_communication_log,
    generate_response_objectives,
)


st.set_page_config(page_title="紧急应变指挥系统", layout="wide")

st.markdown(
    """
    <style>
    :root {
      --bg-top: #08131f;
      --bg-mid: #102232;
      --bg-bottom: #d6dfd2;
      --panel: rgba(8, 19, 31, 0.72);
      --panel-soft: rgba(255, 255, 255, 0.08);
      --border: rgba(255, 255, 255, 0.12);
      --accent: #ff7a18;
      --accent-2: #22c55e;
      --text-main: #f6f7f2;
      --text-soft: #d2dbe4;
      --warn: #f97316;
      --danger: #ef4444;
    }

    html, body, [data-testid="stAppViewContainer"] {
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(255, 122, 24, 0.18), transparent 26%),
        radial-gradient(circle at top right, rgba(34, 197, 94, 0.12), transparent 24%),
        linear-gradient(180deg, var(--bg-top) 0%, var(--bg-mid) 48%, #e9ece7 100%);
    }

    [data-testid="stHeader"] {
      background: transparent;
    }

    .block-container {
      padding-top: 1.1rem;
      padding-bottom: 2rem;
    }

    .hero-panel {
      padding: 1.35rem 1.5rem;
      border-radius: 22px;
      background: linear-gradient(140deg, rgba(6, 14, 24, 0.90), rgba(18, 36, 52, 0.88));
      border: 1px solid var(--border);
      box-shadow: 0 18px 50px rgba(0, 0, 0, 0.25);
      color: var(--text-main);
      margin-bottom: 1rem;
    }

    .hero-kicker {
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 0.75rem;
      color: #ffcf99;
      margin-bottom: 0.55rem;
    }

    .hero-title {
      font-size: clamp(2rem, 3.6vw, 3.6rem);
      font-weight: 700;
      line-height: 1.05;
      margin-bottom: 0.5rem;
    }

    .hero-subtitle {
      color: var(--text-soft);
      max-width: 58rem;
      font-size: 1rem;
    }

    .info-strip {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      margin-top: 1rem;
    }

    .info-chip {
      background: rgba(255, 255, 255, 0.07);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 999px;
      padding: 0.45rem 0.8rem;
      font-size: 0.88rem;
    }

    .section-card {
      border-radius: 20px;
      padding: 1rem 1.15rem;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(8, 19, 31, 0.08);
      box-shadow: 0 14px 32px rgba(8, 19, 31, 0.08);
      margin-bottom: 1rem;
    }

    .section-card.dark {
      background: var(--panel);
      color: var(--text-main);
      border: 1px solid var(--border);
    }

    .section-card h3 {
      margin-top: 0;
      margin-bottom: 0.45rem;
      font-size: 1.05rem;
    }

    .metric-note {
      color: rgba(255, 255, 255, 0.72);
      font-size: 0.84rem;
    }

    [data-testid="stMetric"] {
      background: rgba(255, 255, 255, 0.78);
      border-radius: 18px;
      padding: 0.8rem 0.95rem;
      border: 1px solid rgba(8, 19, 31, 0.08);
    }

    [data-testid="stSidebar"] {
      background: rgba(6, 14, 24, 0.92);
    }

    [data-testid="stSidebar"] * {
      color: #f6f7f2 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


INCIDENT_TYPES = [
    "城市火灾",
    "危化品泄漏",
    "地震灾害",
    "洪涝灾害",
    "公共卫生",
    "综合突发",
]


def init_log_state(level: str, incident_type: str, commander: str) -> None:
    seed_signature = f"{level}|{incident_type}|{commander}"
    if st.session_state.get("log_seed") != seed_signature:
        st.session_state["log_seed"] = seed_signature
        st.session_state["command_log"] = default_communication_log(level, incident_type, commander)


def add_log_entry(category: str, sender: str, content: str) -> None:
    if not content.strip():
        return
    entry = {
        "时间": datetime.now().strftime("%H:%M"),
        "类别": category,
        "发送方": sender.strip() or "值守席",
        "内容": content.strip(),
    }
    st.session_state["command_log"] = [entry] + st.session_state["command_log"]


def render_metric_card(title: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="section-card dark">
          <h3>{title}</h3>
          <div style="font-size:2rem;font-weight:700;line-height:1.05;">{value}</div>
          <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sector_chart(sector_frame: pd.DataFrame) -> go.Figure:
    color_map = {
        "红色警戒": "#ef4444",
        "橙色管控": "#f97316",
        "黄色巡查": "#facc15",
        "绿色稳定": "#22c55e",
    }
    chart = px.scatter(
        sector_frame,
        x="横轴",
        y="纵轴",
        size="风险指数",
        color="状态",
        color_discrete_map=color_map,
        text="区域",
        hover_data={"风险指数": True, "人员密度": ":.0%", "通行能力": ":.0%", "横轴": False, "纵轴": False},
    )
    chart.update_traces(textposition="top center", marker={"opacity": 0.9, "line": {"width": 1.5, "color": "#ffffff"}})
    chart.update_layout(
        height=380,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis_title="东侧到西侧指挥轴线",
        yaxis_title="外围到核心风险纵深",
        legend_title="区域状态",
    )
    return chart


def render_resource_chart(resource_frame: pd.DataFrame) -> go.Figure:
    chart = go.Figure()
    chart.add_trace(
        go.Bar(
            x=resource_frame["资源类型"],
            y=resource_frame["已出动"],
            name="已出动",
            marker_color="#ff7a18",
        )
    )
    chart.add_trace(
        go.Bar(
            x=resource_frame["资源类型"],
            y=resource_frame["待命"],
            name="待命",
            marker_color="#0f766e",
        )
    )
    chart.update_layout(
        barmode="stack",
        height=360,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        yaxis_title="资源数量",
        xaxis_title="",
    )
    return chart


with st.sidebar:
    st.header("事件控制台")
    incident_name = st.text_input("事件名称", value="滨江化工园区泄漏处置")
    incident_type = st.selectbox("事件类型", INCIDENT_TYPES, index=1)
    location = st.text_input("事发地点", value="滨江新区东二路 18 号")
    commander = st.text_input("值守总指挥", value="王敏")
    severity = st.slider("事件严重度", min_value=1, max_value=5, value=4)
    affected_people = st.number_input("影响人数", min_value=0, value=260, step=20)
    critical_sites = st.slider("受影响重点点位", min_value=0, max_value=10, value=3)
    weather_risk = st.slider("气象外溢风险", min_value=0.0, max_value=1.0, value=0.55, step=0.05)
    medical_pressure = st.slider("医疗承压系数", min_value=0.0, max_value=1.0, value=0.45, step=0.05)
    evacuation_progress = st.slider("疏散完成率", min_value=0.0, max_value=1.0, value=0.68, step=0.01)
    communications_disrupted = st.toggle("通信链路受扰", value=True)
    auto_refresh = st.toggle("自动刷新", value=False)
    if auto_refresh:
        st_autorefresh(interval=20_000, key="emergency-refresh")


score = calculate_incident_score(
    severity=severity,
    affected_people=int(affected_people),
    critical_sites=critical_sites,
    weather_risk=weather_risk,
    medical_pressure=medical_pressure,
    communications_disrupted=communications_disrupted,
)
level = classify_response_level(score)
command_roster = build_command_roster(commander=commander, location=location)
resource_board = build_resource_board(level=level, affected_people=int(affected_people), medical_pressure=medical_pressure)
task_board = build_task_board(
    incident_type=incident_type,
    level=level,
    evacuation_progress=evacuation_progress,
)
sector_status = build_sector_status(
    severity=severity,
    affected_people=int(affected_people),
    weather_risk=weather_risk,
    evacuation_progress=evacuation_progress,
)
objectives = generate_response_objectives(
    incident_type=incident_type,
    level=level,
    affected_people=int(affected_people),
    communications_disrupted=communications_disrupted,
)

init_log_state(level=level, incident_type=incident_type, commander=commander)

last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

st.markdown(
    f"""
    <div class="hero-panel">
      <div class="hero-kicker">Emergency Command System</div>
      <div class="hero-title">{incident_name}</div>
      <div class="hero-subtitle">
        用于前方指挥席、联动单位和值守中心共享同一态势图、同一任务板和同一通信链路。
      </div>
      <div class="info-strip">
        <div class="info-chip">响应等级：{level}</div>
        <div class="info-chip">事发地点：{location}</div>
        <div class="info-chip">总指挥：{commander}</div>
        <div class="info-chip">最后更新：{last_updated}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(4)
with metric_cols[0]:
    render_metric_card("事件评分", str(score), "综合严重度、人数、重点点位、气象与医疗承压计算")
with metric_cols[1]:
    render_metric_card("影响人数", f"{int(affected_people)}", "纳入疏散、医疗和安置调度口径")
with metric_cols[2]:
    resource_gap = int(resource_board["缺口"].sum())
    render_metric_card("资源缺口", str(resource_gap), "优先向短板资源发起增援请求")
with metric_cols[3]:
    render_metric_card("疏散进度", f"{evacuation_progress:.0%}", "低于 75% 时维持高频滚动播报")

overview_tab, command_tab, resource_tab, sector_tab, comms_tab = st.tabs(
    ["综合态势", "指挥体系", "资源调度", "分区态势", "通信日志"]
)

with overview_tab:
    left, right = st.columns([1.05, 0.95])
    with left:
        st.markdown('<div class="section-card dark"><h3>行动目标</h3></div>', unsafe_allow_html=True)
        for item in objectives:
            st.markdown(f"- {item}")
        risk_text = "通信受扰，建议启用备份链路。" if communications_disrupted else "主通信链路稳定，可维持标准播报频率。"
        st.info(
            f"当前 {level}，重点点位 {critical_sites} 处，{risk_text}"
        )
    with right:
        st.markdown('<div class="section-card"><h3>任务快照</h3></div>', unsafe_allow_html=True)
        status_counts = task_board["状态"].value_counts().rename_axis("状态").reset_index(name="数量")
        donut = px.pie(status_counts, names="状态", values="数量", hole=0.62, color="状态")
        donut.update_layout(height=320, margin={"l": 10, "r": 10, "t": 10, "b": 10}, showlegend=True)
        st.plotly_chart(donut, use_container_width=True)
        priority_text = "高优任务较多，建议维持 15 分钟复盘节奏。" if (task_board["优先级"] == "高").sum() >= 5 else "当前可按照标准班次推进。"
        st.caption(priority_text)

with command_tab:
    left, right = st.columns([1.05, 0.95])
    with left:
        st.markdown('<div class="section-card"><h3>统一指挥编组</h3></div>', unsafe_allow_html=True)
        st.dataframe(command_roster, use_container_width=True, hide_index=True)
    with right:
        st.markdown('<div class="section-card"><h3>任务看板</h3></div>', unsafe_allow_html=True)
        st.dataframe(task_board, use_container_width=True, hide_index=True)

with resource_tab:
    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown('<div class="section-card"><h3>资源投送结构</h3></div>', unsafe_allow_html=True)
        st.plotly_chart(render_resource_chart(resource_board), use_container_width=True)
    with right:
        st.markdown('<div class="section-card"><h3>资源状态表</h3></div>', unsafe_allow_html=True)
        display_board = resource_board.copy()
        display_board["到位率"] = display_board["到位率"].map(lambda value: f"{value:.0%}")
        st.dataframe(display_board, use_container_width=True, hide_index=True)

with sector_tab:
    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown('<div class="section-card"><h3>现场分区态势图</h3></div>', unsafe_allow_html=True)
        st.plotly_chart(render_sector_chart(sector_status), use_container_width=True)
    with right:
        st.markdown('<div class="section-card"><h3>分区监测数据</h3></div>', unsafe_allow_html=True)
        display_sector = sector_status.copy()
        display_sector["人员密度"] = display_sector["人员密度"].map(lambda value: f"{value:.0%}")
        display_sector["通行能力"] = display_sector["通行能力"].map(lambda value: f"{value:.0%}")
        st.dataframe(display_sector.drop(columns=["横轴", "纵轴"]), use_container_width=True, hide_index=True)

with comms_tab:
    left, right = st.columns([1.05, 0.95])
    with left:
        st.markdown('<div class="section-card"><h3>指挥通信日志</h3></div>', unsafe_allow_html=True)
        log_frame = pd.DataFrame(st.session_state["command_log"])
        st.dataframe(log_frame, use_container_width=True, hide_index=True)
        latest = log_frame.iloc[0]
        st.caption(f"最近播报：{latest['时间']} {latest['发送方']} - {latest['内容']}")
    with right:
        st.markdown('<div class="section-card"><h3>新增播报</h3></div>', unsafe_allow_html=True)
        with st.form("add-log", clear_on_submit=True):
            category = st.selectbox("日志类别", ["调度命令", "态势播报", "医疗回报", "物资回报", "公众信息"])
            sender = st.text_input("发送方", value=commander)
            content = st.text_area("播报内容", placeholder="例如：东侧警戒区已封控，转运通道保持畅通。")
            submitted = st.form_submit_button("写入日志", use_container_width=True)
            if submitted:
                add_log_entry(category=category, sender=sender, content=content)
