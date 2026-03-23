from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import requests


SEMICONDUCTOR_INCIDENT_TYPES = [
    "化灾",
    "火灾",
    "气灾",
    "地震",
    "电力中断或压降",
    "异味",
    "暴雨天气",
    "台风天气",
    "漏水事件",
]

TAIWAN_FAB_SITES = {
    "新竹 Fab 12A": {"lat": 24.781, "lon": 121.006, "area": "Hsinchu / Baoshan"},
    "台中 Fab 15A": {"lat": 24.254, "lon": 120.523, "area": "Taichung Central Taiwan Science Park"},
    "台南 Fab 18A": {"lat": 23.104, "lon": 120.270, "area": "Tainan Southern Taiwan Science Park"},
    "高雄 Fab 22": {"lat": 22.759, "lon": 120.332, "area": "Kaohsiung Nanzih"},
}

CHEMICAL_GHS_PROFILES = {
    "氯气": {
        "信号词": "危险",
        "GHS图示": ["氧化剂", "高压气体", "腐蚀", "急毒", "环境危害"],
        "主要危害": [
            "强烈刺激并腐蚀呼吸道、眼睛与皮肤",
            "高浓度吸入可致命，泄漏时下风向暴露风险极高",
            "对水生环境有高危害，禁止未经控制直接排放",
        ],
        "关键PPE": ["正压式空气呼吸器", "全身防化服", "耐化手套", "面屏/护目镜"],
        "现场禁忌": ["禁止无防护进入下风处", "禁止与还原剂或可燃物混放", "禁止直接冲入一般排水系统"],
        "首要动作": ["立即上风侧封控并疏散", "确认气柜/阀组切断与 scrubber", "连续监测下风向浓度变化"],
    },
    "氨气": {
        "信号词": "危险",
        "GHS图示": ["高压气体", "腐蚀", "急毒", "环境危害"],
        "主要危害": [
            "强烈刺激眼睛、皮肤和呼吸道",
            "高浓度吸入可造成肺部损伤与窒息风险",
            "泄漏后可快速扩散并影响周边集合点",
        ],
        "关键PPE": ["正压式空气呼吸器", "防化手套", "耐碱防护服", "护目镜"],
        "现场禁忌": ["禁止逆风接近源头", "禁止与酸类混触", "禁止在未复测前解除封锁"],
        "首要动作": ["立即确认风向并疏散下风处", "隔离阀组并稳定排风", "对暴露人员进行冲洗与医疗评估"],
    },
    "氢氟酸": {
        "信号词": "危险",
        "GHS图示": ["腐蚀", "急毒", "健康危害"],
        "主要危害": [
            "对皮肤、眼睛和黏膜高度腐蚀",
            "可经皮吸收并造成深部组织与全身毒性伤害",
            "泄漏后需特别关注二次接触和残留污染",
        ],
        "关键PPE": ["防酸防化服", "丁基/氯丁防化手套", "面屏/护目镜", "呼吸防护具"],
        "现场禁忌": ["禁止徒手处理污染物", "禁止使用不相容吸附材", "禁止忽略二次洗消与污染工具隔离"],
        "首要动作": ["立即围堵与隔离污染面", "启动洗消并准备葡萄糖酸钙医疗资源", "确认废液与污染耗材分流收集"],
    },
    "盐酸蒸气": {
        "信号词": "危险",
        "GHS图示": ["腐蚀", "惊叹号"],
        "主要危害": [
            "腐蚀眼睛、皮肤与呼吸道",
            "蒸气可沿下风处扩散并造成局部高暴露",
            "接触金属可能释出其他危险气体",
        ],
        "关键PPE": ["防酸手套", "防化围裙/防护服", "护目镜", "呼吸防护具"],
        "现场禁忌": ["禁止与碱类或漂白剂混合", "禁止在密闭低洼处久留", "禁止未复测即恢复通行"],
        "首要动作": ["确认源头并上风侧接近", "围堵并加强排风", "复测蒸气后再解除警戒"],
    },
    "硅烷": {
        "信号词": "危险",
        "GHS图示": ["火焰", "高压气体"],
        "主要危害": [
            "极易自燃，泄漏后遇空气可迅速着火",
            "高压气体释放会造成喷射与二次点火风险",
            "需同时管理火灾、爆炸和窒息风险",
        ],
        "关键PPE": ["阻燃防护服", "空气呼吸器", "防火手套", "防爆通讯设备"],
        "现场禁忌": ["禁止产生火花", "禁止带电拆装或临时作业", "禁止在未惰化确认前接近设备"],
        "首要动作": ["立即切断供气并清场", "确认惰化/排风/火警联锁状态", "同步布置消防与气体检测"],
    },
    "异丙醇蒸气": {
        "信号词": "危险",
        "GHS图示": ["火焰", "惊叹号"],
        "主要危害": [
            "高度易燃，蒸气可与空气形成可燃混合物",
            "可刺激眼睛并导致头晕、嗜睡等中枢抑制症状",
            "低洼处与回风区应重点防范积聚",
        ],
        "关键PPE": ["防静电工作服", "耐化手套", "护目镜", "必要时配戴呼吸防护具"],
        "现场禁忌": ["禁止明火和热源", "禁止非防爆设备进入", "禁止忽略回风与低洼区检测"],
        "首要动作": ["先消除点火源", "加强排风并限制动火", "以可燃气体检测确认安全后再恢复作业"],
    },
}

