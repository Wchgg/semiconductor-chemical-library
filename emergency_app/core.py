from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd


ROLE_ASSIGNMENTS = [
    ("总指挥", "总体决策、升级响应、跨部门协调"),
    ("现场行动组", "灭火/救援/搜救/警戒线执行"),
    ("情报研判组", "态势更新、风险研判、预测扩散"),
    ("医疗救治组", "检伤分类、医院协调、转运分流"),
    ("后勤保障组", "物资补给、道路保通、电力通信保障"),
    ("公众信息组", "统一口径、媒体发布、群众引导"),
    ("联络协调组", "与公安、消防、医院、街道联动"),
    ("安全监督官", "次生灾害监测、人员安全稽核"),
]


def calculate_incident_score(
    severity: int,
    affected_people: int,
    critical_sites: int,
    weather_risk: float,
    medical_pressure: float,
    communications_disrupted: bool,
) -> int:
    severity_score = severity * 12
    people_score = min(24, affected_people / 25)
    site_score = critical_sites * 4
    weather_score = weather_risk * 14
    medical_score = medical_pressure * 16
    communication_score = 10 if communications_disrupted else 0

    score = round(
        severity_score
        + people_score
        + site_score
        + weather_score
        + medical_score
        + communication_score
    )
    return max(0, min(100, score))


def classify_response_level(score: int) -> str:
    if score >= 85:
        return "I级响应"
    if score >= 70:
        return "II级响应"
    if score >= 50:
        return "III级响应"
    return "IV级响应"


def generate_response_objectives(
    incident_type: str,
    level: str,
    affected_people: int,
    communications_disrupted: bool,
) -> list[str]:
    objectives = [
        "30分钟内完成现场统一指挥席搭建与责任到岗确认。",
        "优先控制核心风险源，防止事故外溢和次生灾害。",
        "建立伤员转运与安置闭环，滚动更新救治和安置人数。",
    ]

    incident_specific = {
        "城市火灾": "重点保护医院、学校、油气点位等高敏感目标，压制火势蔓延。",
        "危化品泄漏": "立即划设警戒区和洗消区，监控风向并组织分级撤离。",
        "地震灾害": "优先开展生命搜救，核查危楼、桥梁和燃气设施受损情况。",
        "洪涝灾害": "优先打通生命通道，封控漫水路段并转移低洼地带群众。",
        "公共卫生": "启动分级分诊与流调链路，确保检验、隔离、发布同步。",
        "综合突发": "按照多灾种复合场景统筹消防、医疗、公安和市政力量。",
    }
    objectives.append(incident_specific.get(incident_type, incident_specific["综合突发"]))

    if affected_people >= 500:
        objectives.append("启动大规模疏散与集中安置方案，优先保障老人、儿童和行动不便人员。")
    if communications_disrupted:
        objectives.append("启用应急通信车、卫星电话和离线回传机制，确保每15分钟一次态势回报。")
    if level in {"I级响应", "II级响应"}:
        objectives.append("按高等级响应运行跨部门会商机制，关键指标每30分钟复盘一次。")

    return objectives


def build_command_roster(commander: str, location: str) -> pd.DataFrame:
    owners = [
        commander,
        "消防支队联勤席",
        "应急管理局值守席",
        "市急救中心调度席",
        "交通/供电联合保障席",
        "宣传与舆情专班",
        "公安与街道联络席",
        "现场安全员",
    ]
    rows = []
    for index, ((role, focus), owner) in enumerate(zip(ROLE_ASSIGNMENTS, owners), start=1):
        rows.append(
            {
                "序号": index,
                "职能": role,
                "负责人": owner,
                "当前重点": focus,
                "部署位置": location if role == "总指挥" else "前方指挥车/分区席位",
            }
        )
    return pd.DataFrame(rows)


def build_resource_board(
    level: str,
    affected_people: int,
    medical_pressure: float,
) -> pd.DataFrame:
    level_factor = {"IV级响应": 1.0, "III级响应": 1.2, "II级响应": 1.5, "I级响应": 1.9}[level]
    people_factor = max(1.0, affected_people / 180)

    resources = [
        ("消防救援队", 6, 4),
        ("医疗转运车", 8, 5),
        ("警戒疏导组", 10, 6),
        ("无人机巡查组", 4, 2),
        ("应急通信车", 2, 1),
        ("后勤补给车", 5, 3),
        ("临时安置点", 3, 2),
    ]

    rows = []
    medical_boost = 1.0 + medical_pressure * 0.5
    for resource_name, base_ready, base_dispatch in resources:
        boost = medical_boost if resource_name in {"医疗转运车", "临时安置点"} else 1.0
        ready = int(round(base_ready * level_factor * people_factor * boost))
        dispatched = min(ready, int(round(base_dispatch * level_factor * boost)))
        standby = max(0, ready - dispatched)
        demand = int(round(dispatched * 1.15 + affected_people / 150))
        gap = max(0, demand - ready)
        rows.append(
            {
                "资源类型": resource_name,
                "已到位": ready,
                "已出动": dispatched,
                "待命": standby,
                "预测需求": demand,
                "缺口": gap,
                "到位率": 0.0 if demand == 0 else min(1.0, ready / demand),
            }
        )

    return pd.DataFrame(rows)


