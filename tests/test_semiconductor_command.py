from __future__ import annotations

from pathlib import Path

from emergency_app.semiconductor import (
    apply_rollcall_override,
    authenticate_user,
    build_aloha_quick_estimate,
    build_badge_audit_board,
    build_chemical_ghs_profile,
    build_default_user_accounts,
    build_incident_control_profile,
    build_gms_sensor_board,
    build_monitoring_interface_board,
    build_reference_supplements,
    build_semiconductor_alert_board,
    build_semiconductor_facility_status,
    build_photo_checklist_library,
    build_photo_ero_structure,
    build_photo_process_library,
    build_cross_fab_support_board,
    build_semiconductor_recovery_checklist,
    build_semiconductor_rollcall_board,
    build_semiconductor_resource_board,
    build_sop_execution_board,
    build_semiconductor_task_board,
    build_taiwan_bcm_stage_board,
    build_user_role_matrix,
    build_semiconductor_wip_board,
    build_semiconductor_zone_status,
    calculate_semiconductor_risk_score,
    classify_semiconductor_response_level,
    describe_wind_direction,
    get_checklist_name_for_incident,
    get_process_name_for_incident,
    get_taiwan_fab_sites,
    hash_user_password,
    load_user_accounts,
    save_user_accounts,
    set_user_active_status,
    upsert_user_account,
)


def test_calculate_semiconductor_risk_score_caps_at_100() -> None:
    score = calculate_semiconductor_risk_score(
        severity=5,
        exposed_people=1000,
        toxic_gas_risk=1.0,
        contamination_risk=1.0,
        utility_failure=1.0,
        tool_impact_count=80,
        mes_disrupted=True,
    )
    assert score == 100


def test_classify_semiconductor_response_level_thresholds() -> None:
    assert classify_semiconductor_response_level(45) == "厂级IV级"
    assert classify_semiconductor_response_level(60) == "厂级III级"
    assert classify_semiconductor_response_level(75) == "厂级II级"
    assert classify_semiconductor_response_level(92) == "厂级I级"


def test_hash_user_password_is_stable() -> None:
    assert hash_user_password("ERCAdmin#2026!") == hash_user_password("ERCAdmin#2026!")
    assert hash_user_password("ERCAdmin#2026!") != hash_user_password("ERCViewer#2026!")


def test_load_user_accounts_creates_defaults(tmp_path: Path) -> None:
    accounts_path = tmp_path / "users.json"
    accounts = load_user_accounts(accounts_path)
    assert accounts_path.exists()
    assert {str(account["username"]) for account in accounts} == {"admin", "commander", "ehs", "viewer"}


def test_authenticate_user_accepts_active_account() -> None:
    accounts = build_default_user_accounts()
    user = authenticate_user(accounts, username="admin", password="ERCAdmin#2026!")
    assert user is not None
    assert user["role"] == "系统管理员"


def test_authenticate_user_rejects_inactive_account() -> None:
    accounts = set_user_active_status(build_default_user_accounts(), "admin", active=False)
    user = authenticate_user(accounts, username="admin", password="ERCAdmin#2026!")
    assert user is None


def test_upsert_user_account_updates_existing_password_and_role() -> None:
    accounts = build_default_user_accounts()
    updated = upsert_user_account(
        accounts,
        username="ehs",
        display_name="EHS 夜班",
        role="指挥官",
        password="Updated@2026",
        active=True,
    )
    user = authenticate_user(updated, username="ehs", password="Updated@2026")
    assert user is not None
    assert user["display_name"] == "EHS 夜班"
    assert user["role"] == "指挥官"


def test_upsert_user_account_appends_new_account() -> None:
    accounts = build_default_user_accounts()
    updated = upsert_user_account(
        accounts,
        username="shiftlead",
        display_name="值班长",
        role="指挥官",
        password="ShiftLead@2026",
        active=True,
    )
    assert authenticate_user(updated, username="shiftlead", password="ShiftLead@2026") is not None


def test_save_user_accounts_roundtrip(tmp_path: Path) -> None:
    accounts_path = tmp_path / "users.json"
    accounts = upsert_user_account(
        build_default_user_accounts(),
        username="observer2",
        display_name="观察员二号",
        role="观察员",
        password="Observer@2026",
        active=False,
    )
    save_user_accounts(accounts_path, accounts)
    reloaded = load_user_accounts(accounts_path)
    assert any(str(account["username"]) == "observer2" and not bool(account["active"]) for account in reloaded)


def test_build_user_role_matrix_contains_permissions_column() -> None:
    matrix = build_user_role_matrix(build_default_user_accounts())
    assert list(matrix.columns) == ["账号", "姓名", "角色", "状态", "权限"]
    admin_row = matrix[matrix["账号"] == "admin"].iloc[0]
    assert "用户管理" in str(admin_row["权限"])