INCIDENT_CONTROL_PROFILES = {
    "化灾": {
        "incident_suffix": "化灾联动处置",
        "incident_area": "湿制程化学品供应区 / 排水沟附近",
        "commander": "林予安",
        "severity": 4,
        "exposed_people": 54,
        "inside_ratio": 0.63,
        "tool_impact_count": 12,
        "toxic_gas_risk": 0.34,
        "contamination_risk": 0.81,
        "utility_failure": 0.28,
        "cleanroom_recovery_progress": 0.38,
        "mes_disrupted": False,
        "chemical_name": "氢氟酸",
    },
    "火灾": {
        "incident_suffix": "火灾联动处置",
        "incident_area": "A栋 MAU / 电气夹层",
        "commander": "周岚",
        "severity": 5,
        "exposed_people": 88,
        "inside_ratio": 0.56,
        "tool_impact_count": 26,
        "toxic_gas_risk": 0.42,
        "contamination_risk": 0.48,
        "utility_failure": 0.66,
        "cleanroom_recovery_progress": 0.24,
        "mes_disrupted": True,
        "chemical_name": "硅烷",
    },
    "气灾": {
        "incident_suffix": "气灾联动处置",
        "incident_area": "A栋 Gas Cabinet / Sub-Fab",
        "commander": "周岚",
        "severity": 4,
        "exposed_people": 96,
        "inside_ratio": 0.58,
        "tool_impact_count": 18,
        "toxic_gas_risk": 0.78,
        "contamination_risk": 0.42,
        "utility_failure": 0.36,
        "cleanroom_recovery_progress": 0.32,
        "mes_disrupted": True,
        "chemical_name": "氯气",
    },
    "地震": {
        "incident_suffix": "地震应变处置",
        "incident_area": "全厂区 / 洁净室 / Sub-Fab",
        "commander": "许明岳",
        "severity": 5,
        "exposed_people": 120,
        "inside_ratio": 0.52,
        "tool_impact_count": 30,
        "toxic_gas_risk": 0.36,
        "contamination_risk": 0.40,
        "utility_failure": 0.74,
        "cleanroom_recovery_progress": 0.22,
        "mes_disrupted": True,
        "chemical_name": "氨气",
    },
    "电力中断或压降": {
        "incident_suffix": "电力中断或压降恢复",
        "incident_area": "Main Substation / Fab 支线",
        "commander": "许明岳",
        "severity": 4,
        "exposed_people": 68,
        "inside_ratio": 0.52,
        "tool_impact_count": 32,
        "toxic_gas_risk": 0.18,
        "contamination_risk": 0.30,
        "utility_failure": 0.84,
        "cleanroom_recovery_progress": 0.34,
        "mes_disrupted": True,
        "chemical_name": "硅烷",
    },
    "异味": {
        "incident_suffix": "异味源追查处置",
        "incident_area": "Fab Bay / Drain / Scrubber 周边",
        "commander": "叶知衡",
        "severity": 3,
        "exposed_people": 46,
        "inside_ratio": 0.49,
        "tool_impact_count": 8,
        "toxic_gas_risk": 0.44,
        "contamination_risk": 0.38,
        "utility_failure": 0.24,
        "cleanroom_recovery_progress": 0.52,
        "mes_disrupted": False,
        "chemical_name": "氯气",
    },
    "暴雨天气": {
        "incident_suffix": "暴雨天气应变",
        "incident_area": "厂区外围 / 地下机房 / 雨排系统",
        "commander": "陆承叙",
        "severity": 3,
        "exposed_people": 42,
        "inside_ratio": 0.34,
        "tool_impact_count": 10,
        "toxic_gas_risk": 0.10,
        "contamination_risk": 0.22,
        "utility_failure": 0.64,
        "cleanroom_recovery_progress": 0.58,
        "mes_disrupted": False,
        "chemical_name": "氨气",
    },
    "台风天气": {
        "incident_suffix": "台风天气应变",
        "incident_area": "厂区外围 / 屋顶 / 雨排系统",
        "commander": "陆承叙",
        "severity": 4,
        "exposed_people": 56,
        "inside_ratio": 0.30,
        "tool_impact_count": 14,
        "toxic_gas_risk": 0.12,
        "contamination_risk": 0.26,
        "utility_failure": 0.70,
        "cleanroom_recovery_progress": 0.50,
        "mes_disrupted": False,
        "chemical_name": "氨气",
    },
    "漏水事件": {
        "incident_suffix": "漏水事件应变",
        "incident_area": "UPW 夹层 / Fab Bay 地板下方",
        "commander": "韩书廷",
        "severity": 3,
        "exposed_people": 38,
        "inside_ratio": 0.61,
        "tool_impact_count": 20,
        "toxic_gas_risk": 0.08,
        "contamination_risk": 0.44,
        "utility_failure": 0.46,
        "cleanroom_recovery_progress": 0.48,
        "mes_disrupted": True,
        "chemical_name": "异丙醇蒸气",
    },
}

INCIDENT_TO_CHECKLIST = {
    "化灾": "化灾应急CheckList",
    "火灾": "火灾应急CheckList",
    "气灾": "气灾应急CheckList",
    "地震": "地震应急CheckList",
    "电力中断或压降": "电力中断压降CheckList",
    "异味": "异味CheckList",
    "暴雨天气": "暴雨天气应急CheckList",
    "台风天气": "台风天气应急CheckList",
    "漏水事件": "漏水事件应急CheckList",
}

INCIDENT_TO_PROCESS = {
    "化灾": "化学品泄漏处理流程",
    "火灾": "火灾处理流程",
    "气灾": "气体泄漏处理流程",
    "地震": "地震处理流程",
    "电力中断或压降": "电力中断或压降处理流程",
    "异味": "异味处理流程",
    "暴雨天气": "紧急应变指挥官处理流程",
    "台风天气": "紧急应变指挥官处理流程",
    "漏水事件": "漏水处理流程",
}


