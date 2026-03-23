from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from emergency_app.semiconductor import (
    apply_rollcall_override,
    authenticate_user,
    SEMICONDUCTOR_INCIDENT_TYPES,
    build_aloha_quick_estimate,
    build_badge_audit_board,
    build_chemical_ghs_profile,
    build_cross_fab_support_board,
    build_user_role_matrix,
    build_gms_sensor_board,
    build_incident_control_profile,
    build_monitoring_interface_board,
    build_reference_supplements,
    build_semiconductor_alert_board,
    build_semiconductor_command_roster,
    build_semiconductor_facility_status,
    build_semiconductor_objectives,
    build_photo_checklist_library,
    build_photo_ero_structure,
    build_photo_process_library,
    build_semiconductor_recovery_checklist,
    build_semiconductor_rollcall_board,
    build_semiconductor_resource_board,
    build_sop_execution_board,
    build_semiconductor_task_board,
    build_taiwan_bcm_stage_board,
    build_semiconductor_timeline,
    build_semiconductor_wip_board,
    build_semiconductor_zone_status,
    calculate_semiconductor_risk_score,
    classify_semiconductor_response_level,
    describe_wind_direction,
    default_semiconductor_log,
    fetch_live_weather_snapshot,
    get_role_permissions,
    get_checklist_name_for_incident,
    get_process_name_for_incident,
    get_taiwan_fab_sites,
    load_user_accounts,
    save_user_accounts,
    set_user_active_status,
    upsert_user_account,
)


st.set_page_config(page_title="半导体应急指挥系统", layout="wide")

ALOHA_OFFICIAL_URL = "https://www.epa.gov/cameo/aloha-software"
OPEN_METEO_URL = "https://open-meteo.com/en/docs"
CAMEO_CHEMICALS_URL = "https://cameochemicals.noaa.gov/"
USER_ACCOUNTS_PATH = Path(__file__).resolve().parent / "data" / "semiconductor_users.json"

ACTION_STATUS_LABELS = {
    "broadcast": "厂广播已启动",
    "cross_fab_cctv": "跨厂 CCTV 已共享",
    "aloha": "ALOHA 推估已启动",
    "external_support": "外部支援已请求",
    "wip_lock": "高风险 WIP 已冻结",
    "fire_linkage": "火警联动已启动",
    "gms_recheck": "GMS 复测已派发",
    "rollcall_muster": "二次点名已发布",
    "facility_isolation": "厂务隔离已执行",
    "incident_briefing": "事故快报已发出",
}