def test_build_semiconductor_resource_board_has_valid_ratios() -> None:
    board = build_semiconductor_resource_board(
        level="厂级II级",
        toxic_gas_risk=0.8,
        utility_failure=0.5,
        tool_impact_count=20,
    )
    assert not board.empty
    assert ((board["到位率"] >= 0) & (board["到位率"] <= 1)).all()
    assert (board["缺口"] >= 0).all()


def test_build_semiconductor_zone_status_includes_core_areas() -> None:
    zones = build_semiconductor_zone_status(
        incident_type="气灾",
        toxic_gas_risk=0.75,
        contamination_risk=0.5,
        utility_failure=0.4,
        cleanroom_recovery_progress=0.35,
    )
    assert len(zones) == 6
    assert "事故Bay区" in zones["区域"].tolist()
    assert zones["风险指数"].max() <= 100


def test_build_semiconductor_task_board_reflects_cleanroom_recovery_progress() -> None:
    tasks = build_semiconductor_task_board(
        incident_type="化灾",
        level="厂级II级",
        cleanroom_recovery_progress=0.34,
    )
    cleanroom_task = tasks[tasks["职能"] == "洁净室控制组"].iloc[0]
    assert "34%" in cleanroom_task["任务"]
    assert cleanroom_task["状态"] == "待净化完成"


def test_build_semiconductor_facility_status_marks_mes_disruption() -> None:
    facility = build_semiconductor_facility_status(
        toxic_gas_risk=0.7,
        contamination_risk=0.5,
        utility_failure=0.4,
        mes_disrupted=True,
    )
    mes_row = facility[facility["系统"] == "MES/告警链路"].iloc[0]
    assert mes_row["状态"] == "高风险"


def test_build_semiconductor_wip_board_returns_positive_lot_counts() -> None:
    wip = build_semiconductor_wip_board(
        incident_type="气灾",
        tool_impact_count=18,
        cleanroom_recovery_progress=0.4,
        mes_disrupted=False,
    )
    assert (wip["受影响批次"] > 0).all()


def test_build_semiconductor_recovery_checklist_reflects_unmet_conditions() -> None:
    checklist = build_semiconductor_recovery_checklist(
        incident_type="电力中断或压降",
        contamination_risk=0.7,
        utility_failure=0.6,
        mes_disrupted=True,
        cleanroom_recovery_progress=0.5,
    )
    assert "未满足" in checklist["状态"].tolist()


def test_build_photo_checklist_library_contains_photo_titles() -> None:
    library = build_photo_checklist_library()
    assert "火灾应急CheckList" in library["预案"].tolist()
    assert "漏水事件应急CheckList" in library["预案"].tolist()


def test_build_photo_process_library_contains_major_flows() -> None:
    process_library = build_photo_process_library()
    assert "紧急应变指挥官处理流程" in process_library
    assert "化学品泄漏处理流程" in process_library


def test_build_photo_ero_structure_contains_core_roles() -> None:
    structure = build_photo_ero_structure()
    assert "核心指挥" in structure
    assert "事故指挥官" in structure["核心指挥"]


def test_build_semiconductor_rollcall_board_contains_indoor_and_outdoor() -> None:
    rollcall = build_semiconductor_rollcall_board(
        cleanroom_inside_due=60,
        outdoor_assembly_due=30,
        toxic_gas_risk=0.7,
        contamination_risk=0.4,
    )
    assert "洁净室内" in rollcall["类型"].tolist()
    assert "室外" in rollcall["类型"].tolist()
    assert (rollcall["失联"] >= 0).all()


def test_build_taiwan_bcm_stage_board_contains_three_stages() -> None:
    stages = build_taiwan_bcm_stage_board(
        incident_type="气灾",
        level="厂级II级",
        cleanroom_recovery_progress=0.4,
        mes_disrupted=True,
    )
    assert stages["阶段"].tolist() == ["应变处置", "事件管理", "营运恢复"]


def test_build_cross_fab_support_board_contains_cctv_and_rollcall() -> None:
    support = build_cross_fab_support_board(
        fab_name="Fab 12A",
        level="厂级II级",
        resource_gap=3,
        rollcall_missing=4,
        tool_impact_count=18,
    )
    assert "台湾跨厂 CCTV" in support["支援模块"].tolist()
    assert "手机疏散点名" in support["支援模块"].tolist()


def test_build_badge_audit_board_contains_badge_and_contractor_checks() -> None:
    audit = build_badge_audit_board(
        cleanroom_inside_due=40,
        outdoor_assembly_due=25,
        rollcall_missing=5,
        mes_disrupted=False,
    )
    assert "门禁 badge 记录" in audit["核对来源"].tolist()
    assert "承包商签到" in audit["核对来源"].tolist()