def build_task_board(
    incident_type: str,
    level: str,
    evacuation_progress: float,
) -> pd.DataFrame:
    urgency = "高" if level in {"I级响应", "II级响应"} else "中"
    evacuation_status = "进行中" if evacuation_progress < 0.85 else "待复核"

    tasks = [
        ("总指挥", "完成首轮态势研判并下达统一口令", "15分钟内", "已下达"),
        ("现场行动组", f"处置{incident_type}主风险源并压缩危险范围", "30分钟内", "执行中"),
        ("医疗救治组", "建立伤员分级与转运清单", "20分钟内", "执行中"),
        ("联络协调组", "同步公安、街道、医院与市政资源", "15分钟内", "已联动"),
        ("后勤保障组", "补给照明、电台、饮水、防护用品", "40分钟内", "待补齐"),
        ("公众信息组", "发布权威通告与避险指引", "25分钟内", "待发布"),
        ("安全监督官", "复核警戒区、次生灾害与人员暴露风险", "持续滚动", "巡检中"),
        ("情报研判组", f"疏散进度复盘，当前完成率 {evacuation_progress:.0%}", "30分钟内", evacuation_status),
    ]

    rows = []
    for role, task, deadline, status in tasks:
        rows.append(
            {
                "职能": role,
                "任务": task,
                "优先级": urgency if role != "后勤保障组" else "中",
                "时限": deadline,
                "状态": status,
            }
        )
    return pd.DataFrame(rows)


def build_sector_status(
    severity: int,
    affected_people: int,
    weather_risk: float,
    evacuation_progress: float,
) -> pd.DataFrame:
    base_density = max(0.2, min(1.0, affected_people / 800))
    sectors = [
        ("核心处置区", 1, 4, 88 + severity * 2, base_density * 0.85, 0.40),
        ("搜救通道", 2, 3, 62 + severity * 3, base_density * 0.70, 0.55),
        ("医疗转运区", 3, 2, 48 + severity * 2, base_density * 0.60, 0.72),
        ("群众安置区", 4, 1, 36 + severity * 2, base_density * 0.95, evacuation_progress),
        ("外围管制区", 5, 3, 42 + weather_risk * 20, base_density * 0.35, 0.90),
    ]

    rows = []
    for name, x_axis, y_axis, risk_index, density, mobility in sectors:
        if risk_index >= 85:
            status = "红色警戒"
        elif risk_index >= 65:
            status = "橙色管控"
        elif risk_index >= 45:
            status = "黄色巡查"
        else:
            status = "绿色稳定"

        rows.append(
            {
                "区域": name,
                "横轴": x_axis,
                "纵轴": y_axis,
                "风险指数": min(100.0, round(risk_index, 1)),
                "人员密度": min(1.0, round(density, 2)),
                "通行能力": min(1.0, round(mobility, 2)),
                "状态": status,
            }
        )

    return pd.DataFrame(rows)


def default_communication_log(level: str, incident_type: str, commander: str) -> list[dict[str, str]]:
    now = datetime.now().replace(second=0, microsecond=0)
    entries = [
        (0, "一级信息", "接警中心", f"接报 {incident_type} 事件，按 {level} 标准启动应急研判。"),
        (7, "调度命令", commander, "前方指挥车、消防、医疗、公安力量同步集结。"),
        (15, "态势播报", "情报研判组", "警戒区已划设，核心风险点位持续监测中。"),
        (23, "资源回报", "后勤保障组", "通信、电源、照明设备到场，补给链保持畅通。"),
    ]
    log = []
    for minutes, category, sender, content in entries:
        timestamp = now - timedelta(minutes=minutes)
        log.append(
            {
                "时间": timestamp.strftime("%H:%M"),
                "类别": category,
                "发送方": sender,
                "内容": content,
            }
        )
    return log