PHOTO_CHECKLIST_ITEMS = [
    ("化灾应急CheckList", "事故发生", "确认化灾或泄漏传感器报警、通知 ERC 与事故指挥官到位", "ERC/IC"),
    ("化灾应急CheckList", "事故发生", "判断化学品种类、影响范围和人员暴露风险，按等级组织隔离", "ERC/FAC"),
    ("化灾应急CheckList", "ERT成立", "通知 ERT 携带防化、围堵、洗消与吸附物资到场", "IC/ERT"),
    ("化灾应急CheckList", "现场处置", "优先切断源头、建立警戒区、避免与禁忌物接触", "ERT/FAC"),
    ("化灾应急CheckList", "现场处置", "确认废液收集与现场洗消方式，防止流入排水系统", "ERT/MFG"),
    ("化灾应急CheckList", "恢复解除", "完成环境复原、废弃物转运与事故复盘，解除警报", "ERC/ESH"),
    ("火灾应急CheckList", "事故发生", "确认火警、回报起火点位与烟雾情况，通知 ERC 集合", "ERC"),
    ("火灾应急CheckList", "ERT成立", "确认消防器材、呼吸防护、对讲机与撤离广播准备", "IC"),
    ("火灾应急CheckList", "危险确认", "判断火势是否可控，核查电力、气体、排风与机台连锁", "ERT/ERC"),
    ("火灾应急CheckList", "现场处置", "优先人员疏散，其次控制火源与周边易燃物，必要时请求厂外支援", "ERT/FAC"),
    ("火灾应急CheckList", "恢复解除", "完成余火确认、受损区域封锁、损失统计与复产条件评估", "ERC/ESH"),
    ("气灾应急CheckList", "事故发生", "确认 MLG/GMS 或气体侦测系统报警，判断是否 shutdown", "ERC/FAC"),
    ("气灾应急CheckList", "ERT成立", "确认 ERT 人员、空气呼吸器、气体检测仪和疏散路线", "IC"),
    ("气灾应急CheckList", "危险确认", "确认是否为特气、毒气或惰性气体泄漏，并划设警戒区", "ERT/ERC"),
    ("气灾应急CheckList", "现场处置", "切断阀组、稳定排风与尾气处理、禁止无关人员进入 sub-fab", "ERT/FAC"),
    ("气灾应急CheckList", "恢复解除", "完成区域复测和原因调查，确认无残余风险后解除警报", "ERC/ESH"),
    ("地震应急CheckList", "事故发生", "地震发生时要求人员就地掩护、远离高架与危险源", "ERC/IC"),
    ("地震应急CheckList", "ERT成立", "集结 ERT，确认是否有人员受困、火灾、漏水或设施损坏", "IC"),
    ("地震应急CheckList", "巡查跟进", "核查厂房结构、机台固定、化学品柜、气体与电力状态", "ERC/FAC"),
    ("地震应急CheckList", "现场处置", "优先处理次生灾害并封锁危险区域，组织点名与伤员转运", "ERT/MFG"),
    ("地震应急CheckList", "恢复解除", "完成余震评估、结构确认与系统复原后再决定复产", "ERC/ESH"),
    ("电力中断压降CheckList", "事故发生", "确认厂务停电或压降原因，检查 EMS/GMS/门禁/CCTV 是否在线", "FAC/ERC"),
    ("电力中断压降CheckList", "ERT成立", "确认 ERC 广播、值班长与关键公辅值守是否到位", "IC"),
    ("电力中断压降CheckList", "通报拉警", "通知受影响区域确认机台、真空、排风、冷却与 UPS 状态", "ERC/FAC"),
    ("电力中断压降CheckList", "现场处置", "按优先级恢复电力与公辅，防止腔体、机台与批次损伤", "ERT/FAC"),
    ("电力中断压降CheckList", "恢复解除", "确认供电稳定、Exhaust 恢复、机台完成重启检查", "ERC/MFG"),
    ("异味CheckList", "事故发生", "确认异味来源、影响区域与投诉信息，判断是否涉及化学品/气体/排水", "ERC/FAC"),
    ("异味CheckList", "ERT成立", "安排 ERT 携带检测仪、PPE 和现场记录工具到场", "IC"),
    ("异味CheckList", "危险确认", "检查 HVAC、Exhaust、Drain、Scrubber、sub-fab 与工艺区域", "FAC/Module"),
    ("异味CheckList", "现场处置", "按区域逐项排查并控制潜在源头，必要时扩大警戒或局部停机", "FAC/ERT"),
    ("异味CheckList", "恢复解除", "异味消除后复测并通知相关部门，补充原因调查与改善项目", "ERC"),
    ("暴雨天气应急CheckList", "预警响应（橙色预警）", "ERC 发布恶劣天气预警，召开 30 分钟内 ERC 集合", "ERC/IC"),
    ("暴雨天气应急CheckList", "预警响应（橙色预警）", "各部门停止高风险作业并巡检积水、排水、边坡与脆弱点", "FAC/FAB/行政/WH/IT/Lab"),
    ("暴雨天气应急CheckList", "巡查跟进", "ERC 使用 checklist 汇总各部门巡检反馈，按小时回报", "ERC"),
    ("暴雨天气应急CheckList", "预警更新（升级红色预警）", "要求增加巡检频率、补充沙包与防洪物资、准备厂广播", "IC"),
    ("暴雨天气应急CheckList", "预警解除", "汇整漏水、积水与损伤信息，安排后续追踪整改", "ESH"),
    ("台风天气应急CheckList", "预警响应（橙色预警）", "ERC 发布台风预警并确认气象监测、风雨情况和应急会议", "ERC/IC"),
    ("台风天气应急CheckList", "预警响应（橙色预警）", "各部门巡检门窗、屋顶、雨排、室外物品、围挡与高空风险", "FAC/行政/FAB/WH"),
    ("台风天气应急CheckList", "巡查跟进", "要求责任部门定时回报现场状态与危险点变化", "ERC/IC"),
    ("台风天气应急CheckList", "预警更新（升级红色预警）", "提前关闭高风险活动，必要时安排宿舍待命和人力预布", "IC"),
    ("台风天气应急CheckList", "预警解除", "确认设施安全后解除状态并纳入专项追踪整改", "ESH"),
    ("漏水事件应急CheckList", "事件发生", "确认 ERC Leak Sensor 是否真实报警并通知区域人员佩戴防护", "ERC"),
    ("漏水事件应急CheckList", "ERT成立", "确认指挥官、安全官和 ERT 到位，必要时进行厂广播与人数清点", "IC"),
    ("漏水事件应急CheckList", "危害确认", "判断是否有触电风险、设备受影响风险和漏水源头位置", "ERT"),
    ("漏水事件应急CheckList", "现场处置", "优先止漏、围堵、导排和保护机台，必要时扩大应急等级", "ERT/IC"),
    ("漏水事件应急CheckList", "现场复原", "确认环境恢复、受影响设备状态、生产损失与后续改善项", "IC/ESH"),
]


PHOTO_PROCESS_LIBRARY = {
    "紧急应变指挥官处理流程": [
        "接报事故后，由厂务/EHS/监控室先做初步确认并通知 ERC。",
        "事故指挥官判定事故等级，决定是否启动 ERC/ERT 与厂广播。",
        "明确安全官、救灾组、急救组、疏散组、管制组等角色。",
        "按事故类型指挥 FAC、制造、设备、IT/MES 进行联动处置。",
        "滚动回收现场信息，评估升级、解除或请求厂外支援。",
        "完成现场复原、损失确认、事故调查与管理复盘。",
    ],
    "地震处理流程": [
        "发生地震时先就地掩护，停止危险动作。",
        "震动结束后由 ERC 组织点名、确认伤员与次生灾害。",
        "核查火灾、漏气、漏水、电力异常和结构损伤。",
        "按危险区域划设封锁并启动 ERT 处理。",
        "确认建筑与公辅安全后，逐步恢复系统。",
    ],
    "火灾处理流程": [
        "确认火警来源与火势等级，立即通知 ERC/IC。",
        "优先进行人员疏散与厂广播，切断相关能源。",
        "ERT 评估是否可初期灭火，必要时请求外部消防。",
        "控制周边易燃物并确认排风、气体与电力状态。",
        "扑灭后执行余火确认、损伤隔离和复产评估。",
    ],
    "气体泄漏处理流程": [
        "确认气体侦测或 MLG/GMS 报警并识别气体属性。",
        "立即封锁区域、疏散人员、确认 PPE 等级。",
        "切断阀组、稳定 exhaust/scrubber、进行气体复测。",
        "必要时扩大警戒区并请求厂外支援。",
        "复测达标后进入原因调查与恢复阶段。",
    ],
    "漏水处理流程": [
        "确认 Leak Sensor 与现场真实漏水点位。",
        "判断是否有触电、机台受损与大面积扩散风险。",
        "执行止漏、围堵、排水和设备防护。",
        "如影响生产或持续扩大，升级应急等级。",
        "完成现场复原、设备点检和损失统计。",
    ],
    "异味处理流程": [
        "确认异味区域与人员反馈，初判是否为气体、化学品或排水问题。",
        "检查 HVAC、Exhaust、Drain、Scrubber、sub-fab 和周边 module。",
        "局部隔离可疑区域并安排检测与复测。",
        "控制来源后通知相关部门恢复。",
        "记录调查结果并纳入后续改善。",
    ],
    "电力中断或压降处理流程": [
        "确认停电/压降范围与 EMS/GMS/门禁/CCTV 状态。",
        "核查 UPS、柴油机、排风、真空与关键机台保护状态。",
        "通知各区执行安全停机和 WIP 冻结。",
        "按优先级恢复公辅与机台，逐项确认 interlock。",
        "稳定后完成复机、损失确认与经验回收。",
    ],
    "化学品泄漏处理流程": [
        "确认化学品类别、禁忌关系和暴露风险。",
        "执行人员隔离、防化穿戴、围堵和洗消。",
        "阻断排水和扩散路径，收集废液与污染物。",
        "确认机台、地面和周边环境是否受影响。",
        "完成清理、复测、转运和后续调查。",
    ],
}