st.markdown(
    """
    <style>
    :root {
      --bg-top: #0b1b34;
      --bg-mid: #163a63;
      --bg-bottom: #e9f1fb;
      --panel-dark: rgba(10, 24, 47, 0.88);
      --panel-darker: rgba(7, 18, 37, 0.94);
      --panel-light: rgba(252, 249, 242, 0.88);
      --panel-soft: rgba(230, 241, 255, 0.12);
      --border-dark: rgba(210, 229, 255, 0.12);
      --border-light: rgba(40, 78, 126, 0.10);
      --text-light: #f8fafc;
      --text-soft: rgba(248, 250, 252, 0.76);
      --text-dark: #1f2937;
      --accent: #5aa7ff;
      --accent-2: #2e74c8;
      --warning: #d18b2b;
      --danger: #b4413c;
      --ok: #2f7dba;
    }

    html, body, [data-testid="stAppViewContainer"] {
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(90, 167, 255, 0.22), transparent 28%),
        radial-gradient(circle at top right, rgba(46, 116, 200, 0.16), transparent 24%),
        linear-gradient(180deg, var(--bg-top) 0%, var(--bg-mid) 48%, #eef5ff 100%);
    }

    .hero-title, .section-title, .matrix-title, .tile-value, .kpi-value {
      letter-spacing: -0.02em;
    }

    .hero-title, .section-title {
      font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
    }

    [data-testid="stHeader"] {
      background: transparent;
    }

    .block-container {
      padding-top: 0.9rem;
      padding-bottom: 2rem;
      max-width: 1460px;
    }

    .hero {
      position: relative;
      overflow: hidden;
      border-radius: 28px;
      padding: 1.45rem 1.55rem;
      border: 1px solid var(--border-dark);
      background:
        linear-gradient(135deg, rgba(10, 24, 47, 0.98), rgba(20, 50, 88, 0.92)),
        linear-gradient(90deg, rgba(90, 167, 255, 0.14), transparent);
      box-shadow: 0 26px 60px rgba(0, 0, 0, 0.25);
      color: var(--text-light);
      margin-bottom: 1rem;
    }

    .hero::after {
      content: "";
      position: absolute;
      inset: auto -8% -35% auto;
      width: 340px;
      height: 340px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(90, 167, 255, 0.22), transparent 68%);
      pointer-events: none;
    }

    .hero-kicker {
      text-transform: uppercase;
      letter-spacing: 0.2em;
      font-size: 0.74rem;
      color: #b9dbff;
      margin-bottom: 0.55rem;
    }

    .hero-grid {
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 1rem;
      align-items: end;
    }

    .hero-title {
      font-size: clamp(2rem, 3.8vw, 3.7rem);
      font-weight: 700;
      line-height: 1.04;
      margin-bottom: 0.5rem;
    }

    .hero-subtitle {
      color: var(--text-soft);
      max-width: 52rem;
      font-size: 0.98rem;
    }

    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.65rem;
      margin-top: 1rem;
    }

    .chip {
      padding: 0.44rem 0.78rem;
      border-radius: 999px;
      background: rgba(255, 248, 235, 0.08);
      border: 1px solid rgba(255, 243, 224, 0.12);
      font-size: 0.88rem;
    }

    .hero-right {
      display: grid;
      gap: 0.65rem;
    }

    .hero-panel {
      background: rgba(255, 248, 235, 0.08);
      border: 1px solid rgba(255, 243, 224, 0.12);
      border-radius: 18px;
      padding: 0.9rem 1rem;
    }

    .hero-panel-label {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: rgba(248, 250, 252, 0.66);
      margin-bottom: 0.35rem;
    }

    .hero-panel-value {
      font-size: 1.55rem;
      font-weight: 700;
      line-height: 1.05;
    }

    .status-band {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 0.8rem;
      margin: 0.25rem 0 1rem;
    }

    .status-tile {
      padding: 0.95rem 1rem;
      border-radius: 18px;
      color: var(--text-light);
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.12);
    }

    .tile-red { background: linear-gradient(135deg, rgba(112, 40, 40, 0.96), rgba(180, 65, 60, 0.78)); }
    .tile-amber { background: linear-gradient(135deg, rgba(123, 83, 30, 0.96), rgba(197, 139, 42, 0.80)); }
    .tile-cyan { background: linear-gradient(135deg, rgba(54, 74, 67, 0.96), rgba(63, 107, 91, 0.82)); }
    .tile-green { background: linear-gradient(135deg, rgba(39, 84, 63, 0.96), rgba(47, 125, 90, 0.80)); }

    .tile-title {
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      opacity: 0.84;
      margin-bottom: 0.32rem;
    }

    .tile-value {
      font-size: 1.6rem;
      font-weight: 700;
      line-height: 1.05;
    }

    .tile-note {
      font-size: 0.84rem;
      opacity: 0.78;
      margin-top: 0.28rem;
    }

    .card-light, .card-dark {
      border-radius: 20px;
      padding: 1rem 1.1rem;
      margin-bottom: 1rem;
    }

    .card-light {
      background: var(--panel-light);
      border: 1px solid var(--border-light);
      box-shadow: 0 16px 34px rgba(7, 16, 26, 0.08);
      color: var(--text-dark);
    }

    .card-dark {
      background: var(--panel-dark);
      border: 1px solid var(--border-dark);
      box-shadow: 0 18px 38px rgba(0, 0, 0, 0.15);
      color: var(--text-light);
    }

    .section-title {
      font-size: 1.02rem;
      font-weight: 700;
      margin-bottom: 0.32rem;
    }

    .section-head-light, .section-head-dark {
      border-radius: 18px;
      padding: 0.85rem 1rem 0.8rem;
      margin-bottom: 0.55rem;
    }

    .section-head-light {
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid rgba(7, 16, 26, 0.08);
      box-shadow: 0 12px 28px rgba(7, 16, 26, 0.06);
      color: var(--text-dark);
    }

    .section-head-dark {
      background: rgba(7, 16, 26, 0.82);
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 16px 34px rgba(0, 0, 0, 0.12);
      color: var(--text-light);
    }

    .section-subtitle {
      font-size: 0.86rem;
      color: rgba(15, 23, 42, 0.65);
      margin-bottom: 0.75rem;
    }

    .dark-subtitle {
      font-size: 0.86rem;
      color: rgba(248, 250, 252, 0.68);
      margin-bottom: 0.75rem;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 0.8rem;
      margin-bottom: 1rem;
    }

    .kpi-card {
      background: rgba(255, 255, 255, 0.86);
      border: 1px solid rgba(7, 16, 26, 0.08);
      border-radius: 20px;
      padding: 0.95rem 1rem;
      box-shadow: 0 12px 28px rgba(7, 16, 26, 0.08);
      color: var(--text-dark);
    }

    .kpi-label {
      font-size: 0.82rem;
      color: rgba(15, 23, 42, 0.68);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 0.28rem;
    }

    .kpi-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--text-dark);
      line-height: 1.05;
    }

    .kpi-note {
      font-size: 0.84rem;
      color: rgba(15, 23, 42, 0.62);
      margin-top: 0.26rem;
    }

    .mini-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.7rem;
    }

    .mini-card {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 0.8rem 0.88rem;
    }

    .mini-label {
      font-size: 0.8rem;
      color: rgba(248, 250, 252, 0.64);
      margin-bottom: 0.22rem;
    }

    .mini-value {
      font-size: 1.2rem;
      font-weight: 700;
      line-height: 1.05;
    }

    .gate-item {
      display: flex;
      justify-content: space-between;
      gap: 0.8rem;
      padding: 0.72rem 0;
      border-bottom: 1px solid rgba(7, 16, 26, 0.08);
    }

    .gate-item:last-child {
      border-bottom: none;
    }

    .gate-status {
      white-space: nowrap;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
    }

    .gate-ok {
      background: rgba(34, 197, 94, 0.15);
      color: #15803d;
    }

    .gate-wait {
      background: rgba(245, 158, 11, 0.16);
      color: #b45309;
    }

    .timeline-item {
      display: grid;
      grid-template-columns: 74px 1fr;
      gap: 0.8rem;
      padding: 0.62rem 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    .timeline-item:last-child {
      border-bottom: none;
    }

    .timeline-time {
      color: #8cebf4;
      font-weight: 700;
    }

    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, rgba(8, 37, 78, 0.98), rgba(17, 66, 129, 0.96));
      font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
      font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #f8fafc !important;
    }

    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span {
      font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
      color: #f8fafc !important;
    }

    [data-testid="stSidebar"] .sidebar-panel,
    [data-testid="stSidebar"] .sidebar-panel *,
    [data-testid="stSidebar"] .sidebar-heading,
    [data-testid="stSidebar"] .sidebar-title,
    [data-testid="stSidebar"] .sidebar-note,
    [data-testid="stSidebar"] .sidebar-chip,
    [data-testid="stSidebar"] .sidebar-stat-label,
    [data-testid="stSidebar"] .sidebar-stat-value {
      color: #f8fafc !important;
    }

    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] label p {
      font-size: 0.92rem !important;
      font-weight: 600 !important;
      letter-spacing: 0.01em;
      color: #f8fafc !important;
      font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif !important;
    }

    [data-testid="stSidebar"] [data-testid="stTextInput"] input,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] input,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] div,
    [data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"],
    [data-testid="stSidebar"] summary,
    [data-testid="stSidebar"] summary * {
      font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif !important;
      font-size: 0.95rem !important;
      font-weight: 500 !important;
    }

    [data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="base-input"],
    [data-testid="stSidebar"] [data-testid="stNumberInput"] [data-baseweb="base-input"],
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] textarea {
      background: rgba(210, 229, 255, 0.12) !important;
      border: 1px solid rgba(210, 229, 255, 0.22) !important;
      color: #0f172a !important;
    }

    [data-testid="stSidebar"] [data-testid="stTextInput"] input,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] input,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] div,
    [data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="input"] div,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] [data-baseweb="input"] div {
      color: #0f172a !important;
      caret-color: #0f172a !important;
      -webkit-text-fill-color: #0f172a !important;
    }

    [data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] input::placeholder,
    [data-testid="stSidebar"] textarea::placeholder {
      color: rgba(15, 23, 42, 0.48) !important;
      -webkit-text-fill-color: rgba(15, 23, 42, 0.48) !important;
    }

    .sidebar-panel {
      background: rgba(210, 229, 255, 0.10);
      border: 1px solid rgba(210, 229, 255, 0.18);
      border-radius: 18px;
      padding: 0.9rem 0.95rem;
      margin-bottom: 0.8rem;
    }

    .sidebar-heading {
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: rgba(248, 250, 252, 0.68);
      margin-bottom: 0.45rem;
      font-weight: 700;
    }

    .sidebar-title {
      font-size: 1.1rem;
      font-weight: 700;
      color: #f8fafc;
      margin-bottom: 0.25rem;
    }

    .sidebar-note {
      font-size: 0.84rem;
      color: rgba(248, 250, 252, 0.72);
      line-height: 1.5;
    }

    .sidebar-chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      margin-top: 0.55rem;
    }

    .sidebar-chip {
      padding: 0.22rem 0.54rem;
      border-radius: 999px;
      background: rgba(210, 229, 255, 0.12);
      border: 1px solid rgba(210, 229, 255, 0.18);
      font-size: 0.78rem;
      color: #f8fafc;
    }

    .sidebar-stat-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.55rem;
      margin-top: 0.55rem;
    }

    .sidebar-stat {
      padding: 0.62rem 0.68rem;
      border-radius: 14px;
      background: rgba(210, 229, 255, 0.08);
      border: 1px solid rgba(210, 229, 255, 0.14);
    }

    .sidebar-stat-label {
      font-size: 0.76rem;
      color: rgba(248, 250, 252, 0.66);
      margin-bottom: 0.18rem;
    }

    .sidebar-stat-value {
      font-size: 1rem;
      font-weight: 700;
      color: #f8fafc;
    }

    [data-testid="stSidebar"] [data-testid="stSlider"] *,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] button,
    [data-testid="stSidebar"] summary,
    [data-testid="stSidebar"] summary * {
      color: #f8fafc !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] [aria-selected="true"],
    [data-testid="stSidebar"] [data-baseweb="select"] [aria-selected="true"] *,
    [role="listbox"] div,
    [role="listbox"] span,
    [data-baseweb="popover"] div,
    [data-baseweb="menu"] div {
      color: #1f2937 !important;
    }

    [data-testid="stPlotlyChart"],
    [data-testid="stDataFrame"],
    [data-testid="stForm"] {
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid rgba(7, 16, 26, 0.08);
      border-radius: 18px;
      box-shadow: 0 12px 28px rgba(7, 16, 26, 0.06);
      padding: 0.55rem;
    }

    .card-light,
    .section-head-light,
    .kpi-card,
    .matrix-card:not(.dark),
    .stage-card,
    .ticker-shell,
    [data-testid="stPlotlyChart"],
    [data-testid="stDataFrame"],
    [data-testid="stForm"] {
      color: var(--text-dark);
    }

    .card-light p,
    .card-light div,
    .card-light span,
    .section-head-light div,
    .section-head-light span,
    .kpi-card div,
    .matrix-card:not(.dark) div,
    .matrix-card:not(.dark) span,
    .stage-card div,
    .stage-card span,
    .ticker-shell div,
    .ticker-shell span,
    [data-testid="stForm"] label,
    [data-testid="stForm"] p,
    [data-testid="stForm"] span,
    [data-testid="stForm"] div {
      color: inherit;
    }

    [data-testid="stForm"] input,
    [data-testid="stForm"] textarea,
    [data-testid="stForm"] [data-baseweb="select"] > div {
      color: var(--text-dark) !important;
    }

    [data-testid="stForm"] input::placeholder,
    [data-testid="stForm"] textarea::placeholder {
      color: rgba(31, 41, 55, 0.45) !important;
    }

    [data-testid="stAlert"] {
      border-radius: 16px;
    }

    .stButton > button, .stLinkButton > a {
      border-radius: 14px !important;
      font-weight: 700 !important;
      letter-spacing: 0.01em;
      min-height: 2.7rem;
    }

    .stLinkButton > a {
      background: linear-gradient(135deg, rgba(123, 83, 30, 0.98), rgba(197, 139, 42, 0.82));
      color: #f8fafc !important;
      border: none !important;
      box-shadow: 0 12px 28px rgba(7, 16, 26, 0.12);
    }

    .role-cloud {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.5rem;
    }

    .role-pill {
      padding: 0.34rem 0.62rem;
      border-radius: 999px;
      background: rgba(34, 211, 238, 0.12);
      color: #0f172a;
      border: 1px solid rgba(34, 211, 238, 0.16);
      font-size: 0.84rem;
      font-weight: 600;
    }

    .matrix-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1rem;
    }

    .matrix-card {
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid rgba(7, 16, 26, 0.08);
      border-radius: 18px;
      box-shadow: 0 12px 28px rgba(7, 16, 26, 0.06);
      padding: 0.9rem 0.95rem;
    }

    .matrix-card.dark {
      background: rgba(7, 16, 26, 0.84);
      border: 1px solid rgba(255, 255, 255, 0.10);
      color: var(--text-light);
    }

    .matrix-title {
      font-size: 0.95rem;
      font-weight: 700;
      margin-bottom: 0.2rem;
    }

    .matrix-meta {
      font-size: 0.82rem;
      color: rgba(15, 23, 42, 0.62);
      margin-bottom: 0.45rem;
    }

    .matrix-card.dark .matrix-meta {
      color: rgba(248, 250, 252, 0.70);
    }

    .signal-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.22rem 0.55rem;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
    }

    .badge-red { background: rgba(180, 65, 60, 0.14); color: #8f2d2a; }
    .badge-amber { background: rgba(197, 139, 42, 0.18); color: #8b5d1c; }
    .badge-green { background: rgba(47, 125, 90, 0.16); color: #236145; }
    .badge-cyan { background: rgba(63, 107, 91, 0.16); color: #315749; }
    .badge-slate { background: rgba(100, 116, 139, 0.14); color: #334155; }

    .lane-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.8rem;
      margin-bottom: 1rem;
    }

    .lane-card {
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid rgba(7, 16, 26, 0.08);
      border-radius: 18px;
      padding: 0.9rem 0.95rem;
      box-shadow: 0 12px 28px rgba(7, 16, 26, 0.06);
    }

    .task-item, .feed-item, .check-item {
      padding: 0.72rem 0;
      border-bottom: 1px solid rgba(7, 16, 26, 0.08);
    }

    .task-item:last-child, .feed-item:last-child, .check-item:last-child {
      border-bottom: none;
    }

    .progress-track {
      width: 100%;
      height: 8px;
      background: rgba(148, 163, 184, 0.18);
      border-radius: 999px;
      overflow: hidden;
      margin: 0.4rem 0 0.3rem;
    }

    .progress-fill {
      height: 100%;
      border-radius: 999px;
    }

    .feed-time {
      font-size: 0.78rem;
      color: rgba(15, 23, 42, 0.55);
      margin-bottom: 0.18rem;
    }

    .zone-stack, .checklist-stack {
      display: grid;
      gap: 0.75rem;
      margin-bottom: 1rem;
    }

    .stage-card {
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid rgba(7, 16, 26, 0.08);
      border-radius: 18px;
      padding: 0.9rem 1rem;
      box-shadow: 0 12px 28px rgba(7, 16, 26, 0.06);
    }

    .aloha-zone-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.8rem;
      margin-bottom: 1rem;
    }

    .aloha-zone-card {
      border-radius: 18px;
      padding: 0.95rem 1rem;
      color: #f8fafc;
      box-shadow: 0 16px 34px rgba(0, 0, 0, 0.12);
    }

    .aloha-red { background: linear-gradient(135deg, rgba(127, 29, 29, 0.96), rgba(239, 68, 68, 0.78)); }
    .aloha-orange { background: linear-gradient(135deg, rgba(154, 52, 18, 0.96), rgba(249, 115, 22, 0.78)); }
    .aloha-yellow { background: linear-gradient(135deg, rgba(133, 77, 14, 0.96), rgba(234, 179, 8, 0.78)); color: #111827; }

    .weather-note {
      font-size: 0.84rem;
      color: rgba(15, 23, 42, 0.62);
      margin-top: 0.35rem;
    }

    .ticker-shell {
      overflow: hidden;
      border-radius: 18px;
      padding: 0.78rem 0;
      margin: 0.15rem 0 1rem;
      background: rgba(252, 249, 242, 0.9);
      border: 1px solid rgba(53, 62, 56, 0.10);
      box-shadow: 0 12px 28px rgba(7, 16, 26, 0.06);
      white-space: nowrap;
    }

    .ticker-track {
      display: inline-block;
      padding-left: 100%;
      animation: ticker-scroll 42s linear infinite;
    }

    .ticker-item {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      margin-right: 2rem;
      font-size: 0.92rem;
      color: #1f2937;
      font-weight: 600;
    }

    .ticker-item-new {
      color: #8f2d2a;
      font-weight: 700;
    }

    .ticker-dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: #c58b2a;
      display: inline-block;
    }

    .ticker-pill-new {
      display: inline-flex;
      align-items: center;
      padding: 0.16rem 0.46rem;
      border-radius: 999px;
      background: rgba(180, 65, 60, 0.14);
      color: #8f2d2a;
      font-size: 0.74rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      margin-right: 0.15rem;
    }

    @keyframes ticker-scroll {
      0% { transform: translateX(0); }
      100% { transform: translateX(-100%); }
    }

    @media (max-width: 1100px) {
      .hero-grid, .status-band, .kpi-grid, .mini-grid {
        grid-template-columns: 1fr;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_log_state(level: str, incident_type: str, commander: str, fab_name: str) -> None:
    seed = f"{level}|{incident_type}|{commander}|{fab_name}"
    if st.session_state.get("semi_log_seed") != seed:
        st.session_state["semi_log_seed"] = seed
        st.session_state["semi_command_log"] = default_semiconductor_log(
            fab_name=fab_name,
            incident_type=incident_type,
            level=level,
            commander=commander,
        )


def init_interaction_state(seed: str) -> None:
    if st.session_state.get("semi_interaction_seed") != seed:
        st.session_state["semi_interaction_seed"] = seed
        st.session_state["semi_action_feed"] = []
        st.session_state["semi_ack_alerts"] = []
        st.session_state["semi_rollcall_overrides"] = {}
        st.session_state["semi_enabled_actions"] = []
        st.session_state["semi_current_stage"] = "应变处置"


def add_log_entry(category: str, sender: str, content: str) -> None:
    if not content.strip():
        return
    entry = {
        "时间": datetime.now().strftime("%H:%M"),
        "类别": category,
        "发送方": sender.strip() or "值守席",
        "内容": content.strip(),
    }
    st.session_state["semi_command_log"] = [entry] + st.session_state["semi_command_log"]


def add_action_feed(title: str, detail: str) -> None:
    entry = {
        "时间": datetime.now().strftime("%H:%M"),
        "动作": title,
        "说明": detail,
    }
    st.session_state["semi_action_feed"] = [entry] + st.session_state["semi_action_feed"]


def trigger_command_action(action_key: str, title: str, detail: str, sender: str) -> None:
    enabled = list(st.session_state.get("semi_enabled_actions", []))
    if action_key not in enabled:
        enabled.append(action_key)
    st.session_state["semi_enabled_actions"] = enabled


def render_command_button(
    label: str,
    action_key: str,
    title: str,
    detail: str,
    sender: str,
    *,
    button_key: str,
    disabled: bool = False,
    rerun: bool = False,
) -> None:
    if st.button(label, key=button_key, use_container_width=True, disabled=disabled):
        trigger_command_action(action_key, title, detail, sender)
        if rerun:
            st.rerun()


def render_enabled_action_summary(enabled_actions: set[str]) -> None:
    if not enabled_actions:
        st.caption("当前还没有启用联动动作。")
        return

    chips = "".join(
        f'<div class="chip" style="background:rgba(90,167,255,0.14);border-color:rgba(90,167,255,0.18);">{ACTION_STATUS_LABELS.get(action_key, action_key)}</div>'
        for action_key in ACTION_STATUS_LABELS
        if action_key in enabled_actions
    )
    st.markdown(f'<div class="chip-row">{chips}</div>', unsafe_allow_html=True)


def set_active_stage(stage_name: str, sender: str) -> None:
    current_stage = str(st.session_state.get("semi_current_stage", "应变处置"))
    if stage_name == current_stage:
        return
    st.session_state["semi_current_stage"] = stage_name


def render_stage_action_bar(stage_order: list[str], active_stage: str, sender: str, *, allow_change: bool) -> None:
    st.markdown(
        """
        <div class="card-light" style="margin-bottom:1rem;">
          <div class="section-title">阶段控制</div>
          <div class="section-subtitle">顶部阶段按钮可直接切换到应变处置、事件管理或营运恢复，并同步刷新当前阶段状态。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    columns = st.columns(len(stage_order))
    for index, stage_name in enumerate(stage_order):
        with columns[index]:
            button_type = "primary" if stage_name == active_stage else "secondary"
            if st.button(
                stage_name,
                key=f"stage-bar-{stage_name}",
                use_container_width=True,
                type=button_type,
                disabled=not allow_change,
            ):
                set_active_stage(stage_name, sender)
                st.rerun()


def build_reference_search_index(
    photo_checklists: pd.DataFrame,
    photo_processes: dict[str, list[str]],
    reference_supplements: dict[str, list[str]],
) -> pd.DataFrame:
    records: list[dict[str, str]] = []

    for row in photo_checklists.itertuples(index=False):
        records.append(
            {
                "来源": "CheckList",
                "标题": str(row.预案),
                "分类": str(row.阶段),
                "内容": str(row.主要工作内容),
                "责任方": str(row.执行单位),
            }
        )

    for process_name, steps in photo_processes.items():
        for index, step in enumerate(steps, start=1):
            records.append(
                {
                    "来源": "处理流程",
                    "标题": str(process_name),
                    "分类": f"步骤 {index}",
                    "内容": str(step),
                    "责任方": "流程节点",
                }
            )

    for title, items in reference_supplements.items():
        for item in items:
            records.append(
                {
                    "来源": "参考补充",
                    "标题": str(title),
                    "分类": "参考项",
                    "内容": str(item),
                    "责任方": "参考资料",
                }
            )

    for chemical_name in ["氯气", "氨气", "氢氟酸", "盐酸蒸气", "硅烷", "异丙醇蒸气"]:
        profile = build_chemical_ghs_profile(chemical_name)
        ghs_sections = {
            "主要危害": profile["主要危害"],
            "关键 PPE": profile["关键PPE"],
            "现场禁忌": profile["现场禁忌"],
            "首要动作": profile["首要动作"],
        }
        for section, items in ghs_sections.items():
            for item in items:  # type: ignore[assignment]
                records.append(
                    {
                        "来源": "GHS",
                        "标题": chemical_name,
                        "分类": section,
                        "内容": str(item),
                        "责任方": str(profile["信号词"]),
                    }
                )

    return pd.DataFrame(records, columns=["来源", "标题", "分类", "内容", "责任方"])


def render_search_result_cards(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.info("没有匹配结果，请换一个关键字或放宽来源过滤。")
        return

    cards = []
    for row in frame.itertuples(index=False):
        cards.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.标题}</div>
                    <span class="signal-badge badge-slate">{row.来源}</span>
                  </div>
                  <div class="matrix-meta">{row.分类} · {row.责任方}</div>
                  <div style="font-size:0.9rem;font-weight:600;">{row.内容}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def get_effective_rollcall_board(base_board: pd.DataFrame) -> pd.DataFrame:
    updated = base_board.copy()
    overrides = st.session_state.get("semi_rollcall_overrides", {})
    for zone, payload in overrides.items():
        updated = apply_rollcall_override(
            updated,
            zone=zone,
            arrived=int(payload["arrived"]),
            medical_observe=int(payload["observe"]),
        )
    return updated


def apply_control_profile(profile: dict[str, str | int | float | bool], force: bool = False) -> None:
    assignments = {
        "control_incident_name": profile["incident_name"],
        "control_incident_area": profile["incident_area"],
        "control_shift_name": "夜班",
        "control_commander": profile["commander"],
        "control_severity": int(profile["severity"]),
        "control_exposed_people": int(profile["exposed_people"]),
        "control_inside_ratio": float(profile["inside_ratio"]),
        "control_tool_impact_count": int(profile["tool_impact_count"]),
        "control_toxic_gas_risk": float(profile["toxic_gas_risk"]),
        "control_contamination_risk": float(profile["contamination_risk"]),
        "control_utility_failure": float(profile["utility_failure"]),
        "control_cleanroom_recovery_progress": float(profile["cleanroom_recovery_progress"]),
        "control_mes_disrupted": bool(profile["mes_disrupted"]),
        "semi_aloha_chemical": profile["chemical_name"],
    }
    for key, value in assignments.items():
        if force or key not in st.session_state:
            st.session_state[key] = value


def init_control_panel_state(fab_name: str, incident_type: str, force: bool = False) -> dict[str, str | int | float | bool]:
    profile = build_incident_control_profile(incident_type=incident_type, fab_name=fab_name)
    seed = f"{fab_name}|{incident_type}"
    if force or st.session_state.get("semi_control_seed") != seed:
        st.session_state["semi_control_seed"] = seed
        apply_control_profile(profile, force=True)
    return profile


@st.cache_data(ttl=600, show_spinner=False)
def load_live_weather_snapshot(site_name: str, latitude: float, longitude: float) -> dict[str, str | float | None]:
    _ = site_name
    try:
        snapshot = fetch_live_weather_snapshot(latitude=latitude, longitude=longitude)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"实时气象同步失败：{exc}",
            "timestamp": None,
            "temperature_c": None,
            "humidity_pct": None,
            "wind_speed_ms": None,
            "wind_direction_deg": None,
            "wind_gust_ms": None,
        }
    snapshot["status"] = "ok"
    snapshot["message"] = "实时气象已同步"
    return snapshot


