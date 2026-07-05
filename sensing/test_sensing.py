"""
Task 2 感知模块测试脚本。

运行方式:
    cd sensing
    python test_sensing.py

测试内容:
1. 单次生成全部 6 种 Mock 场景
2. 每 5 秒循环切换场景（持续 60 秒）
3. 验证字段完整性
"""

import time
import json

from mock_generator import (
    generate_study_state,
    get_available_scenarios,
    print_state,
)
from focus_detector import calculate_focus_score, is_effective_learning
from fatigue_detector import calculate_fatigue_score, is_fatigue_alert
from distraction_detector import (
    determine_distraction_level,
    get_level_description,
    DistractionLevel,
)

REQUIRED_FIELDS = [
    "sessionId", "timestamp", "elapsedSeconds",
    "focusScore", "fatigueScore", "distractionLevel",
    "emotion", "currentScene", "isUserPresent",
    "headDownSeconds", "eyeClosedRatio", "distractionCount",
]


def validate_study_state(state: dict) -> list[str]:
    """验证 StudyState 字段完整性，返回缺失字段列表"""
    missing = [f for f in REQUIRED_FIELDS if f not in state]
    return missing


def test_all_scenarios_once():
    """测试 1：一次性生成全部 6 种场景并验证"""
    print("\n" + "=" * 60)
    print("  测试 1：全部 6 种 Mock 场景生成")
    print("=" * 60)

    scenarios = get_available_scenarios()
    all_passed = True

    for scenario in scenarios:
        state = generate_study_state(scenario=scenario)
        print_state(state)

        # 验证字段
        missing = validate_study_state(state)
        if missing:
            print(f"  [FAIL] 缺失字段: {missing}")
            all_passed = False
        else:
            print(f"  [PASS] 字段完整")

        # 验证值范围
        if not (0 <= state["focusScore"] <= 100):
            print(f"  [FAIL] focusScore 超出 0-100 范围: {state['focusScore']}")
            all_passed = False
        if not (0 <= state["fatigueScore"] <= 100):
            print(f"  [FAIL] fatigueScore 超出 0-100 范围: {state['fatigueScore']}")
            all_passed = False
        if state["distractionLevel"] not in ["NONE", "L1", "L2", "L3"]:
            print(f"  [FAIL] distractionLevel 非法值: {state['distractionLevel']}")
            all_passed = False

    return all_passed


def test_scenario_loop():
    """测试 2：每 5 秒循环切换场景，持续约 60 秒"""
    print("\n" + "=" * 60)
    print("  测试 2：循环输出 StudyState（每 5 秒一次）")
    print("  运行中，请观察控制台输出...")
    print("=" * 60)

    scenario_order = [
        "normal_focus",
        "slight_distract",
        "severe_distract",
        "high_fatigue",
        "away_from_seat",
        "recovery_focus",
    ]

    elapsed = 0
    cycle_count = 0
    try:
        # 运行 2 轮（12 次输出，约 60 秒）
        while cycle_count < 2:
            for scenario in scenario_order:
                state = generate_study_state(
                    scenario=scenario,
                    elapsed_offset=elapsed,
                )
                print_state(state)
                elapsed += 5
                time.sleep(5)
            cycle_count += 1
    except KeyboardInterrupt:
        print("\n  用户中断循环。")