PHOTO_ERO_STRUCTURE = {
    "核心指挥": ["事故指挥官", "安全官", "公关", "财务"],
    "应急功能组": ["急救组", "救灾组", "疏散组", "管制组"],
    "支援编组": ["支援组长", "支援组员", "抢救1组", "搜寻1组", "抢救2组", "搜寻2组", "抢救3组", "搜寻3组", "抢救4组", "搜寻4组"],
    "专业支援": ["机械", "电力", "水课", "气化", "系统整合"],
}


REFERENCE_SUPPLEMENTS = {
    "ALOHA扩散模拟参考": [
        "用途：用于紧急事件应变，预测泄漏源下风处污染物浓度、气云移动与扩散范围。",
        "优点：由 USEPA 与 NOAA 维护、免费、输入参数相对简易、运算速度快。",
        "关键输入：化学品、地点、建筑型态、大气条件、来源型态（储槽/管线/集液池）与来源强度。",
        "输出重点：Threat Zone、毒性效应距离、热辐射、爆炸过压与文字摘要，可套叠地理图层。",
        "限制：分析多以 60 分钟内、10 公里内为主，未细致考虑地形、树木吸附与长期衰减。",
        "系统借鉴：可在 ERC 中加入下风向警戒圈、疏散半径、风向变化与资源部署建议。",
    ],
    "氯气危害预防及应变计划参考": [
        "场域特性：clean room 晶圆厂，24 小时 ERC 值班，并针对氯气建立完整危害预防与应变计划。",
        "侦测与警报：Honeywell Vertex 连续监测，最小刻度 0.04 ppm，第一段警报 0.5 ppm，第二段警报 1 ppm。",
        "工程控制：一旦泄漏，以 exhaust 持续将氯气导向洗涤塔处理；钢瓶存放于具抽气设备之气瓶柜。",
        "训练与演练：工程、厂务、制造等部门都纳入定期教育训练与演练，验证系统正常运作。",
        "应变资源：文件把资源拆成消防设备、泄漏警报设备、紧急处理器具、个人防护、通讯设备等类别。",
        "系统借鉴：可在 ERC 中补强警报门槛管理、器材盘点、外部支援、楼层配置图与医疗支援索引。",
    ],
}


def calculate_semiconductor_risk_score(
    severity: int,
    exposed_people: int,
    toxic_gas_risk: float,
    contamination_risk: float,
    utility_failure: float,
    tool_impact_count: int,
    mes_disrupted: bool,
) -> int:
    score = round(
        severity * 14
        + min(18, exposed_people / 12)
        + toxic_gas_risk * 18
        + contamination_risk * 15
        + utility_failure * 17
        + min(14, tool_impact_count * 1.4)
        + (8 if mes_disrupted else 0)
    )
    return max(0, min(100, score))


def classify_semiconductor_response_level(score: int) -> str:
    if score >= 85:
        return "厂级I级"
    if score >= 70:
        return "厂级II级"
    if score >= 52:
        return "厂级III级"
    return "厂级IV级"


def build_semiconductor_command_roster(
    commander: str,
    fab_name: str,
) -> pd.DataFrame:
    rows = [
        ("总指挥", commander, "封控升级、停线决策、对外汇报", f"{fab_name} EOC"),
        ("EHS应变组", "EHS值班经理", "危险源识别、PPE等级、隔离边界", "EOC / 事故前沿"),
        ("特气系统组", "特气站主管", "气柜切断、阀组隔离、尾气吸附确认", "特气站 / Sub-Fab"),
        ("化学品处置组", "化学仓主管", "围堵、洗消、废液转运", "化学品仓 / 湿制程区"),
        ("洁净室控制组", "洁净室值班工程师", "压差控制、交叉污染隔离、洁净恢复", "Fab Bay"),
        ("厂务保障组", "厂务值班长", "电力、UPW、CDA、真空、排风恢复", "公辅站"),
        ("设备恢复组", "设备部经理", "关键机台保全、批次冻结、开机条件确认", "设备监控席"),
        ("生产连续性组", "制造部值班长", "WIP冻结、批次追踪、交付影响评估", "MES / 调度席"),
        ("IT/MES组", "IT值班经理", "MES权限控制、告警联动、数据保全", "IT War Room"),
        ("医疗疏散组", "厂医与安保联席", "人员点名、检伤分类、转运路线", "集合点 / 医务室"),
    ]
    return pd.DataFrame(
        rows,
        columns=["职能", "负责人", "当前重点", "部署位置"],
    )


def build_semiconductor_objectives(
    incident_type: str,
    level: str,
    contamination_risk: float,
    mes_disrupted: bool,
) -> list[str]:
    objectives = [
        "10分钟内完成事故区域停留人员清点与电子门禁复核。",
        "优先切断危险介质和能量源，避免毒气扩散、化学反应失控或设备二次损伤。",
        "冻结受影响批次与机台状态，确保产品、履历和异常链路可追溯。",
    ]

    mapping = {
        "化灾": "快速围堵、吸附和洗消，防止化学品进入排水或与禁忌物反应。",
        "火灾": "确认火势边界、切断相关能源并优先组织人员疏散与初期灭火。",
        "气灾": "启动阀组切断、尾气吸收和气体检测复核，按风向与压差组织分级撤离。",
        "地震": "完成全厂点名、核查次生灾害，并优先确认结构、公辅和危险源状态。",
        "电力中断或压降": "维持 UPS、柴油机和关键排风连续，按序停机避免腔体与真空系统受损。",
        "异味": "沿 HVAC、Drain、Scrubber 和 sub-fab 路径追查来源，必要时局部停机。",
        "暴雨天气": "加密积水、边坡、地下机房和雨排巡检，提前布设沙包与抽排资源。",
        "台风天气": "关闭高风险户外作业，检查屋顶、门窗、围挡和厂区外围脆弱点。",
        "漏水事件": "优先止漏、导排和机台防护，避免触电、污染扩散和地板下方积水失控。",
    }
    objectives.append(mapping[incident_type])

    if contamination_risk >= 0.6:
        objectives.append("执行洁净恢复准入标准，未完成 particle / AMC / 压差验证前不得恢复生产。")
    if mes_disrupted:
        objectives.append("启用纸质或离线应急台账，确保批次、载具和处置记录不中断。")
    if level in {"厂级I级", "厂级II级"}:
        objectives.append("启动厂级跨部门会商，每15分钟滚动更新停线影响、环境数据和复产条件。")

    return objectives