def test_build_reference_supplements_contains_aloha_and_chlorine() -> None:
    refs = build_reference_supplements()
    assert "ALOHA扩散模拟参考" in refs
    assert "氯气危害预防及应变计划参考" in refs


def test_build_semiconductor_alert_board_contains_expected_alerts() -> None:
    alerts = build_semiconductor_alert_board(
        level="厂级II级",
        toxic_gas_risk=0.8,
        contamination_risk=0.65,
        resource_gap=3,
        rollcall_missing=2,
        mes_disrupted=True,
    )
    assert "毒气下风向风险" in alerts["标题"].tolist()
    assert "点名尚未闭环" in alerts["标题"].tolist()


def test_apply_rollcall_override_updates_status_and_missing() -> None:
    board = build_semiconductor_rollcall_board(
        cleanroom_inside_due=40,
        outdoor_assembly_due=20,
        toxic_gas_risk=0.6,
        contamination_risk=0.4,
    )
    zone = board["区域"].iloc[0]
    updated = apply_rollcall_override(board, zone=zone, arrived=40, medical_observe=2)
    row = updated[updated["区域"] == zone].iloc[0]
    assert row["状态"] == "完成点名"
    assert row["失联"] == 0


def test_get_taiwan_fab_sites_contains_coordinates() -> None:
    sites = get_taiwan_fab_sites()
    assert "新竹 Fab 12A" in sites
    assert sites["台南 Fab 18A"]["lat"] > 20
    assert sites["高雄 Fab 22"]["lon"] > 120


def test_describe_wind_direction_returns_expected_labels() -> None:
    assert describe_wind_direction(None) == "未知"
    assert describe_wind_direction(0) == "北"
    assert describe_wind_direction(90) == "东"
    assert describe_wind_direction(225) == "西南"


def test_build_aloha_quick_estimate_returns_three_zone_layout() -> None:
    estimate = build_aloha_quick_estimate(
        chemical_name="氯气",
        release_rate_kg_min=4.5,
        duration_min=15,
        wind_speed_ms=2.2,
        temperature_c=29,
        humidity_pct=84,
    )
    assert estimate["区域"].tolist() == ["红区", "橙区", "黄区"]
    assert estimate["半径米"].is_monotonic_increasing
    assert "氯气" in estimate.iloc[0]["说明"]


def test_build_chemical_ghs_profile_contains_expected_fields() -> None:
    profile = build_chemical_ghs_profile("氢氟酸")
    assert profile["信号词"] == "危险"
    assert "腐蚀" in profile["GHS图示"]
    assert any("葡萄糖酸钙" in item for item in profile["首要动作"])


def test_build_chemical_ghs_profile_returns_fallback_for_unknown_chemical() -> None:
    profile = build_chemical_ghs_profile("未知化学品")
    assert profile["信号词"] == "注意"
    assert profile["GHS图示"] == ["待确认"]


def test_build_incident_control_profile_returns_consistent_defaults() -> None:
    profile = build_incident_control_profile("气灾", "台南 Fab 18A")
    assert profile["incident_name"] == "台南 Fab 18A气灾联动处置"
    assert profile["incident_area"] == "A栋 Gas Cabinet / Sub-Fab"
    assert profile["chemical_name"] == "氯气"
    assert float(profile["inside_ratio"]) < 1.0


def test_get_checklist_and_process_name_for_incident() -> None:
    assert get_checklist_name_for_incident("火灾") == "火灾应急CheckList"
    assert get_process_name_for_incident("漏水事件") == "漏水处理流程"


def test_build_sop_execution_board_contains_current_node() -> None:
    board = build_sop_execution_board(
        incident_type="气灾",
        level="厂级II级",
        toxic_gas_risk=0.8,
        contamination_risk=0.3,
        utility_failure=0.2,
        cleanroom_recovery_progress=0.2,
    )
    assert "当前节点" in board["状态"].tolist()
    assert board.iloc[0]["阶段"] == "事故发生"


def test_build_monitoring_interface_board_contains_required_interfaces() -> None:
    board = build_monitoring_interface_board(
        fab_name="台南 Fab 18A",
        incident_type="气灾",
        incident_area="A栋 Gas Cabinet / Sub-Fab",
        chemical_name="氯气",
        toxic_gas_risk=0.8,
        utility_failure=0.3,
    )
    assert set(["CCTV", "GMS", "火警报警", "厂广播"]).issubset(set(board["系统"].tolist()))


def test_build_gms_sensor_board_contains_readings_and_locations() -> None:
    board = build_gms_sensor_board(
        incident_type="气灾",
        incident_area="A栋 Gas Cabinet / Sub-Fab",
        chemical_name="氯气",
        toxic_gas_risk=0.8,
    )
    assert "读值" in board.columns
    assert "报警位置" in board.columns
    assert board["读值"].max() > 0
