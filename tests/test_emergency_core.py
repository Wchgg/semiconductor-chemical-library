from __future__ import annotations

from emergency_app.core import (
    build_resource_board,
    build_sector_status,
    build_task_board,
    calculate_incident_score,
    classify_response_level,
)


def test_calculate_incident_score_caps_at_100() -> None:
    score = calculate_incident_score(
        severity=5,
        affected_people=5000,
        critical_sites=10,
        weather_risk=1.0,
        medical_pressure=1.0,
        communications_disrupted=True,
    )
    assert score == 100


def test_classify_response_level_uses_expected_thresholds() -> None:
    assert classify_response_level(48) == "IV级响应"
    assert classify_response_level(55) == "III级响应"
    assert classify_response_level(72) == "II级响应"
    assert classify_response_level(90) == "I级响应"


def test_build_resource_board_contains_gap_and_ratio_columns() -> None:
    board = build_resource_board(level="II级响应", affected_people=300, medical_pressure=0.5)
    assert {"资源类型", "缺口", "到位率"}.issubset(board.columns)
    assert (board["缺口"] >= 0).all()
    assert ((board["到位率"] >= 0) & (board["到位率"] <= 1)).all()


def test_build_sector_status_returns_multiple_control_zones() -> None:
    sector_status = build_sector_status(
        severity=4,
        affected_people=260,
        weather_risk=0.5,
        evacuation_progress=0.68,
    )
    assert len(sector_status) == 5
    assert "核心处置区" in sector_status["区域"].tolist()
    assert sector_status["风险指数"].max() <= 100


def test_build_task_board_reflects_evacuation_progress() -> None:
    tasks = build_task_board("危化品泄漏", "II级响应", evacuation_progress=0.62)
    progress_task = tasks[tasks["职能"] == "情报研判组"].iloc[0]
    assert "62%" in progress_task["任务"]
    assert progress_task["状态"] == "进行中"