def build_semiconductor_resource_board(
    level: str,
    toxic_gas_risk: float,
    utility_failure: float,
    tool_impact_count: int,
) -> pd.DataFrame:
    level_factor = {"厂级IV级": 1.0, "厂级III级": 1.25, "厂级II级": 1.55, "厂级I级": 1.9}[level]
    gas_boost = 1.0 + toxic_gas_risk * 0.45
    utility_boost = 1.0 + utility_failure * 0.5
    tool_boost = 1.0 + min(0.4, tool_impact_count / 50)

    resources = [
        ("SCBA应急小组", 4, gas_boost),
        ("便携式气体检测仪", 12, gas_boost),
        ("化学品围堵包", 8, 1.0 + toxic_gas_risk * 0.2),
        ("洁净恢复小组", 6, 1.0 + 0.5 * utility_boost),
        ("厂务抢修班", 8, utility_boost),
        ("备用发电/UPS保障组", 3, utility_boost),
        ("关键设备保全组", 7, tool_boost),
        ("批次追溯与调度席", 5, tool_boost),
    ]

    rows = []
    for name, base_ready, domain_boost in resources:
        ready = int(round(base_ready * level_factor * domain_boost))
        dispatched = max(1, int(round(ready * 0.6)))
        demand = int(round(dispatched * 1.2 + level_factor * 2))
        rows.append(
            {
                "资源类型": name,
                "已到位": ready,
                "已出动": min(ready, dispatched),
                "待命": max(0, ready - dispatched),
                "预测需求": demand,
                "缺口": max(0, demand - ready),
                "到位率": 0.0 if demand == 0 else min(1.0, ready / demand),
            }
        )
    return pd.DataFrame(rows)


def build_semiconductor_task_board(
    incident_type: str,
    level: str,
    cleanroom_recovery_progress: float,
) -> pd.DataFrame:
    high_priority = "高" if level in {"厂级I级", "厂级II级"} else "中"
    recovery_status = "恢复验证中" if cleanroom_recovery_progress >= 0.8 else "待净化完成"
    core_action = {
        "化灾": "完成化学品识别、围堵与洗消路径确认",
        "火灾": "完成火点边界确认、火警联动与疏散广播",
        "气灾": "完成 GMS / 阀组 / 排风 / scrubber 联动确认",
        "地震": "完成全厂点名与次生灾害扫描",
        "电力中断或压降": "确认主变、UPS、柴油机与关键公辅恢复顺序",
        "异味": "完成异味源追查并锁定可疑系统",
        "暴雨天气": "完成积水风险点巡查与抽排部署",
        "台风天气": "完成外围设施巡检与人力预布",
        "漏水事件": "完成止漏、导排与机台覆盖保护",
    }[incident_type]

    rows = [
        ("总指挥", "确认停线边界、上报厂级应变并发布统一口令", high_priority, "10分钟", "已发布"),
        ("EHS应变组", f"完成{incident_type}风险边界和 PPE 等级确认", high_priority, "10分钟", "执行中"),
        ("现场处置组", core_action, high_priority, "15分钟", "执行中"),
        ("化学品处置组", "完成围堵、吸附、废弃物收集与禁忌物复核", high_priority, "20分钟", "待收口"),
        ("洁净室控制组", f"洁净恢复进度 {cleanroom_recovery_progress:.0%}，复核压差与污染扩散", "高", "持续滚动", recovery_status),
        ("厂务保障组", "恢复 UPW / CDA / 真空 / 排风等关键公辅条件", high_priority, "30分钟", "抢修中"),
        ("设备恢复组", "冻结受影响机台并执行恢复前 checklist", "高", "30分钟", "待确认"),
        ("生产连续性组", "锁定受影响批次、载具与交付承诺窗口", "中", "25分钟", "排查中"),
        ("IT/MES组", "保全告警、履历与批次流转数据", "中", "20分钟", "已保全"),
    ]
    return pd.DataFrame(rows, columns=["职能", "任务", "优先级", "时限", "状态"])


def build_semiconductor_zone_status(
    incident_type: str,
    toxic_gas_risk: float,
    contamination_risk: float,
    utility_failure: float,
    cleanroom_recovery_progress: float,
) -> pd.DataFrame:
    base = {
        "化灾": 78,
        "火灾": 86,
        "气灾": 84,
        "地震": 82,
        "电力中断或压降": 73,
        "异味": 64,
        "暴雨天气": 60,
        "台风天气": 68,
        "漏水事件": 66,
    }[incident_type]

    rows = [
        ("事故Bay区", 1, 4, base + toxic_gas_risk * 10, 0.35, 0.30),
        ("Sub-Fab/管廊", 2, 3, 65 + toxic_gas_risk * 14 + utility_failure * 5, 0.20, 0.42),
        ("洁净生产区", 3, 3, 52 + contamination_risk * 18, 0.58, cleanroom_recovery_progress),
        ("化学品仓/湿制程", 4, 2, 50 + contamination_risk * 12, 0.30, 0.66),
        ("公辅站", 5, 2, 48 + utility_failure * 20, 0.22, 0.71),
        ("集合点/医疗区", 6, 1, 24 + toxic_gas_risk * 6, 0.74, 0.94),
    ]

    records = []
    for name, x_axis, y_axis, risk_index, density, mobility in rows:
        risk_index = min(100.0, round(risk_index, 1))
        if risk_index >= 85:
            status = "红色封控"
        elif risk_index >= 70:
            status = "橙色处置"
        elif risk_index >= 50:
            status = "黄色监控"
        else:
            status = "绿色受控"
        records.append(
            {
                "区域": name,
                "横轴": x_axis,
                "纵轴": y_axis,
                "风险指数": risk_index,
                "人员密度": min(1.0, round(density, 2)),
                "恢复度": min(1.0, round(mobility, 2)),
                "状态": status,
            }
        )
    return pd.DataFrame(records)


def build_semiconductor_facility_status(
    toxic_gas_risk: float,
    contamination_risk: float,
    utility_failure: float,
    mes_disrupted: bool,
) -> pd.DataFrame:
    rows = [
        ("毒气监测", 1 - toxic_gas_risk * 0.88, "0.42 ppm", "< 0.10 ppm", "维持气柜、走廊与排风末端三点复测"),
        ("洁净环境", 1 - contamination_risk * 0.82, "ISO 4 偏离", "恢复至 ISO 4", "恢复 particle / AMC / 压差联合验证"),
        ("排风废气", 1 - (toxic_gas_risk * 0.35 + utility_failure * 0.45), "Scrubber 92%", ">= 95%", "确认排风机与洗涤塔连续运行"),
        ("UPW/CDA/真空", 1 - utility_failure * 0.9, "UPW 76%", ">= 98%", "按机台优先级恢复公辅并复核 interlock"),
        ("MES/告警链路", 0.38 if mes_disrupted else 0.92, "降级运行" if mes_disrupted else "在线", "全链路在线", "同步保全 recipe、履历、批次锁定记录"),
    ]

    records = []
    for system, health, current, threshold, note in rows:
        health = max(0.0, min(1.0, round(health, 2)))
        if health < 0.45:
            status = "高风险"
        elif health < 0.7:
            status = "受扰"
        else:
            status = "可控"
        records.append(
            {
                "系统": system,
                "健康度": health,
                "当前读数": current,
                "控制阈值": threshold,
                "状态": status,
                "处置说明": note,
            }
        )
    return pd.DataFrame(records)