def format_metric(value: float | int | None, suffix: str = "", decimals: int = 0) -> str:
    if value is None:
        return "--"
    return f"{float(value):.{decimals}f}{suffix}"


def render_kpi_card(title: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">{title}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_tile(css_class: str, title: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="status-tile {css_class}">
          <div class="tile-title">{title}</div>
          <div class="tile-value">{value}</div>
          <div class="tile-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_head(title: str, subtitle: str, dark: bool = False) -> None:
    class_name = "section-head-dark" if dark else "section-head-light"
    subtitle_class = "dark-subtitle" if dark else "section-subtitle"
    st.markdown(
        f"""
        <div class="{class_name}">
          <div class="section-title">{title}</div>
          <div class="{subtitle_class}" style="margin-bottom:0;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_zone_chart(zone_frame: pd.DataFrame) -> go.Figure:
    colors = {
        "红色封控": "#ef4444",
        "橙色处置": "#f97316",
        "黄色监控": "#facc15",
        "绿色受控": "#22c55e",
    }
    fig = px.scatter(
        zone_frame,
        x="横轴",
        y="纵轴",
        size="风险指数",
        color="状态",
        color_discrete_map=colors,
        text="区域",
        hover_data={"风险指数": True, "人员密度": ":.0%", "恢复度": ":.0%", "横轴": False, "纵轴": False},
    )
    fig.update_traces(textposition="top center", marker={"opacity": 0.92, "line": {"width": 1.5, "color": "#ffffff"}})
    fig.update_layout(
        height=400,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis_title="厂区横向区域分布",
        yaxis_title="由外围到核心工艺纵深",
        legend_title="分区状态",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_resource_chart(resource_frame: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=resource_frame["资源类型"], y=resource_frame["已出动"], name="已出动", marker_color="#22d3ee"))
    fig.add_trace(go.Bar(x=resource_frame["资源类型"], y=resource_frame["待命"], name="待命", marker_color="#1d4ed8"))
    fig.update_layout(
        barmode="stack",
        height=360,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        yaxis_title="数量",
        xaxis_title="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_facility_chart(facility_frame: pd.DataFrame) -> go.Figure:
    chart = facility_frame.copy().sort_values("健康度")
    color_map = {"高风险": "#ef4444", "受扰": "#f59e0b", "可控": "#22c55e"}
    fig = px.bar(
        chart,
        x="健康度",
        y="系统",
        orientation="h",
        color="状态",
        color_discrete_map=color_map,
        text=chart["健康度"].map(lambda value: f"{value:.0%}"),
        hover_data={"当前读数": True, "控制阈值": True, "健康度": ":.0%"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=320,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis_title="系统健康度",
        yaxis_title="",
        legend_title="状态",
        xaxis_tickformat=".0%",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_wip_chart(wip_frame: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        wip_frame,
        x="工艺段",
        y="受影响批次",
        color="冻结状态",
        text="受影响批次",
        color_discrete_sequence=["#06b6d4", "#f59e0b", "#ef4444"],
    )
    fig.update_layout(
        height=320,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis_title="",
        yaxis_title="受影响批次",
        legend_title="冻结状态",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_gate_list(gate_frame: pd.DataFrame) -> str:
    lines: list[str] = []
    for row in gate_frame.itertuples(index=False):
        css = "gate-ok" if row.状态 == "已满足" else "gate-wait"
        lines.append(
            dedent(
                f"""
                <div class="gate-item">
                  <div>
                    <div style="font-weight:700;">{row.复产关卡}</div>
                    <div style="font-size:0.86rem;color:rgba(15,23,42,0.68);">{row.判定标准}</div>
                    <div style="font-size:0.82rem;color:rgba(15,23,42,0.54);margin-top:0.18rem;">责任方：{row.责任方}</div>
                  </div>
                  <div class="gate-status {css}">{row.状态}</div>
                </div>
                """
            ).strip()
        )
    return "".join(lines)


def render_timeline_list(timeline_frame: pd.DataFrame) -> str:
    blocks: list[str] = []
    for row in timeline_frame.itertuples(index=False):
        blocks.append(
            dedent(
                f"""
                <div class="timeline-item">
                  <div class="timeline-time">{row.时间节点}</div>
                  <div>
                    <div style="font-weight:700;">{row.主责团队}</div>
                    <div style="font-size:0.86rem;color:rgba(248,250,252,0.72);">{row.关键动作}</div>
                  </div>
                </div>
                """
            ).strip()
        )
    return "".join(blocks)


def render_timeline_panel(timeline_frame: pd.DataFrame) -> None:
    render_section_head("处置时间轴", "用固定时间节点压缩信息延迟，避免 EOC 进入无节奏状态。", dark=True)
    st.markdown(
        f'<div class="card-dark">{render_timeline_list(timeline_frame)}</div>',
        unsafe_allow_html=True,
    )


def render_process_steps(steps: list[str]) -> None:
    for index, step in enumerate(steps, start=1):
        st.markdown(f"{index}. {step}")


def render_ero_cloud(structure: dict[str, list[str]]) -> None:
    for group_name, roles in structure.items():
        st.markdown(f"**{group_name}**")
        pill_html = "".join(f'<span class="role-pill">{role}</span>' for role in roles)
        st.markdown(f'<div class="role-cloud">{pill_html}</div>', unsafe_allow_html=True)


def badge_class(text: str) -> str:
    if any(keyword in text for keyword in ["红", "高风险", "立即搜寻", "未满足", "失联", "报警"]):
        return "badge-red"
    if any(keyword in text for keyword in ["橙", "二次复核", "待", "受扰", "当前节点", "预警"]):
        return "badge-amber"
    if any(keyword in text for keyword in ["完成", "已满足", "可控", "已发布", "在线"]):
        return "badge-green"
    if any(keyword in text for keyword in ["执行中", "抢修中", "巡检中", "排查中"]):
        return "badge-cyan"
    return "badge-slate"


def render_command_cards(frame: pd.DataFrame) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        cards.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div class="matrix-title">{row.职能}</div>
                  <div class="matrix-meta">负责人：{row.负责人}</div>
                  <div style="font-size:0.9rem;font-weight:600;margin-bottom:0.25rem;">{row.当前重点}</div>
                  <div style="font-size:0.84rem;color:rgba(15,23,42,0.58);">部署位置：{row.部署位置}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_task_lanes(frame: pd.DataFrame) -> None:
    for priority in ["高", "中"]:
        subset = frame[frame["优先级"] == priority]
        if subset.empty:
            continue
        render_section_head(f"{priority}优先任务", "按任务状态编排，方便指挥席滚动追踪。")
        lanes = []
        for row in subset.itertuples(index=False):
            lanes.append(
                dedent(
                    f"""
                    <div class="lane-card">
                      <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                        <div class="matrix-title">{row.职能}</div>
                        <span class="signal-badge {badge_class(row.状态)}">{row.状态}</span>
                      </div>
                      <div style="font-size:0.9rem;font-weight:600;margin:0.35rem 0 0.4rem;">{row.任务}</div>
                      <div class="matrix-meta">时限：{row.时限}</div>
                    </div>
                    """
                ).strip()
            )
        st.markdown(f'<div class="lane-grid">{"".join(lanes)}</div>', unsafe_allow_html=True)


def render_wip_cards(frame: pd.DataFrame) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        cards.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.工艺段}</div>
                    <span class="signal-badge {badge_class(row.冻结状态)}">{row.冻结状态}</span>
                  </div>
                  <div class="matrix-meta">关键产品：{row.关键产品}</div>
                  <div style="font-size:1.6rem;font-weight:700;line-height:1;">{row.受影响批次}</div>
                  <div style="font-size:0.82rem;color:rgba(15,23,42,0.55);margin-bottom:0.35rem;">受影响批次</div>
                  <div style="font-size:0.88rem;font-weight:600;">当前约束：{row.当前约束}</div>
                  <div style="font-size:0.84rem;color:rgba(15,23,42,0.58);margin-top:0.3rem;">释放条件：{row.释放条件}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_resource_cards(frame: pd.DataFrame) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        fill_color = "#22c55e" if row.到位率 >= 0.9 else "#f59e0b" if row.到位率 >= 0.7 else "#ef4444"
        cards.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.资源类型}</div>
                    <span class="signal-badge {badge_class('已满足' if row.缺口 == 0 else '未满足')}">缺口 {row.缺口}</span>
                  </div>
                  <div class="progress-track"><div class="progress-fill" style="width:{row.到位率:.0%};background:{fill_color};"></div></div>
                  <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0.4rem;font-size:0.84rem;margin-top:0.3rem;">
                    <div><div class="matrix-meta">已到位</div><div style="font-weight:700;">{row.已到位}</div></div>
                    <div><div class="matrix-meta">已出动</div><div style="font-weight:700;">{row.已出动}</div></div>
                    <div><div class="matrix-meta">待命</div><div style="font-weight:700;">{row.待命}</div></div>
                    <div><div class="matrix-meta">需求</div><div style="font-weight:700;">{row.预测需求}</div></div>
                  </div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_zone_cards(frame: pd.DataFrame) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        cards.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.区域}</div>
                    <span class="signal-badge {badge_class(row.状态)}">{row.状态}</span>
                  </div>
                  <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0.4rem;margin-top:0.35rem;">
                    <div><div class="matrix-meta">风险指数</div><div style="font-weight:700;">{row.风险指数}</div></div>
                    <div><div class="matrix-meta">人员密度</div><div style="font-weight:700;">{row.人员密度:.0%}</div></div>
                    <div><div class="matrix-meta">恢复度</div><div style="font-weight:700;">{row.恢复度:.0%}</div></div>
                  </div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="zone-stack">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_facility_cards(frame: pd.DataFrame, dark: bool = False) -> None:
    cards = []
    dark_class = " dark" if dark else ""
    for row in frame.itertuples(index=False):
        fill_color = "#22c55e" if row.健康度 >= 0.8 else "#f59e0b" if row.健康度 >= 0.55 else "#ef4444"
        cards.append(
            dedent(
                f"""
                <div class="matrix-card{dark_class}">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.系统}</div>
                    <span class="signal-badge {badge_class(row.状态)}">{row.状态}</span>
                  </div>
                  <div class="progress-track"><div class="progress-fill" style="width:{row.健康度:.0%};background:{fill_color};"></div></div>
                  <div class="matrix-meta">当前读数：{row.当前读数}</div>
                  <div style="font-size:0.85rem;font-weight:600;">控制阈值：{row.控制阈值}</div>
                  <div style="font-size:0.83rem;margin-top:0.35rem;opacity:0.82;">{row.处置说明}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_checklist_stage_cards(frame: pd.DataFrame) -> None:
    blocks = []
    for stage, stage_frame in frame.groupby("阶段", sort=False):
        items = []
        for row in stage_frame.itertuples(index=False):
            items.append(
                dedent(
                    f"""
                    <div class="check-item">
                      <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                        <div style="font-size:0.9rem;font-weight:600;">{row.主要工作内容}</div>
                        <span class="signal-badge badge-slate">{row.执行单位}</span>
                      </div>
                    </div>
                    """
                ).strip()
            )
        blocks.append(
            dedent(
                f"""
                <div class="stage-card">
                  <div class="matrix-title">{stage}</div>
                  {''.join(items)}
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="checklist-stack">{"".join(blocks)}</div>', unsafe_allow_html=True)


def render_log_stream(frame: pd.DataFrame) -> None:
    blocks = []
    for row in frame.itertuples(index=False):
        blocks.append(
            dedent(
                f"""
                <div class="feed-item">
                  <div class="feed-time">{row.时间} · {row.类别}</div>
                  <div style="font-size:0.92rem;font-weight:700;">{row.发送方}</div>
                  <div style="font-size:0.9rem;margin-top:0.22rem;">{row.内容}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="stage-card">{"".join(blocks)}</div>', unsafe_allow_html=True)


def render_rollcall_cards(frame: pd.DataFrame) -> None:
    for zone_type in ["洁净室内", "室外"]:
        subset = frame[frame["类型"] == zone_type]
        if subset.empty:
            continue
        render_section_head(zone_type + "点名", "以应到、已到、失联和医疗观察四个口径滚动更新。")
        cards = []
        for row in subset.itertuples(index=False):
            fill_color = "#22c55e" if row.到位率 >= 0.95 else "#f59e0b" if row.到位率 >= 0.85 else "#ef4444"
            cards.append(
                dedent(
                    f"""
                    <div class="matrix-card">
                      <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                        <div class="matrix-title">{row.区域}</div>
                        <span class="signal-badge {badge_class(row.状态)}">{row.状态}</span>
                      </div>
                      <div class="progress-track"><div class="progress-fill" style="width:{row.到位率:.0%};background:{fill_color};"></div></div>
                      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0.4rem;">
                        <div><div class="matrix-meta">应到</div><div style="font-weight:700;">{row.应到}</div></div>
                        <div><div class="matrix-meta">已到</div><div style="font-weight:700;">{row.已到}</div></div>
                        <div><div class="matrix-meta">失联</div><div style="font-weight:700;">{row.失联}</div></div>
                        <div><div class="matrix-meta">观察</div><div style="font-weight:700;">{row.医疗观察}</div></div>
                      </div>
                      <div style="font-size:0.84rem;color:rgba(15,23,42,0.62);margin-top:0.45rem;">下一动作：{row.下一动作}</div>
                    </div>
                    """
                ).strip()
            )
        st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_bcm_stage_cards(frame: pd.DataFrame, active_stage: str) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        active_badge = "当前阶段" if row.阶段 == active_stage else row.状态
        cards.append(
            dedent(
                f"""
                <div class="matrix-card{' dark' if row.阶段 == active_stage else ''}">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.阶段}</div>
                    <span class="signal-badge {badge_class(active_badge)}">{active_badge}</span>
                  </div>
                  <div class="matrix-meta">时间尺度：{row.时间尺度}</div>
                  <div style="font-size:0.9rem;font-weight:600;margin-bottom:0.3rem;">{row.阶段目标}</div>
                  <div style="font-size:0.84rem;color:rgba(15,23,42,0.62);">当前动作：{row.当前动作}</div>
                  <div style="font-size:0.84rem;color:rgba(15,23,42,0.58);margin-top:0.3rem;">主责团队：{row.主责团队}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_support_cards(frame: pd.DataFrame) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        cards.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.支援模块}</div>
                    <span class="signal-badge {badge_class(row.状态)}">{row.状态}</span>
                  </div>
                  <div class="matrix-meta">模式：{row.模式}</div>
                  <div style="font-size:0.88rem;">{row.说明}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_audit_cards(frame: pd.DataFrame) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        cards.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.核对来源}</div>
                    <span class="signal-badge {badge_class(row.状态)}">{row.状态}</span>
                  </div>
                  <div class="matrix-meta">覆盖范围：{row.覆盖范围}</div>
                  <div style="font-size:0.88rem;">{row.说明}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_reference_cards(reference_data: dict[str, list[str]]) -> None:
    blocks = []
    for title, items in reference_data.items():
        bullet_html = "".join(
            dedent(
                f"""
                <div class="check-item">
                  <div style="font-size:0.9rem;font-weight:600;">{item}</div>
                </div>
                """
            ).strip()
            for item in items
        )
        blocks.append(
            dedent(
                f"""
                <div class="stage-card">
                  <div class="matrix-title">{title}</div>
                  {bullet_html}
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="checklist-stack">{"".join(blocks)}</div>', unsafe_allow_html=True)


def render_sop_execution_cards(frame: pd.DataFrame) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        cards.append(
            dedent(
                f"""
                <div class="matrix-card{' dark' if row.状态 == '当前节点' else ''}">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">Step {row.顺序} · {row.阶段}</div>
                    <span class="signal-badge {badge_class(row.状态)}">{row.状态}</span>
                  </div>
                  <div class="matrix-meta">执行单位：{row.执行单位}</div>
                  <div style="font-size:0.9rem;font-weight:600;">{row.关键动作}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="checklist-stack">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_monitoring_interface_cards(frame: pd.DataFrame) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        cards.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.系统}</div>
                    <span class="signal-badge {badge_class(row.运行状态)}">{row.运行状态}</span>
                  </div>
                  <div class="matrix-meta">接口状态：{row.接口状态}</div>
                  <div style="font-size:0.9rem;font-weight:600;margin-bottom:0.3rem;">报警位置：{row.报警位置}</div>
                  <div style="font-size:0.84rem;color:rgba(15,23,42,0.62);">{row.说明}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_gms_cards(frame: pd.DataFrame) -> None:
    cards = []
    for row in frame.itertuples(index=False):
        cards.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.点位}</div>
                    <span class="signal-badge {badge_class(row.状态)}">{row.状态}</span>
                  </div>
                  <div class="matrix-meta">气体：{row.气体}</div>
                  <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.5rem;margin-bottom:0.35rem;">
                    <div><div class="matrix-meta">读值</div><div style="font-weight:700;">{row.读值:.2f} ppm</div></div>
                    <div><div class="matrix-meta">报警阈值</div><div style="font-weight:700;">{row.报警阈值}</div></div>
                  </div>
                  <div style="font-size:0.84rem;color:rgba(15,23,42,0.62);">报警位置：{row.报警位置}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_weather_snapshot_cards(
    snapshot: dict[str, str | float | None],
    site_name: str,
    site_area: str,
    wind_direction_label: str,
) -> None:
    cards = [
        ("气温", format_metric(snapshot.get("temperature_c"), " °C", 1), f"{site_name} | {site_area}"),
        ("相对湿度", format_metric(snapshot.get("humidity_pct"), " %", 0), "实时气象同步参考"),
        ("平均风速", format_metric(snapshot.get("wind_speed_ms"), " m/s", 1), f"风向：{wind_direction_label}"),
        ("阵风", format_metric(snapshot.get("wind_gust_ms"), " m/s", 1), "用于判断下风向警戒区扩大趋势"),
    ]
    blocks = []
    for title, value, note in cards:
        blocks.append(
            dedent(
                f"""
                <div class="matrix-card">
                  <div class="kpi-label">{title}</div>
                  <div class="kpi-value">{value}</div>
                  <div class="weather-note">{note}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="matrix-grid">{"".join(blocks)}</div>', unsafe_allow_html=True)


def render_aloha_zone_chart(zone_frame: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        zone_frame,
        x="半径米",
        y="区域",
        orientation="h",
        color="区域",
        text="半径米",
        color_discrete_map={"红区": "#ef4444", "橙区": "#f97316", "黄区": "#eab308"},
        hover_data={"说明": True, "行动建议": True, "半径米": True},
    )
    fig.update_layout(
        height=280,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis_title="建议警戒半径（米）",
        yaxis_title="",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_aloha_zone_cards(zone_frame: pd.DataFrame) -> None:
    style_map = {"红区": "aloha-red", "橙区": "aloha-orange", "黄区": "aloha-yellow"}
    blocks = []
    for row in zone_frame.itertuples(index=False):
        blocks.append(
            dedent(
                f"""
                <div class="aloha-zone-card {style_map.get(row.区域, 'aloha-orange')}">
                  <div class="matrix-title">{row.区域}</div>
                  <div style="font-size:2rem;font-weight:700;line-height:1.05;margin:0.25rem 0;">{row.半径米} m</div>
                  <div style="font-size:0.92rem;font-weight:600;margin-bottom:0.35rem;">{row.说明}</div>
                  <div style="font-size:0.84rem;opacity:0.86;">{row.行动建议}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="aloha-zone-grid">{"".join(blocks)}</div>', unsafe_allow_html=True)


def render_ghs_profile(profile: dict[str, str | list[str]], chemical_name: str) -> None:
    pictograms = " / ".join(profile["GHS图示"])  # type: ignore[index]
    st.markdown(
        f"""
        <div class="card-light">
          <div class="section-title">{chemical_name} GHS 参考</div>
          <div class="section-subtitle">用于 ERC 快速判读，正式分类与处置仍应以 SDS、厂内化学品台账和 EHS 指示为准。</div>
          <div class="chip-row" style="margin-top:0.2rem;margin-bottom:0.8rem;">
            <div class="chip" style="background:rgba(239,68,68,0.10);border-color:rgba(239,68,68,0.18);color:#991b1b;">信号词：{profile['信号词']}</div>
            <div class="chip" style="background:rgba(15,23,42,0.05);border-color:rgba(15,23,42,0.10);color:#0f172a;">图示：{pictograms}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    info_cols = st.columns(2)
    sections = [
        ("主要危害", profile["主要危害"]),
        ("关键 PPE", profile["关键PPE"]),
        ("现场禁忌", profile["现场禁忌"]),
        ("首要动作", profile["首要动作"]),
    ]
    for index, (title, items) in enumerate(sections):
        with info_cols[index % 2]:
            bullets = "".join(
                f'<div class="check-item"><div style="font-size:0.9rem;font-weight:600;">{item}</div></div>'
                for item in items  # type: ignore[arg-type]
            )
            st.markdown(
                f'<div class="stage-card"><div class="matrix-title">{title}</div>{bullets}</div>',
                unsafe_allow_html=True,
            )


def render_action_stream(feed: list[dict[str, str]]) -> None:
    if not feed:
        st.caption("还没有执行过指挥动作。")
        return
    blocks = []
    for item in feed[:8]:
        blocks.append(
            dedent(
                f"""
                <div class="feed-item">
                  <div class="feed-time">{item['时间']}</div>
                  <div style="font-size:0.92rem;font-weight:700;">{item['动作']}</div>
                  <div style="font-size:0.88rem;margin-top:0.2rem;">{item['说明']}</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f'<div class="stage-card">{"".join(blocks)}</div>', unsafe_allow_html=True)


def render_event_ticker(items: list[dict[str, str | bool]]) -> None:
    if not items:
        return
    ticker_blocks = []
    for item in items:
        is_new = bool(item.get("is_new", False))
        new_pill = '<span class="ticker-pill-new">最新</span>' if is_new else ""
        css_class = "ticker-item ticker-item-new" if is_new else "ticker-item"
        ticker_blocks.append(
            f'<span class="{css_class}"><span class="ticker-dot"></span>{new_pill}{item["text"]}</span>'
        )
    ticker_items = "".join(ticker_blocks)
    st.markdown(
        f'<div class="ticker-shell"><div class="ticker-track">{ticker_items}{ticker_items}</div></div>',
        unsafe_allow_html=True,
    )


def render_alert_cards(alerts: pd.DataFrame, *, allow_ack: bool) -> None:
    acked = set(st.session_state.get("semi_ack_alerts", []))
    visible = alerts[~alerts["告警ID"].isin(acked)]
    if visible.empty:
        st.success("当前没有待确认告警。")
        return
    for row in visible.itertuples(index=False):
        col1, col2 = st.columns([0.82, 0.18])
        with col1:
            st.markdown(
                f"""
                <div class="stage-card">
                  <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
                    <div class="matrix-title">{row.标题}</div>
                    <span class="signal-badge {badge_class(row.优先级 if row.优先级 == 'P1' else '待处理')}">{row.优先级}</span>
                  </div>
                  <div class="matrix-meta">责任方：{row.责任方}</div>
                  <div style="font-size:0.88rem;">{row.建议动作}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("确认", key=f"ack-{row.告警ID}", use_container_width=True, disabled=not allow_ack):
                acked.add(row.告警ID)
                st.session_state["semi_ack_alerts"] = sorted(acked)
                st.rerun()


def init_auth_state() -> None:
    if "semi_authenticated_user" not in st.session_state:
        st.session_state["semi_authenticated_user"] = None


def render_login_gate() -> tuple[list[dict[str, str | bool]], dict[str, str | bool]]:
    init_auth_state()
    accounts = load_user_accounts(USER_ACCOUNTS_PATH)
    current_user = st.session_state.get("semi_authenticated_user")
    if current_user:
        normalized = str(current_user["username"]).lower()
        refreshed_user = next(
            (
                account
                for account in accounts
                if str(account["username"]).lower() == normalized and bool(account["active"])
            ),
            None,
        )
        if refreshed_user:
            st.session_state["semi_authenticated_user"] = refreshed_user
            return accounts, refreshed_user
        st.session_state["semi_authenticated_user"] = None

    st.markdown(
        """
        <div class="hero">
          <div class="hero-kicker">Single Account Access</div>
          <div class="hero-title">半导体应急指挥系统登录</div>
          <div class="hero-subtitle">系统当前使用单账号登录。请先输入授权账号和密码，再进入指挥席、点名、ALOHA 和通信模块。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    login_left, login_right = st.columns([0.72, 0.28])
    with login_left:
        st.markdown(
            """
            <div class="card-light">
              <div class="section-title">登录</div>
              <div class="section-subtitle">当前系统只保留一个授权账号，页面不会展示账号密码。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("semi-login"):
            username = st.text_input("账号")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录", use_container_width=True)
            if submitted:
                matched_user = authenticate_user(accounts, username=username, password=password)
                if matched_user:
                    st.session_state["semi_authenticated_user"] = matched_user
                    st.rerun()
                st.error("账号或密码不正确，或该账号已被停用。")
    with login_right:
        st.markdown(
            """
            <div class="stage-card">
              <div class="matrix-title">访问说明</div>
              <div class="check-item"><strong>访问方式：</strong>请使用已分配的系统账号登录。</div>
              <div class="check-item"><strong>账号申请：</strong>如需新增、停用或重置账号，请联系系统管理员。</div>
              <div class="check-item"><strong>安全提醒：</strong>页面不再展示默认账号和密码。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()


def render_user_management_panel(
    accounts: list[dict[str, str | bool]],
    current_user: dict[str, str | bool],
) -> list[dict[str, str | bool]]:
    return accounts


user_accounts, authenticated_user = render_login_gate()
current_role = str(authenticated_user["role"])
current_permissions = set(get_role_permissions(current_role))
can_edit_scene = "场景配置" in current_permissions
can_run_commands = "指挥动作" in current_permissions
can_edit_rollcall = "点名修正" in current_permissions
can_write_logs = "通信记录" in current_permissions
can_use_aloha = "ALOHA工作台" in current_permissions


with st.sidebar:
    permission_chips = "".join(f'<span class="sidebar-chip">{permission}</span>' for permission in current_permissions)
    st.markdown(
        f"""
        <div class="sidebar-panel">
          <div class="sidebar-heading">当前登录用户</div>
          <div class="sidebar-title">{authenticated_user["display_name"]}</div>
          <div class="sidebar-note">账号：{authenticated_user["username"]}</div>
          <div class="sidebar-note">角色：{current_role}</div>
          <div class="sidebar-chip-row">{permission_chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("退出登录", use_container_width=True):
        st.session_state["semi_authenticated_user"] = None
        st.rerun()

    taiwan_fab_sites = get_taiwan_fab_sites()
    fab_name = st.selectbox("应变厂区", list(taiwan_fab_sites.keys()), index=2, disabled=not can_edit_scene)
    site_profile = taiwan_fab_sites[fab_name]
    incident_type = st.selectbox("事故类型", SEMICONDUCTOR_INCIDENT_TYPES, index=0, disabled=not can_edit_scene)
    profile = init_control_panel_state(fab_name=fab_name, incident_type=incident_type)
    mapped_checklist = get_checklist_name_for_incident(incident_type)
    mapped_process = get_process_name_for_incident(incident_type)
    st.markdown(
        f"""
        <div class="sidebar-panel">
          <div class="sidebar-heading">应变控制台</div>
          <div class="sidebar-title">{fab_name}</div>
          <div class="sidebar-note">当前事故类型会自动联动预案、流程、人数、风险强度和 ALOHA 化学品，不再是彼此分离的输入项。</div>
          <div class="sidebar-chip-row">
            <span class="sidebar-chip">{incident_type}</span>
            <span class="sidebar-chip">{mapped_checklist}</span>
            <span class="sidebar-chip">{mapped_process}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("重载当前场景模板", use_container_width=True, disabled=not can_edit_scene):
        profile = init_control_panel_state(fab_name=fab_name, incident_type=incident_type, force=True)
        st.rerun()

    st.markdown('<div class="sidebar-heading">指挥信息</div>', unsafe_allow_html=True)
    incident_name = st.text_input("事件名称", key="control_incident_name", disabled=not can_edit_scene)
    incident_area = st.text_input("事故区域", key="control_incident_area", disabled=not can_edit_scene)
    shift_name = st.selectbox("值班班次", ["白班", "中班", "夜班"], key="control_shift_name", disabled=not can_edit_scene)
    commander = st.text_input("值守总指挥", key="control_commander", disabled=not can_edit_scene)

    st.markdown('<div class="sidebar-heading">人员与点名</div>', unsafe_allow_html=True)
    exposed_people = int(
        st.number_input("涉险人数", min_value=0, step=8, key="control_exposed_people", disabled=not can_edit_scene)
    )
    inside_ratio = float(
        st.slider(
            "洁净室内点名占比",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            key="control_inside_ratio",
            disabled=not can_edit_scene,
        )
    )
    cleanroom_inside_due = int(round(exposed_people * inside_ratio))
    outdoor_assembly_due = max(0, int(exposed_people) - int(cleanroom_inside_due))
    st.markdown(
        f"""
        <div class="sidebar-panel">
          <div class="sidebar-heading">点名口径联动</div>
          <div class="sidebar-note">涉险人数会自动拆成洁净室内和室外集合点两条口径，避免控制台和页面内容对不上。</div>
          <div class="sidebar-stat-grid">
            <div class="sidebar-stat">
              <div class="sidebar-stat-label">洁净室内</div>
              <div class="sidebar-stat-value">{cleanroom_inside_due} 人</div>
            </div>
            <div class="sidebar-stat">
              <div class="sidebar-stat-label">室外集合点</div>
              <div class="sidebar-stat-value">{outdoor_assembly_due} 人</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="sidebar-panel">
          <div class="sidebar-heading">SOP 联动</div>
          <div class="sidebar-note">当前控制台已绑定：</div>
          <div class="sidebar-stat-grid">
            <div class="sidebar-stat">
              <div class="sidebar-stat-label">预案</div>
              <div class="sidebar-stat-value">{mapped_checklist}</div>
            </div>
            <div class="sidebar-stat">
              <div class="sidebar-stat-label">流程</div>
              <div class="sidebar-stat-value">{mapped_process}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("高级场景参数", expanded=False):
        severity = int(st.slider("事故严重度", min_value=1, max_value=5, key="control_severity", disabled=not can_edit_scene))
        tool_impact_count = int(
            st.slider("受影响机台数", min_value=0, max_value=80, key="control_tool_impact_count", disabled=not can_edit_scene)
        )
        toxic_gas_risk = float(
            st.slider("毒气风险", min_value=0.0, max_value=1.0, step=0.05, key="control_toxic_gas_risk", disabled=not can_edit_scene)
        )
        contamination_risk = float(
            st.slider(
                "洁净污染风险",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                key="control_contamination_risk",
                disabled=not can_edit_scene,
            )
        )
        utility_failure = float(
            st.slider(
                "厂务异常程度",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                key="control_utility_failure",
                disabled=not can_edit_scene,
            )
        )
        cleanroom_recovery_progress = float(
            st.slider(
                "洁净恢复进度",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                key="control_cleanroom_recovery_progress",
                disabled=not can_edit_scene,
            )
        )
        mes_disrupted = st.toggle("MES/告警链路受扰", key="control_mes_disrupted", disabled=not can_edit_scene)

    if "control_severity" not in st.session_state:
        apply_control_profile(profile)
    severity = int(st.session_state["control_severity"])
    tool_impact_count = int(st.session_state["control_tool_impact_count"])
    toxic_gas_risk = float(st.session_state["control_toxic_gas_risk"])
    contamination_risk = float(st.session_state["control_contamination_risk"])
    utility_failure = float(st.session_state["control_utility_failure"])
    cleanroom_recovery_progress = float(st.session_state["control_cleanroom_recovery_progress"])
    mes_disrupted = bool(st.session_state["control_mes_disrupted"])

    st.markdown(
        f"""
        <div class="sidebar-panel">
          <div class="sidebar-heading">系统状态</div>
          <div class="sidebar-note">厂区位置：{site_profile['area']}</div>
          <div class="sidebar-note">MES/告警链路：{'受扰' if mes_disrupted else '在线'}</div>
          <div class="sidebar-note">实时气象、SOP 路径和页面主态势已统一跟随当前厂区。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    auto_refresh = st.toggle("自动刷新", value=False)
    if auto_refresh:
        st_autorefresh(interval=20_000, key="semi-refresh")
    st_autorefresh(interval=12_000, key="semi-live-events-refresh")
    user_accounts = render_user_management_panel(user_accounts, authenticated_user)


score = calculate_semiconductor_risk_score(
    severity=severity,
    exposed_people=int(exposed_people),
    toxic_gas_risk=toxic_gas_risk,
    contamination_risk=contamination_risk,
    utility_failure=utility_failure,
    tool_impact_count=tool_impact_count,
    mes_disrupted=mes_disrupted,
)
level = classify_semiconductor_response_level(score)
command_roster = build_semiconductor_command_roster(commander=commander, fab_name=fab_name)
resource_board = build_semiconductor_resource_board(
    level=level,
    toxic_gas_risk=toxic_gas_risk,
    utility_failure=utility_failure,
    tool_impact_count=tool_impact_count,
)
task_board = build_semiconductor_task_board(
    incident_type=incident_type,
    level=level,
    cleanroom_recovery_progress=cleanroom_recovery_progress,
)
zone_status = build_semiconductor_zone_status(
    incident_type=incident_type,
    toxic_gas_risk=toxic_gas_risk,
    contamination_risk=contamination_risk,
    utility_failure=utility_failure,
    cleanroom_recovery_progress=cleanroom_recovery_progress,
)
objectives = build_semiconductor_objectives(
    incident_type=incident_type,
    level=level,
    contamination_risk=contamination_risk,
    mes_disrupted=mes_disrupted,
)
facility_status = build_semiconductor_facility_status(
    toxic_gas_risk=toxic_gas_risk,
    contamination_risk=contamination_risk,
    utility_failure=utility_failure,
    mes_disrupted=mes_disrupted,
)
wip_board = build_semiconductor_wip_board(
    incident_type=incident_type,
    tool_impact_count=tool_impact_count,
    cleanroom_recovery_progress=cleanroom_recovery_progress,
    mes_disrupted=mes_disrupted,
)
recovery_checklist = build_semiconductor_recovery_checklist(
    incident_type=incident_type,
    contamination_risk=contamination_risk,
    utility_failure=utility_failure,
    mes_disrupted=mes_disrupted,
    cleanroom_recovery_progress=cleanroom_recovery_progress,
)
timeline = build_semiconductor_timeline(level=level, incident_type=incident_type)
photo_checklists = build_photo_checklist_library()
photo_processes = build_photo_process_library()
photo_ero_structure = build_photo_ero_structure()
reference_supplements = build_reference_supplements()
live_weather = load_live_weather_snapshot(
    fab_name,
    float(site_profile["lat"]),
    float(site_profile["lon"]),
)
weather_online = live_weather.get("status") == "ok"
wind_direction_label = describe_wind_direction(live_weather.get("wind_direction_deg"))  # type: ignore[arg-type]
live_wind_speed = float(live_weather["wind_speed_ms"]) if live_weather.get("wind_speed_ms") is not None else 3.2
live_temperature = float(live_weather["temperature_c"]) if live_weather.get("temperature_c") is not None else 28.0
live_humidity = float(live_weather["humidity_pct"]) if live_weather.get("humidity_pct") is not None else 70.0
active_chemical_name = str(st.session_state.get("semi_aloha_chemical", profile["chemical_name"]))
upwind_hint = "优先保持上风侧集合点、下风侧交通与门禁管制。"
if weather_online and wind_direction_label != "未知":
    upwind_hint = f"当前厂区风向为{wind_direction_label}风，建议室外集合点优先布设在上风侧。"
base_rollcall_board = build_semiconductor_rollcall_board(
    cleanroom_inside_due=int(cleanroom_inside_due),
    outdoor_assembly_due=int(outdoor_assembly_due),
    toxic_gas_risk=toxic_gas_risk,
    contamination_risk=contamination_risk,
)
interaction_seed = f"{fab_name}|{incident_type}|{commander}|{incident_area}"
init_interaction_state(interaction_seed)
rollcall_board = get_effective_rollcall_board(base_rollcall_board)
resource_gap = int(resource_board["缺口"].sum())
rollcall_missing = int(rollcall_board["失联"].sum())
bcm_stage_board = build_taiwan_bcm_stage_board(
    incident_type=incident_type,
    level=level,
    cleanroom_recovery_progress=cleanroom_recovery_progress,
    mes_disrupted=mes_disrupted,
)
cross_fab_support_board = build_cross_fab_support_board(
    fab_name=fab_name,
    level=level,
    resource_gap=resource_gap,
    rollcall_missing=rollcall_missing,
    tool_impact_count=tool_impact_count,
)
badge_audit_board = build_badge_audit_board(
    cleanroom_inside_due=int(cleanroom_inside_due),
    outdoor_assembly_due=int(outdoor_assembly_due),
    rollcall_missing=rollcall_missing,
    mes_disrupted=mes_disrupted,
)
sop_execution_board = build_sop_execution_board(
    incident_type=incident_type,
    level=level,
    toxic_gas_risk=toxic_gas_risk,
    contamination_risk=contamination_risk,
    utility_failure=utility_failure,
    cleanroom_recovery_progress=cleanroom_recovery_progress,
)
monitoring_interface_board = build_monitoring_interface_board(
    fab_name=fab_name,
    incident_type=incident_type,
    incident_area=incident_area,
    chemical_name=active_chemical_name,
    toxic_gas_risk=toxic_gas_risk,
    utility_failure=utility_failure,
)
gms_sensor_board = build_gms_sensor_board(
    incident_type=incident_type,
    incident_area=incident_area,
    chemical_name=active_chemical_name,
    toxic_gas_risk=toxic_gas_risk,
)
alert_board = build_semiconductor_alert_board(
    level=level,
    toxic_gas_risk=toxic_gas_risk,
    contamination_risk=contamination_risk,
    resource_gap=resource_gap,
    rollcall_missing=rollcall_missing,
    mes_disrupted=mes_disrupted,
)
if weather_online and toxic_gas_risk >= 0.65:
    live_alert = pd.DataFrame(
        [
            (
                "live_weather",
                "实时风场已同步",
                "P2",
                "EHS应变组",
                f"{fab_name} 当前 {wind_direction_label}风 {live_wind_speed:.1f} m/s，建议立即校正下风向封控与集合点布置。",
            )
        ],
        columns=["告警ID", "标题", "优先级", "责任方", "建议动作"],
    )
    alert_board = pd.concat([live_alert, alert_board], ignore_index=True)
enabled_actions = set(st.session_state.get("semi_enabled_actions", []))
if "cross_fab_cctv" in enabled_actions:
    cross_fab_support_board.loc[cross_fab_support_board["支援模块"] == "台湾跨厂 CCTV", "状态"] = "已启用"
if "external_support" in enabled_actions:
    cross_fab_support_board.loc[cross_fab_support_board["支援模块"] == "跨厂 ERT 支援", "状态"] = "已请求"
if "wip_lock" in enabled_actions:
    cross_fab_support_board.loc[cross_fab_support_board["支援模块"] == "产能重分配", "状态"] = "评估中"
if "aloha" in enabled_actions:
    alert_board = alert_board[alert_board["告警ID"] != "gas_zone"].reset_index(drop=True)
if "rollcall_update" in enabled_actions and rollcall_missing == 0:
    alert_board = alert_board[alert_board["告警ID"] != "rollcall_gap"].reset_index(drop=True)
if "broadcast" in enabled_actions:
    monitoring_interface_board.loc[monitoring_interface_board["系统"] == "厂广播", "运行状态"] = "播报中"
if "cross_fab_cctv" in enabled_actions:
    monitoring_interface_board.loc[monitoring_interface_board["系统"] == "CCTV", "运行状态"] = "跨厂共享"
if "gms_recheck" in enabled_actions:
    monitoring_interface_board.loc[monitoring_interface_board["系统"] == "GMS", "运行状态"] = "复测中"
    gms_sensor_board["状态"] = ["复测中", *gms_sensor_board["状态"].tolist()[1:]]
if "fire_linkage" in enabled_actions:
    monitoring_interface_board.loc[monitoring_interface_board["系统"] == "火警报警", "运行状态"] = "联动中"
if "rollcall_muster" in enabled_actions:
    monitoring_interface_board.loc[monitoring_interface_board["系统"] == "门禁 / 点名", "运行状态"] = "二次点名"
if "facility_isolation" in enabled_actions:
    task_board.loc[task_board["职能"] == "厂务保障组", "状态"] = "隔离中"
    facility_status.loc[facility_status["系统"] == "UPW/CDA/真空", "处置说明"] = "已执行厂务隔离，按风险区逐段恢复关键公辅"
if "incident_briefing" in enabled_actions:
    task_board.loc[task_board["职能"] == "生产连续性组", "状态"] = "已通报"

triggered_items: list[dict[str, str | bool]] = []
triggered_items.extend(
    [{"text": f"{row.标题}：{row.建议动作}", "is_new": index < 2} for index, row in enumerate(alert_board.head(4).itertuples(index=False))]
)
triggered_items.extend(
    [
        {"text": f"GMS {row.点位} {row.读值:.2f} ppm @ {row.报警位置}", "is_new": index == 0}
        for index, row in enumerate(gms_sensor_board.head(2).itertuples(index=False))
    ]
)
if not triggered_items:
    triggered_items = [{"text": "当前事件已触发：系统监看中，等待新的告警或 GMS 变化。", "is_new": True}]

init_log_state(level=level, incident_type=incident_type, commander=commander, fab_name=fab_name)

affected_lots = int(wip_board["受影响批次"].sum())
system_health = facility_status["健康度"].mean()
open_gates = int((recovery_checklist["状态"] == "未满足").sum())
critical_zones = int(zone_status["状态"].isin(["红色封控", "橙色处置"]).sum())
high_priority_tasks = int((task_board["优先级"] == "高").sum())
rollcall_inside_rate = (
    0.0
    if rollcall_board[rollcall_board["类型"] == "洁净室内"]["应到"].sum() == 0
    else rollcall_board[rollcall_board["类型"] == "洁净室内"]["已到"].sum()
    / rollcall_board[rollcall_board["类型"] == "洁净室内"]["应到"].sum()
)
stage_order = bcm_stage_board["阶段"].tolist()
active_stage = str(st.session_state.get("semi_current_stage", stage_order[0]))

st.markdown(
    f"""
    <div class="hero">
      <div class="hero-kicker">Fab Emergency Command Center</div>
      <div class="hero-title">{incident_name}</div>
      <div class="hero-subtitle">
        面向晶圆厂与洁净生产区的厂级应急指挥界面，统一承载 EHS、厂务、设备、制造与 IT/MES 的处置、恢复和复产判断。
      </div>
      <div class="chip-row">
        <div class="chip">当前厂区：{fab_name}</div>
        <div class="chip">当前应变等级：{level}</div>
        <div class="chip">事故类型：{incident_type}</div>
        <div class="chip">事故区域：{incident_area}</div>
        <div class="chip">值守总指挥：{commander}</div>
        <div class="chip">班次：{shift_name}</div>
        <div class="chip">实时风况：{wind_direction_label}风 {format_metric(live_weather.get("wind_speed_ms"), " m/s", 1)}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_stage_action_bar(stage_order, active_stage=active_stage, sender=commander, allow_change=can_run_commands)

trigger_cols = st.columns(4)
with trigger_cols[0]:
    render_kpi_card("WIP 冻结批次", str(affected_lots), "受影响批次与载具已纳入冻结逻辑")
with trigger_cols[1]:
    render_kpi_card("资源缺口", str(resource_gap), "仍需跨厂支援或补充物资的人力缺口")
with trigger_cols[2]:
    render_kpi_card("复产未过关卡", str(open_gates), "未满足门槛前不建议切到营运恢复")
with trigger_cols[3]:
    render_kpi_card("点名失联", str(rollcall_missing), "二次点名、badge 与集合点仍需闭环")

render_section_head("当前事件已触发", "滚动显示当前告警和 GMS 读值；页面会自动刷新。")
render_event_ticker(triggered_items)

status_cols = st.columns(4)
with status_cols[0]:
    render_status_tile("tile-red", "FAB 风险评分", str(score), "综合严重度、气体、污染、公辅、设备和 MES 状态")
with status_cols[1]:
    render_status_tile("tile-amber", "高风险区域", str(critical_zones), "红橙分区需要持续封控或处置")
with status_cols[2]:
    render_status_tile("tile-cyan", "系统健康度", f"{system_health:.0%}", "毒气、洁净、公辅、排风和 MES 综合观测")
with status_cols[3]:
    render_status_tile("tile-green", "高优任务", str(high_priority_tasks), "建议维持 15 分钟一次 EOC 滚动复盘")

kpi_cols = st.columns(4)
with kpi_cols[0]:
    render_kpi_card("涉险人数", str(int(exposed_people)), "用于门禁复核、医疗点名和疏散闭环")
with kpi_cols[1]:
    render_kpi_card("受影响机台", str(int(tool_impact_count)), "进入设备保全、空跑验证和恢复前检查")
with kpi_cols[2]:
    render_kpi_card("洁净恢复度", f"{cleanroom_recovery_progress:.0%}", "未达环境门槛前不建议恢复量产")
with kpi_cols[3]:
    render_kpi_card("洁净室内点名", f"{rollcall_inside_rate:.0%}", "用于判断室内撤离是否已经闭环")

overview_tab, response_tab, incident_tab, recovery_tab, aloha_tab, sop_tab, zone_tab, comms_tab = st.tabs(
    ["综合态势", "应变处置", "事件管理", "营运恢复", "ALOHA工作台", "预案与SOP", "厂区分区", "通信日志"]
)

with overview_tab:
    left, right = st.columns([1.1, 0.9])
    with left:
        render_section_head("台系 BCM 三阶段", "参考台湾晶圆厂公开的营运持续做法，把应变、事件管理、恢复分成连续三层。")
        render_bcm_stage_cards(bcm_stage_board, active_stage=active_stage)
        render_section_head("SOP 当前节点", "控制台事故类型已映射到对应 SOP，当前节点会随着风险和恢复状态推进。")
        render_sop_execution_cards(sop_execution_board)
        render_section_head("处置目标", "把危险源、环境、设备、批次和恢复节奏放在同一张指挥图上。", dark=True)
        for objective in objectives:
            st.markdown(f"- {objective}")
        if mes_disrupted:
            st.warning("MES/告警链路受扰，建议同时启用离线批次台账、手工放行签核和口头双确认。")
        else:
            st.success("MES 与告警链路在线，可继续使用电子履历、异常追溯和设备联锁记录。")

        render_section_head("厂务与系统健康", "当前值、阈值和健康度用于判断是否具备继续处置或恢复生产的前提。")
        st.plotly_chart(render_facility_chart(facility_status), use_container_width=True)
    with right:
        render_section_head("快速指挥动作", "广播、点名、GMS、火警联动和支援请求应能一键推进，并在页面内立即生效。")
        render_enabled_action_summary(enabled_actions)
        action_cols = st.columns(3)
        with action_cols[0]:
            render_command_button(
                "启动厂广播",
                "broadcast",
                "启动厂广播",
                f"{incident_area} 已启动厂广播，请各区域依 {incident_type} 预案执行。",
                commander,
                button_key="cmd-broadcast",
                disabled=(not can_run_commands) or ("broadcast" in enabled_actions),
            )
        with action_cols[1]:
            render_command_button(
                "跨厂 CCTV",
                "cross_fab_cctv",
                "启用跨厂 CCTV",
                f"已开放 {fab_name} 事故区域画面供跨厂支援席查看。",
                commander,
                button_key="cmd-cross-fab-cctv",
                disabled=(not can_run_commands) or ("cross_fab_cctv" in enabled_actions),
            )
        with action_cols[2]:
            render_command_button(
                "ALOHA 推估",
                "aloha",
                "启动 ALOHA 推估",
                f"已指派 EHS 根据风向与源项对 {incident_type} 进行下风向扩散模拟。",
                commander,
                button_key="cmd-aloha",
                disabled=(not can_run_commands) or ("aloha" in enabled_actions),
            )
        action_cols_2 = st.columns(3)
        with action_cols_2[0]:
            render_command_button(
                "请求外援",
                "external_support",
                "请求外部支援",
                "已通知厂外支援与跨厂 ERT 待命。",
                commander,
                button_key="cmd-external-support",
                disabled=(not can_run_commands) or ("external_support" in enabled_actions),
            )
        with action_cols_2[1]:
            render_command_button(
                "冻结 WIP",
                "wip_lock",
                "冻结高风险 WIP",
                "已冻结高风险 Bay 批次与相关载具流转。",
                commander,
                button_key="cmd-wip-lock",
                disabled=(not can_run_commands) or ("wip_lock" in enabled_actions),
            )
        with action_cols_2[2]:
            if st.button("升级阶段", use_container_width=True, disabled=not can_run_commands):
                stage_order = bcm_stage_board["阶段"].tolist()
                current_index = stage_order.index(st.session_state["semi_current_stage"])
                if current_index < len(stage_order) - 1:
                    st.session_state["semi_current_stage"] = stage_order[current_index + 1]
                    trigger_command_action("stage_shift", "切换 BCM 阶段", f"当前 BCM 阶段已切换至 {st.session_state['semi_current_stage']}。", commander)
                    st.rerun()
        action_cols_3 = st.columns(3)
        with action_cols_3[0]:
            render_command_button(
                "启动火警联动",
                "fire_linkage",
                "启动火警联动",
                f"{incident_area} 已切换到火警联动检查模式，复核探测器、回路与防排烟状态。",
                commander,
                button_key="cmd-fire-linkage",
                disabled=(not can_run_commands) or ("fire_linkage" in enabled_actions),
            )
        with action_cols_3[1]:
            render_command_button(
                "GMS 二次复测",
                "gms_recheck",
                "派发 GMS 二次复测",
                f"已指派 EHS 对 {incident_area} 的 GMS 点位执行二次复测，并复核报警位置。",
                commander,
                button_key="cmd-gms-recheck",
                disabled=(not can_run_commands) or ("gms_recheck" in enabled_actions),
            )
        with action_cols_3[2]:
            render_command_button(
                "发布二次点名",
                "rollcall_muster",
                "发布二次点名",
                "已要求班组长、安保和门禁席同步执行洁净室内外二次点名。",
                commander,
                button_key="cmd-rollcall-muster",
                disabled=(not can_run_commands) or ("rollcall_muster" in enabled_actions),
            )
        action_cols_4 = st.columns(2)
        with action_cols_4[0]:
            render_command_button(
                "厂务隔离",
                "facility_isolation",
                "执行厂务隔离",
                f"已对 {incident_area} 周边关键公辅执行隔离，降低扩散与次生风险。",
                commander,
                button_key="cmd-facility-isolation",
                disabled=(not can_run_commands) or ("facility_isolation" in enabled_actions),
            )
        with action_cols_4[1]:
            render_command_button(
                "事故快报",
                "incident_briefing",
                "发布事故快报",
                f"已向管理层、制造、设备与供应链发出 {incident_type} 事故快报。",
                commander,
                button_key="cmd-incident-briefing",
                disabled=(not can_run_commands) or ("incident_briefing" in enabled_actions),
            )

        render_section_head("实时气象与外部工具", "把现实风场、ALOHA 官方工具和化学数据库挂到同一处，避免值班席来回切换。")
        if weather_online:
            render_weather_snapshot_cards(
                live_weather,
                site_name=fab_name,
                site_area=str(site_profile["area"]),
                wind_direction_label=wind_direction_label,
            )
            st.info(upwind_hint)
        else:
            st.warning(str(live_weather.get("message", "实时气象暂不可用，已切换到手工输入模式。")))
        link_cols = st.columns(3)
        with link_cols[0]:
            st.link_button("ALOHA 官方页面", ALOHA_OFFICIAL_URL, use_container_width=True)
        with link_cols[1]:
            st.link_button("实时气象数据源", OPEN_METEO_URL, use_container_width=True)
        with link_cols[2]:
            st.link_button("CAMEO 化学数据库", CAMEO_CHEMICALS_URL, use_container_width=True)

        render_section_head("任务状态", "建议按照高优先级任务推进节奏组织跨部门复盘。")
        status_counts = task_board["状态"].value_counts().rename_axis("状态").reset_index(name="数量")
        fig = px.pie(
            status_counts,
            names="状态",
            values="数量",
            hole=0.64,
            color="状态",
            color_discrete_sequence=["#22d3ee", "#38bdf8", "#f59e0b", "#ef4444", "#64748b"],
        )
        fig.update_layout(height=310, margin={"l": 10, "r": 10, "t": 10, "b": 10}, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

        render_section_head("待确认告警", "告警需要由指挥席确认、分派责任方并推进动作。")
        render_alert_cards(alert_board, allow_ack=can_run_commands)

        render_timeline_panel(timeline)

with response_tab:
    left, right = st.columns([1.02, 0.98])
    with left:
        render_section_head("厂级指挥编组", "把值守总指挥、EHS、厂务、设备、制造和 IT/MES 放在一条指挥链上。")
        render_command_cards(command_roster)
        render_section_head("任务看板", "现场处置和恢复前检查应明确责任、时限和状态。")
        render_task_lanes(task_board)
    with right:
        render_section_head("监控接口预留", "已为 CCTV、GMS、火警报警和厂广播预留接口，后续可接真实系统。")
        render_monitoring_interface_cards(monitoring_interface_board)
        render_section_head("GMS 读值与报警位置", "GMS 页面应直接显示读值、阈值和报警位置，而不是只写“有报警”。")
        render_gms_cards(gms_sensor_board)
        render_section_head("跨厂支援视角", "参考台湾大型晶圆厂公开做法，把跨厂画面、点名与资源联动纳入指挥席。")
        render_support_cards(cross_fab_support_board)
        render_section_head("WIP / 批次影响", "把工艺段、产品和释放条件明确化，避免事故结束后仍然批次失控。")
        st.plotly_chart(render_wip_chart(wip_board), use_container_width=True)
        render_wip_cards(wip_board)

with incident_tab:
    left, right = st.columns([1.06, 0.94])
    with left:
        render_section_head("洁净室内外点名总览", "分别跟踪洁净室内撤离与室外集合点到位情况，避免只做单口径点名。")
        render_rollcall_cards(rollcall_board)
    with right:
        render_section_head("点名修正", "允许值班人员手动修正区域点名结果，并保留动作轨迹。")
        with st.form("rollcall-update"):
            zone = st.selectbox("选择区域", rollcall_board["区域"].tolist(), disabled=not can_edit_rollcall)
            current_row = rollcall_board[rollcall_board["区域"] == zone].iloc[0]
            arrived = st.number_input(
                "已到人数",
                min_value=0,
                max_value=int(current_row["应到"]),
                value=int(current_row["已到"]),
                disabled=not can_edit_rollcall,
            )
            observe = st.number_input(
                "医疗观察人数",
                min_value=0,
                max_value=int(arrived),
                value=int(current_row["医疗观察"]),
                disabled=not can_edit_rollcall,
            )
            submitted = st.form_submit_button("更新点名", use_container_width=True, disabled=not can_edit_rollcall)
            if submitted:
                overrides = dict(st.session_state.get("semi_rollcall_overrides", {}))
                overrides[zone] = {"arrived": int(arrived), "observe": int(observe)}
                st.session_state["semi_rollcall_overrides"] = overrides
                trigger_command_action("rollcall_update", "更新点名结果", f"{zone} 已更新为已到 {arrived} 人、医疗观察 {observe} 人。", commander)
                st.rerun()
        if not can_edit_rollcall:
            st.info("当前账号没有点名修正权限，可查看点名闭环状态但不能修改结果。")
        render_section_head("badge / 门禁对账", "把 badge、承包商、访客和交接班名单纳入点名系统，贴近台湾 fab 实务。")
        render_audit_cards(badge_audit_board)
        indoor_missing = int(rollcall_board[rollcall_board["类型"] == "洁净室内"]["失联"].sum())
        outdoor_missing = int(rollcall_board[rollcall_board["类型"] == "室外"]["失联"].sum())
        render_status_tile("tile-cyan", "洁净室内失联", str(indoor_missing), "优先核对 badge、机台区、楼梯口与过站人员")
        render_status_tile("tile-green", "室外失联", str(outdoor_missing), "重点复核承包商、访客和交接班名单")
        st.markdown(
            "- 一次点名：班组长按洁净室内/室外口径分别回报。\n"
            "- 二次复核：EHS 与安保交叉核对 badge、门禁和集合点名单。\n"
            "- 失联处置：优先从高风险 Bay、Sub-Fab、楼梯间和临时作业点回查。"
        )

with recovery_tab:
    left, right = st.columns([1.04, 0.96])
    with left:
        render_section_head("资源出动结构", "应急小组、气体检测、公辅抢修、设备保全和批次追溯资源协同出动。")
        st.plotly_chart(render_resource_chart(resource_board), use_container_width=True)
        render_resource_cards(resource_board)
    with right:
        st.markdown(
            '<div class="card-light"><div class="section-title">复产关卡</div><div class="section-subtitle">没有通过复产门槛时，系统应维持在恢复验证态，而不是急于复机。</div>'
            + render_gate_list(recovery_checklist)
            + "</div>",
            unsafe_allow_html=True,
        )
        unmet = recovery_checklist[recovery_checklist["状态"] == "未满足"]["复产关卡"].tolist()
        if unmet:
            st.info("当前仍需优先收口：" + "、".join(unmet[:3]))
        else:
            st.success("复产关卡已满足，可进入复机节拍和受控投片阶段。")

with aloha_tab:
    render_section_head("ALOHA 扩散工作台", "用实时风场和源项快速预估下风向警戒区，正式封控范围仍应以 ALOHA 与应变团队判定为准。")
    top_left, top_right = st.columns([1.05, 0.95])
    with top_left:
        if weather_online:
            render_weather_snapshot_cards(
                live_weather,
                site_name=fab_name,
                site_area=str(site_profile["area"]),
                wind_direction_label=wind_direction_label,
            )
        else:
            st.warning(str(live_weather.get("message", "实时气象不可用，请改用手工气象输入。")))
        st.caption(f"厂区气象：{fab_name} · {site_profile['area']} · 数据源 Open-Meteo")
    with top_right:
        render_section_head("工具链接", "值班席可直接跳转官方工具或化学数据库，减少临场检索时间。")
        st.link_button("打开 ALOHA 官方页面", ALOHA_OFFICIAL_URL, use_container_width=True)
        st.link_button("打开 CAMEO 化学数据库", CAMEO_CHEMICALS_URL, use_container_width=True)
        st.link_button("查看实时气象接口说明", OPEN_METEO_URL, use_container_width=True)
        st.info("建议流程：先核对实时风场，再确认化学品和源项，最后用 ALOHA 正式模型复核警戒圈。")

    st.markdown("---")
    control_left, control_right = st.columns([1.08, 0.92])
    with control_left:
        chemical_options = ["氯气", "氨气", "氢氟酸", "盐酸蒸气", "硅烷", "异丙醇蒸气"]
        if st.session_state.get("semi_aloha_chemical") not in chemical_options:
            st.session_state["semi_aloha_chemical"] = chemical_options[0]
        aloha_chemical = st.selectbox("化学品", chemical_options, key="semi_aloha_chemical", disabled=not can_use_aloha)
        release_rate_kg_min = st.slider(
            "泄漏速率 (kg/min)",
            min_value=0.1,
            max_value=20.0,
            value=4.5,
            step=0.1,
            disabled=not can_use_aloha,
        )
        duration_min = st.slider(
            "泄漏持续时间 (min)",
            min_value=1,
            max_value=60,
            value=15,
            step=1,
            disabled=not can_use_aloha,
        )
        use_live_weather = st.toggle("使用实时气象填充 ALOHA 快速推估", value=weather_online, disabled=not can_use_aloha)
        if not can_use_aloha:
            st.info("当前账号没有 ALOHA 工作台操作权限，系统已切换为只读查看模式。")
        if use_live_weather:
            wind_speed_for_estimate = live_wind_speed
            temperature_for_estimate = live_temperature
            humidity_for_estimate = live_humidity
            st.success(
                f"已使用 {fab_name} 的实时气象：{wind_direction_label}风 {live_wind_speed:.1f} m/s，"
                f"气温 {live_temperature:.1f} °C，湿度 {live_humidity:.0f}%。"
            )
        else:
            weather_cols = st.columns(3)
            with weather_cols[0]:
                wind_speed_for_estimate = st.number_input(
                    "风速 (m/s)",
                    min_value=0.1,
                    max_value=30.0,
                    value=live_wind_speed,
                    step=0.1,
                    disabled=not can_use_aloha,
                )
            with weather_cols[1]:
                temperature_for_estimate = st.number_input(
                    "气温 (°C)",
                    min_value=-20.0,
                    max_value=60.0,
                    value=live_temperature,
                    step=0.5,
                    disabled=not can_use_aloha,
                )
            with weather_cols[2]:
                humidity_for_estimate = st.number_input(
                    "湿度 (%)",
                    min_value=1.0,
                    max_value=100.0,
                    value=live_humidity,
                    step=1.0,
                    disabled=not can_use_aloha,
                )

        aloha_estimate = build_aloha_quick_estimate(
            chemical_name=aloha_chemical,
            release_rate_kg_min=float(release_rate_kg_min),
            duration_min=int(duration_min),
            wind_speed_ms=float(wind_speed_for_estimate),
            temperature_c=float(temperature_for_estimate),
            humidity_pct=float(humidity_for_estimate),
        )
        chemical_ghs_profile = build_chemical_ghs_profile(aloha_chemical)
        render_aloha_zone_cards(aloha_estimate)
    with control_right:
        render_ghs_profile(chemical_ghs_profile, aloha_chemical)
        render_section_head("快速判读", "把推估半径直接翻译成现场动作，避免指挥席只看数字。")
        st.plotly_chart(render_aloha_zone_chart(aloha_estimate), use_container_width=True)
        total_release = float(release_rate_kg_min) * int(duration_min)
        direction_note = f"{wind_direction_label}风" if wind_direction_label != "未知" else "风向待确认"
        render_kpi_card("估算释放量", f"{total_release:.1f} kg", "用于值班席快速判断是否需要升级事故等级")
        render_kpi_card("下风向判读", direction_note, "优先封控下风侧、保留上风侧紧急通道和集合点")
        render_kpi_card("模型模式", "快速预估", "适合作为 ERC 初判，不替代正式 ALOHA 场景建模")
        st.markdown(
            "- 红区：仅允许完整 PPE 与检测装备齐全的 ERT 进入。\n"
            "- 橙区：限制人员进出，优先布风向标、便携检测和交通管制。\n"
            "- 黄区：执行厂广播、集合点调整、badge 二次复核与客户影响预通知。"
        )
        if toxic_gas_risk >= 0.65:
            st.warning("当前毒气风险较高，建议同步启动正式 ALOHA 建模、跨厂 CCTV 和室外集合点上风侧复核。")
        else:
            st.info("当前更适合把快速推估作为预防性工具，用于先行布点、预布人力和广播演练。")

with sop_tab:
    left, right = st.columns([1.08, 0.92])
    with left:
        render_section_head("照片提取预案库", "已将照片中的应急 CheckList 结构化录入，方便按场景与阶段筛选。")
        checklist_names = list(dict.fromkeys(photo_checklists["预案"].tolist()))
        target_checklist = get_checklist_name_for_incident(incident_type)
        default_index = checklist_names.index(target_checklist) if target_checklist in checklist_names else 0
        selected_checklist = st.selectbox("选择预案", checklist_names, index=default_index)
        filtered_checklist = photo_checklists[photo_checklists["预案"] == selected_checklist].copy()
        stage_count = filtered_checklist["阶段"].nunique()
        task_count = len(filtered_checklist)
        stat_cols = st.columns(2)
        with stat_cols[0]:
            render_kpi_card("阶段数", str(stage_count), "对应照片中提取出的阶段节点")
        with stat_cols[1]:
            render_kpi_card("任务数", str(task_count), "已录入的关键动作与执行单位")
        render_checklist_stage_cards(filtered_checklist)
    with right:
        render_section_head("处理流程库", "把照片里的流程图转成可直接阅读的分步 SOP。")
        process_names = list(photo_processes.keys())
        target_process = get_process_name_for_incident(incident_type)
        process_index = process_names.index(target_process) if target_process in process_names else 0
        selected_process = st.selectbox("选择流程", process_names, index=process_index)
        render_process_steps(photo_processes[selected_process])

        render_section_head("ERO 组织结构", "根据照片中的 ERO 组织图整理核心指挥、应急功能组与专业支援。")
        render_ero_cloud(photo_ero_structure)
        render_section_head("参考补充", "新增 ALOHA 扩散模拟与氯气危害预防/应变计划的可用参考，方便继续深化系统。")
        render_reference_cards(reference_supplements)
        st.caption("照片中还包含 Fab1 3F 平面图参考；当前已先把组织、预案和流程结构化录入，后续可继续接入原图平面图。")

with zone_tab:
    left, right = st.columns([1.08, 0.92])
    with left:
        render_section_head("厂区分区态势图", "同时关注事故 Bay、Sub-Fab、洁净区、化学品区、公辅站和集合点。")
        st.plotly_chart(render_zone_chart(zone_status), use_container_width=True)
    with right:
        render_section_head("区域监测数据", "风险、人员密度和恢复度共同决定封控与放行策略。")
        render_zone_cards(zone_status.drop(columns=["横轴", "纵轴"]))
        render_section_head("系统健康明细", "这些观测项决定应急状态能否切换到恢复状态。", dark=True)
        render_facility_cards(facility_status, dark=True)

with comms_tab:
    render_section_head("指挥通信日志", "保留接警、调度、环境、厂务、设备和生产回报的统一链路。")
    log_frame = pd.DataFrame(st.session_state["semi_command_log"])
    render_log_stream(log_frame)

    render_section_head("新增播报", "建议所有播报都包含区域、状态、动作和下一次更新时间。")
    with st.form("semi-add-log", clear_on_submit=True):
        category = st.selectbox(
            "日志类别",
            ["接警", "调度", "环境回报", "厂务回报", "设备回报", "生产回报"],
            disabled=not can_write_logs,
        )
        sender = st.text_input("发送方", value=commander, disabled=not can_write_logs)
        content = st.text_area(
            "播报内容",
            placeholder="例如：A栋气柜已切断，Sub-Fab 排风维持，受影响批次已冻结，下一次复测 10 分钟后回报。",
            disabled=not can_write_logs,
        )
        submitted = st.form_submit_button("写入日志", use_container_width=True, disabled=not can_write_logs)
        if submitted:
            add_log_entry(category=category, sender=sender, content=content)
    if not can_write_logs:
        st.info("当前账号没有通信记录权限，可查看日志但不能新增播报。")