def test_unit_functions():
    """测试 3：单元函数正确性验证"""
    print("\n" + "=" * 60)
    print("  测试 3：核心函数单元验证")
    print("=" * 60)

    all_passed = True

    # 测试 focus_detector
    score = calculate_focus_score(
        head_down_seconds=0, eye_closed_ratio=0,
        distraction_count=0, is_user_present=True
    )
    assert score == 100, f"理想状态应为 100，实际 {score}"
    print(f"  [PASS] 理想状态 focusScore={score}")

    score = calculate_focus_score(
        head_down_seconds=5, eye_closed_ratio=0.1,
        distraction_count=2, is_user_present=True
    )
    assert 80 <= score <= 95, f"正常状态应在 80-95，实际 {score}"
    print(f"  [PASS] 正常轻微影响 focusScore={score}")

    score = calculate_focus_score(
        head_down_seconds=0, eye_closed_ratio=0,
        distraction_count=0, is_user_present=False
    )
    assert score <= 40, f"离座状态应 <=40，实际 {score}"
    print(f"  [PASS] 离座状态 focusScore={score}")

    # 测试 fatigue_detector
    score = calculate_fatigue_score(
        elapsed_seconds=60, eye_closed_ratio=0.0, head_down_seconds=0
    )
    assert score <= 5, f"学习1分钟疲劳应很低，实际 {score}"
    print(f"  [PASS] 1分钟学习 fatigueScore={score}")

    score = calculate_fatigue_score(
        elapsed_seconds=3600, eye_closed_ratio=0.3, head_down_seconds=20
    )
    assert score > 60, f"学习1小时+高闭眼+低头应 >60，实际 {score}"
    print(f"  [PASS] 高疲劳场景 fatigueScore={score}")

    # 测试 distraction_detector
    level = determine_distraction_level(
        is_user_present=True, gaze_away_seconds=5,
        continuous_distraction_seconds=0, is_entertainment_app=False,
    )
    assert level == "NONE", f"应 NONE，实际 {level}"
    print(f"  [PASS] 正常状态 distractionLevel={level}")

    level = determine_distraction_level(
        is_user_present=True, gaze_away_seconds=25,
        continuous_distraction_seconds=0, is_entertainment_app=False,
    )
    assert level == "L1", f"视线偏离>20s 应 L1，实际 {level}"
    print(f"  [PASS] 视线偏离25s distractionLevel={level}")

    level = determine_distraction_level(
        is_user_present=True, gaze_away_seconds=10,
        continuous_distraction_seconds=75, is_entertainment_app=False,
    )
    assert level == "L2", f"连续分心>60s 应 L2，实际 {level}"
    print(f"  [PASS] 连续分心75s distractionLevel={level}")

    level = determine_distraction_level(
        is_user_present=False, gaze_away_seconds=0,
        continuous_distraction_seconds=0, is_entertainment_app=False,
    )
    assert level == "L3", f"离座应 L3，实际 {level}"
    print(f"  [PASS] 离座 distractionLevel={level}")

    level = determine_distraction_level(
        is_user_present=True, gaze_away_seconds=0,
        continuous_distraction_seconds=0, is_entertainment_app=True,
    )
    assert level == "L3", f"娱乐App应 L3，实际 {level}"
    print(f"  [PASS] 娱乐App distractionLevel={level}")

    # 测试有效学习判断
    assert is_effective_learning(75) is True
    assert is_effective_learning(70) is False
    assert is_effective_learning(65) is False
    print(f"  [PASS] 有效学习阈值 focusScore>70 正确")

    # 测试疲劳提醒
    assert is_fatigue_alert(65) is True
    assert is_fatigue_alert(60) is False
    assert is_fatigue_alert(55) is False
    print(f"  [PASS] 疲劳提醒阈值 fatigueScore>60 正确")

    return all_passed


def main():
    print("=" * 60)
    print("  蓝心AI学习伴侣 - Task 2 感知模块测试")
    print("  测试 StudyState 生成、字段验证、6种场景")
    print("=" * 60)

    # 测试 3：单元验证（最快，先跑）
    test_unit_functions()

    # 测试 1：全场景生成
    test_all_scenarios_once()

    # 测试 2：循环输出（5 秒间隔，会耗时）
    # 非交互式终端自动跳过
    print("\n" + "=" * 60)
    try:
        user_input = input("  是否运行循环测试（约需 60 秒）？y/n [n]: ")
    except (EOFError, OSError):
        user_input = "n"

    if user_input.lower() == "y":
        test_scenario_loop()
    else:
        print("  跳过循环测试。手动运行循环测试的方法：")
        print("    >>> from mock_generator import generate_study_state, print_state")
        print("    >>> import time")
        print("    >>> for s in ['normal_focus', 'slight_distract', ...]:")
        print("    ...     print_state(generate_study_state(scenario=s))")
        print("    ...     time.sleep(5)")

    print("\n" + "=" * 60)
    print("  所有核心测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