def build_semiconductor_wip_board(
    incident_type: str,
    tool_impact_count: int,
    cleanroom_recovery_progress: float,
    mes_disrupted: bool,
) -> pd.DataFrame:
    lots = max(8, int(round(tool_impact_count * 1.6)))
    release_eta = "待 MES 恢复" if mes_disrupted else ("2h 内复核" if cleanroom_recovery_progress >= 0.75 else "待复产条件满足")
    rows = [
        ("光刻", "CIS / PMIC", max(2, lots // 5), "全数冻结", "Recipe 与 reticle 复核中", release_eta),
        ("刻蚀", "MCU / Driver IC", max(2, lots // 4), "全数冻结", "腔体与真空恢复前禁止投片", "待设备保全"),
        ("薄膜沉积", "逻辑 / 模拟", max(1, lots // 6), "条件冻结", "需完成气路与 chamber clean", "待 EHS 放行"),
        ("湿制程", "功率器件", max(1, lots // 5), "全数冻结", "关注残液、残片和交叉污染", "待 UPW 恢复"),
        ("量测/测试", "工程片 / Monitor wafer", max(1, lots // 7), "限制流转", "仅允许验证批次运行", "按验证结果释放"),
    ]
    return pd.DataFrame(
        rows,
        columns=["工艺段", "关键产品", "受影响批次", "冻结状态", "当前约束", "释放条件"],
    )


def build_semiconductor_recovery_checklist(
    incident_type: str,
    contamination_risk: float,
    utility_failure: float,
    mes_disrupted: bool,
    cleanroom_recovery_progress: float,
) -> pd.DataFrame:
    rows = [
        ("环境放行", "Particle / AMC / 压差恢复至工艺标准", "洁净室控制组", cleanroom_recovery_progress >= 0.85),
        ("危险源隔离", f"{incident_type} 危险源确认切断并挂牌", "EHS应变组", contamination_risk <= 0.45),
        ("公辅恢复", "UPW / CDA / 真空 / 排风稳定 30 分钟", "厂务保障组", utility_failure <= 0.35),
        ("设备保全", "关键机台完成 checklist 与空跑验证", "设备恢复组", cleanroom_recovery_progress >= 0.7),
        ("批次追溯", "受影响批次与载具履历完整可回放", "生产连续性组", not mes_disrupted),
        ("管理放行", "总指挥批准复产窗口与节拍策略", "总指挥", False),
    ]

    records = []
    for gate, threshold, owner, passed in rows:
        records.append(
            {
                "复产关卡": gate,
                "判定标准": threshold,
                "责任方": owner,
                "状态": "已满足" if passed else "未满足",
            }
        )
    return pd.DataFrame(records)


def build_semiconductor_timeline(level: str, incident_type: str) -> pd.DataFrame:
    intensity = "15分钟" if level in {"厂级I级", "厂级II级"} else "30分钟"
    rows = [
        ("T+0", "中央监控室", f"确认 {incident_type} 并发布首报"),
        ("T+10", "EHS / 厂务", "完成人员清点、隔离边界、危险源切断"),
        ("T+20", "设备 / 制造", "冻结 WIP、锁定机台、保全关键设备"),
        ("T+30", "洁净室控制组", "输出首轮环境数据和洁净恢复评估"),
        ("T+45", "总指挥", f"组织一次 {intensity} 节奏的跨部门复盘"),
        ("T+60", "生产连续性组", "形成交付影响、客户沟通和复产窗口建议"),
    ]
    return pd.DataFrame(rows, columns=["时间节点", "主责团队", "关键动作"])


def build_taiwan_bcm_stage_board(
    incident_type: str,
    level: str,
    cleanroom_recovery_progress: float,
    mes_disrupted: bool,
) -> pd.DataFrame:
    rows = [
        (
            "应变处置",
            "小时-天",
            "控制灾害、人员搜救、限制影响范围",
            f"依 {incident_type} 预案执行隔离、广播、封控与现场控制",
            "ERC / ERT / EHS / FAC",
            "执行中",
        ),
        (
            "事件管理",
            "天-周",
            "稳定运行、沟通利害关系人、维持最低营运水平",
            "同步员工、客户、供应商与跨厂支援信息，滚动复核 RTO",
            "IC / 制造 / 供应链 / IT-MES",
            "协同中" if mes_disrupted else "持续中",
        ),
        (
            "营运恢复",
            "周-月",
            "恢复产能、释放批次、回到正常交付节奏",
            f"洁净恢复进度 {cleanroom_recovery_progress:.0%}，逐步恢复机台与产线",
            "制造 / 设备 / 厂务 / 品质",
            "恢复验证中" if cleanroom_recovery_progress < 0.85 else "进入复机",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=["阶段", "时间尺度", "阶段目标", "当前动作", "主责团队", "状态"],
    )


def build_cross_fab_support_board(
    fab_name: str,
    level: str,
    resource_gap: int,
    rollcall_missing: int,
    tool_impact_count: int,
) -> pd.DataFrame:
    support_intensity = "高" if level in {"厂级I级", "厂级II级"} else "中"
    rows = [
        (
            "台湾跨厂 CCTV",
            "实时画面共享",
            "已启用" if support_intensity == "高" else "待命",
            f"其他厂区可查看 {fab_name} 事故区域画面并协助资源判断",
        ),
        (
            "手机疏散点名",
            "员工位置回报",
            "已启用",
            f"当前失联 {rollcall_missing} 人，建议以 badge 与门禁记录交叉核对",
        ),
        (
            "跨厂 ERT 支援",
            "人员/装备调度",
            "请求中" if resource_gap > 0 else "待命",
            f"资源缺口 {resource_gap}，可预备调入特气/化学/厂务专长支援",
        ),
        (
            "产能重分配",
            "跨厂生产协同",
            "评估中" if tool_impact_count >= 12 else "暂不启动",
            f"受影响机台 {tool_impact_count} 台，评估是否调整其他厂区产能配置",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=["支援模块", "模式", "状态", "说明"],
    )


def build_badge_audit_board(
    cleanroom_inside_due: int,
    outdoor_assembly_due: int,
    rollcall_missing: int,
    mes_disrupted: bool,
) -> pd.DataFrame:
    rows = [
        (
            "门禁 badge 记录",
            "洁净室内 / 室外集合点",
            "已比对" if rollcall_missing <= 2 else "待补比对",
            "用于确认 Fab Bay、Sub-Fab、楼梯口与集合点最后刷卡记录",
        ),
        (
            "承包商签到",
            "施工 / PM / 维保",
            "重点复核",
            "对照 contractor in/out 名单，避免仅以正式员工名单点名",
        ),
        (
            "访客/交接班名单",
            "访客 / 交接班 / 夜班",
            "重点复核" if cleanroom_inside_due > 0 else "待命",
            "防止访客、换班与培训人员遗漏在洁净室或室外集合点外",
        ),
        (
            "系统可用性",
            "MES / 门禁 / CCTV",
            "降级运行" if mes_disrupted else "在线",
            "若系统受扰，点名应切换纸本与无线电二次回报机制",
        ),
        (
            "室外集合复核",
            f"集合点应到 {outdoor_assembly_due}",
            "已启动",
            "由安保与班组长在 A/B 集合点做二次点名与医疗观察确认",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=["核对来源", "覆盖范围", "状态", "说明"],
    )


def build_photo_checklist_library() -> pd.DataFrame:
    return pd.DataFrame(
        PHOTO_CHECKLIST_ITEMS,
        columns=["预案", "阶段", "主要工作内容", "执行单位"],
    )


def build_photo_process_library() -> dict[str, list[str]]:
    return PHOTO_PROCESS_LIBRARY


def build_photo_ero_structure() -> dict[str, list[str]]:
    return PHOTO_ERO_STRUCTURE


def build_reference_supplements() -> dict[str, list[str]]:
    return REFERENCE_SUPPLEMENTS


def get_taiwan_fab_sites() -> dict[str, dict[str, float | str]]:
    return TAIWAN_FAB_SITES


def build_chemical_ghs_profile(chemical_name: str) -> dict[str, str | list[str]]:
    return CHEMICAL_GHS_PROFILES.get(
        chemical_name,
        {
            "信号词": "注意",
            "GHS图示": ["待确认"],
            "主要危害": ["请以该化学品最新 SDS 与厂内化学品台账为准。"],
            "关键PPE": ["依现场 SDS 与 EHS 指示配置。"],
            "现场禁忌": ["未确认 GHS 与禁忌前，不得贸然处置。"],
            "首要动作": ["先确认化学品身份、风向、隔离边界与人员暴露情况。"],
        },
    )


def build_incident_control_profile(incident_type: str, fab_name: str) -> dict[str, str | int | float | bool]:
    profile = INCIDENT_CONTROL_PROFILES[incident_type].copy()
    profile["incident_name"] = f"{fab_name}{profile.pop('incident_suffix')}"
    return profile


def get_checklist_name_for_incident(incident_type: str) -> str:
    return INCIDENT_TO_CHECKLIST[incident_type]


def get_process_name_for_incident(incident_type: str) -> str:
    return INCIDENT_TO_PROCESS[incident_type]


def build_sop_execution_board(
    incident_type: str,
    level: str,
    toxic_gas_risk: float,
    contamination_risk: float,
    utility_failure: float,
    cleanroom_recovery_progress: float,
) -> pd.DataFrame:
    checklist_name = get_checklist_name_for_incident(incident_type)
    checklist = build_photo_checklist_library()
    stages = list(dict.fromkeys(checklist[checklist["预案"] == checklist_name]["阶段"].tolist()))

    if cleanroom_recovery_progress >= 0.85 and max(toxic_gas_risk, contamination_risk, utility_failure) < 0.35:
        current_index = len(stages) - 1
    elif level in {"厂级I级", "厂级II级"} or max(toxic_gas_risk, contamination_risk, utility_failure) >= 0.65:
        current_index = min(2, len(stages) - 1)
    else:
        current_index = min(1, len(stages) - 1)

    rows = []
    for index, stage in enumerate(stages):
        if index < current_index:
            status = "已完成"
        elif index == current_index:
            status = "当前节点"
        else:
            status = "待执行"
        stage_rows = checklist[(checklist["预案"] == checklist_name) & (checklist["阶段"] == stage)]
        key_action = stage_rows["主要工作内容"].iloc[0]
        owner = stage_rows["执行单位"].iloc[0]
        rows.append((index + 1, stage, status, owner, key_action))

    return pd.DataFrame(rows, columns=["顺序", "阶段", "状态", "执行单位", "关键动作"])


def build_monitoring_interface_board(
    fab_name: str,
    incident_type: str,
    incident_area: str,
    chemical_name: str,
    toxic_gas_risk: float,
    utility_failure: float,
) -> pd.DataFrame:
    rows = [
        ("CCTV", "接口预留", "在线", incident_area, "事故区域、走廊、集合点画面可接入统一监控墙"),
        (
            "GMS",
            "接口预留",
            "报警中" if incident_type in {"气灾", "化灾"} and toxic_gas_risk >= 0.35 else "监看中",
            f"{incident_area} / {chemical_name}",
            "需接入点位读值、阈值、报警位置和阀组联动状态",
        ),
        (
            "火警报警",
            "接口预留",
            "报警中" if incident_type == "火灾" else "待命",
            incident_area,
            "需接入火警回路、探测器地址与防排烟联动状态",
        ),
        (
            "厂广播",
            "接口预留",
            "已准备" if incident_type in {"火灾", "气灾", "地震", "漏水事件"} else "待命",
            fab_name,
            "需接入广播分区、播报模板和回传确认状态",
        ),
        (
            "门禁 / 点名",
            "接口预留",
            "在线" if utility_failure < 0.75 else "降级",
            "洁净室 / 室外集合点",
            "需接入 badge、集合点和访客/承包商名单对账",
        ),
    ]
    return pd.DataFrame(rows, columns=["系统", "接口状态", "运行状态", "报警位置", "说明"])


def build_gms_sensor_board(
    incident_type: str,
    incident_area: str,
    chemical_name: str,
    toxic_gas_risk: float,
) -> pd.DataFrame:
    base_ppm = round(max(0.02, toxic_gas_risk * 1.2), 2)
    gas_name = chemical_name if incident_type in {"气灾", "化灾"} else "复合气体"
    rows = [
        ("GMS-01", gas_name, base_ppm, "0.50 ppm", "报警" if base_ppm >= 0.5 else "预警", f"{incident_area} 北侧气柜"),
        ("GMS-02", gas_name, round(base_ppm * 0.72, 2), "0.50 ppm", "预警" if base_ppm >= 0.3 else "正常", f"{incident_area} 走廊中段"),
        ("GMS-03", gas_name, round(base_ppm * 0.48, 2), "0.50 ppm", "正常", f"{incident_area} 排风末端"),
    ]
    return pd.DataFrame(rows, columns=["点位", "气体", "读值", "报警阈值", "状态", "报警位置"])


def fetch_live_weather_snapshot(latitude: float, longitude: float) -> dict[str, float | str | None]:
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ],
            "timezone": "Asia/Taipei",
            "wind_speed_unit": "ms",
        },
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    current = payload.get("current", {})
    return {
        "timestamp": current.get("time"),
        "temperature_c": current.get("temperature_2m"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "wind_speed_ms": current.get("wind_speed_10m"),
        "wind_direction_deg": current.get("wind_direction_10m"),
        "wind_gust_ms": current.get("wind_gusts_10m"),
    }


def describe_wind_direction(degrees: float | None) -> str:
    if degrees is None:
        return "未知"
    directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    index = int((float(degrees) + 22.5) // 45) % 8
    return directions[index]


def build_aloha_quick_estimate(
    chemical_name: str,
    release_rate_kg_min: float,
    duration_min: int,
    wind_speed_ms: float,
    temperature_c: float,
    humidity_pct: float,
) -> pd.DataFrame:
    released_mass = max(0.0, release_rate_kg_min * duration_min)
    weather_factor = 1.0
    if wind_speed_ms <= 2:
        weather_factor += 0.35
    elif wind_speed_ms <= 4:
        weather_factor += 0.18
    if humidity_pct >= 80:
        weather_factor += 0.08
    if temperature_c >= 30:
        weather_factor += 0.06

    base = (released_mass ** 0.55) * 95 * weather_factor
    red = int(round(max(80, base)))
    orange = int(round(red * 1.8))
    yellow = int(round(orange * 1.7))

    rows = [
        ("红区", f"{chemical_name} 高危暴露区", red, "仅允许穿戴完整防护的 ERT 进入"),
        ("橙区", "控制与侦检区", orange, "限制进出，布设风向标与气体检测"),
        ("黄区", "警戒与疏散提示区", yellow, "进行人员疏散、交通管制与广播"),
    ]
    return pd.DataFrame(rows, columns=["区域", "说明", "半径米", "行动建议"])


def build_semiconductor_alert_board(
    level: str,
    toxic_gas_risk: float,
    contamination_risk: float,
    resource_gap: int,
    rollcall_missing: int,
    mes_disrupted: bool,
) -> pd.DataFrame:
    alerts: list[tuple[str, str, str, str, str]] = []

    if toxic_gas_risk >= 0.65:
        alerts.append(
            (
                "gas_zone",
                "毒气下风向风险",
                "P1",
                "EHS应变组",
                "立即复核风向、扩大警戒并准备 ALOHA 下风向推估。",
            )
        )
    if contamination_risk >= 0.6:
        alerts.append(
            (
                "cleanroom_spread",
                "洁净室交叉污染风险",
                "P1",
                "洁净室控制组",
                "限制相邻 Bay 流转，优先完成 particle / AMC / 压差复测。",
            )
        )
    if resource_gap > 0:
        alerts.append(
            (
                "resource_gap",
                "关键应变资源存在缺口",
                "P2",
                "厂务保障组",
                f"当前缺口 {resource_gap}，评估启动跨厂 ERT 或外部支援。",
            )
        )
    if rollcall_missing > 0:
        alerts.append(
            (
                "rollcall_gap",
                "点名尚未闭环",
                "P1",
                "安保 / 班组长",
                f"当前失联 {rollcall_missing} 人，需以 badge、门禁与集合点名单二次复核。",
            )
        )
    if mes_disrupted:
        alerts.append(
            (
                "mes_degraded",
                "MES / 告警链路降级",
                "P2",
                "IT/MES组",
                "切换离线台账、保全履历并验证门禁与广播链路。",
            )
        )
    if level in {"厂级I级", "厂级II级"}:
        alerts.append(
            (
                "high_response",
                "高等级应变运行中",
                "P2",
                "总指挥",
                "维持 15 分钟复盘节奏，并同步客户/供应链/跨厂支援信息。",
            )
        )

    return pd.DataFrame(
        alerts,
        columns=["告警ID", "标题", "优先级", "责任方", "建议动作"],
    )


def apply_rollcall_override(
    rollcall_board: pd.DataFrame,
    zone: str,
    arrived: int,
    medical_observe: int,
) -> pd.DataFrame:
    updated = rollcall_board.copy()
    mask = updated["区域"] == zone
    if not mask.any():
        return updated

    due = int(updated.loc[mask, "应到"].iloc[0])
    arrived = max(0, min(due, int(arrived)))
    medical_observe = max(0, min(arrived, int(medical_observe)))
    missing = max(0, due - arrived)
    rate = 0.0 if due == 0 else round(arrived / due, 2)
    if missing == 0:
        status = "完成点名"
    elif rate >= 0.85:
        status = "二次复核"
    else:
        status = "立即搜寻"

    updated.loc[mask, "已到"] = arrived
    updated.loc[mask, "失联"] = missing
    updated.loc[mask, "医疗观察"] = medical_observe
    updated.loc[mask, "到位率"] = rate
    updated.loc[mask, "状态"] = status
    return updated


def build_semiconductor_rollcall_board(
    cleanroom_inside_due: int,
    outdoor_assembly_due: int,
    toxic_gas_risk: float,
    contamination_risk: float,
) -> pd.DataFrame:
    subfab_due = max(0, round(cleanroom_inside_due * 0.28))
    indoor_arrived = max(0, round(cleanroom_inside_due * (0.84 - toxic_gas_risk * 0.10)))
    subfab_arrived = max(0, round(subfab_due * (0.78 - toxic_gas_risk * 0.14)))
    outdoor_a_due = max(0, round(outdoor_assembly_due * 0.55))
    outdoor_b_due = max(0, outdoor_assembly_due - outdoor_a_due)
    outdoor_a_arrived = max(0, round(outdoor_a_due * (0.93 - contamination_risk * 0.04)))
    outdoor_b_arrived = max(0, round(outdoor_b_due * (0.89 - toxic_gas_risk * 0.05)))

    rows = [
        ("洁净室内 Fab Bay", "洁净室内", cleanroom_inside_due, indoor_arrived, round(cleanroom_inside_due * max(0.04, contamination_risk * 0.08)), "继续扫描 badge 与机台区撤离点"),
        ("Sub-Fab / 设备夹层", "洁净室内", subfab_due, subfab_arrived, round(subfab_due * max(0.05, toxic_gas_risk * 0.10)), "优先复核气柜、楼梯口与排风平台"),
        ("室外集合点 A", "室外", outdoor_a_due, outdoor_a_arrived, round(outdoor_a_due * 0.03), "对照班组名单二次点名"),
        ("室外集合点 B", "室外", outdoor_b_due, outdoor_b_arrived, round(outdoor_b_due * 0.05), "复核承包商、访客与交接班人员"),
    ]

    records = []
    for zone, zone_type, due, arrived, medical_observe, action in rows:
        due = max(0, int(due))
        arrived = max(0, min(due, int(arrived)))
        medical_observe = max(0, min(arrived, int(medical_observe)))
        missing = max(0, due - arrived)
        rate = 0.0 if due == 0 else round(arrived / due, 2)
        if missing == 0:
            status = "完成点名"
        elif rate >= 0.85:
            status = "二次复核"
        else:
            status = "立即搜寻"
        records.append(
            {
                "区域": zone,
                "类型": zone_type,
                "应到": due,
                "已到": arrived,
                "失联": missing,
                "医疗观察": medical_observe,
                "到位率": rate,
                "状态": status,
                "下一动作": action,
            }
        )
    return pd.DataFrame(records)


def default_semiconductor_log(
    fab_name: str,
    incident_type: str,
    level: str,
    commander: str,
) -> list[dict[str, str]]:
    now = datetime.now().replace(second=0, microsecond=0)
    items = [
        (0, "接警", "中央监控室", f"{fab_name} 发生{incident_type}，按 {level} 启动厂级应变。"),
        (6, "调度", commander, "EHS、厂务、设备、制造、IT/MES 已进入 EOC。"),
        (13, "环境回报", "EHS应变组", "事故区域已封控，气体检测和压差监测持续回传。"),
        (21, "生产回报", "生产连续性组", "受影响批次已冻结，机台与载具状态已锁定。"),
    ]
    records = []
    for minutes, category, sender, content in items:
        timestamp = now - timedelta(minutes=minutes)
        records.append(
            {
                "时间": timestamp.strftime("%H:%M"),
                "类别": category,
                "发送方": sender,
                "内容": content,
            }
        )
    return records
