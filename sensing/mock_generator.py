"""
Mock 状态生成器：生成 6 种学习场景的 StudyState 数据。

支持的场景：
1. normal_focus     - 正常专注
2. slight_distract  - 轻微分心 (L1)
3. severe_distract  - 严重分心 (L2)
4. high_fatigue     - 疲劳偏高
5. away_from_seat   - 离座 (L3)
6. recovery_focus   - 恢复专注

输出字段完全符合 docs/API.md 中的 StudyState 定义。
"""

import time
import random
from typing import Any

from focus_detector import calculate_focus_score, is_effective_learning
from fatigue_detector import calculate_fatigue_score, is_fatigue_alert
from distraction_detector import determine_distraction_level, get_level_description


# 6 种 Mock 场景的原始感知参数配置
SCENARIO_PARAMS: dict[str, dict[str, Any]] = {
    "normal_focus": {
        "description": "正常专注",
        "is_user_present": True,
        "head_down_seconds": 2.0,
        "eye_closed_ratio": 0.05,
        "distraction_count": 0,
        "gaze_away_seconds": 5.0,
        "continuous_distraction_seconds": 0.0,
        "is_entertainment_app": False,
        "emotion": "calm",
        "elapsed_base": 600,
    },
    "slight_distract": {
        "description": "轻微分心",
        "is_user_present": True,
        "head_down_seconds": 12.0,
        "eye_closed_ratio": 0.15,
        "distraction_count": 3,
        "gaze_away_seconds": 25.0,
        "continuous_distraction_seconds": 0.0,
        "is_entertainment_app": False,
        "emotion": "distracted",
        "elapsed_base": 900,
    },
    "severe_distract": {
        "description": "严重分心",
        "is_user_present": True,
        "head_down_seconds": 20.0,
        "eye_closed_ratio": 0.25,
        "distraction_count": 8,
        "gaze_away_seconds": 45.0,
        "continuous_distraction_seconds": 75.0,
        "is_entertainment_app": False,
        "emotion": "distracted",
        "elapsed_base": 1200,
    },
    "high_fatigue": {
        "description": "疲劳偏高",
        "is_user_present": True,
        "head_down_seconds": 18.0,
        "eye_closed_ratio": 0.35,
        "distraction_count": 1,
        "gaze_away_seconds": 10.0,
        "continuous_distraction_seconds": 0.0,
        "is_entertainment_app": False,
        "emotion": "tired",
        "elapsed_base": 2700,
    },
    "away_from_seat": {
        "description": "离座",
        "is_user_present": False,
        "head_down_seconds": 0.0,
        "eye_closed_ratio": 0.0,
        "distraction_count": 10,
        "gaze_away_seconds": 120.0,
        "continuous_distraction_seconds": 120.0,
        "is_entertainment_app": False,
        "emotion": "anxious",
        "elapsed_base": 1500,
    },
    "recovery_focus": {
        "description": "恢复专注",
        "is_user_present": True,
        "head_down_seconds": 3.0,
        "eye_closed_ratio": 0.06,
        "distraction_count": 1,
        "gaze_away_seconds": 8.0,
        "continuous_distraction_seconds": 0.0,
        "is_entertainment_app": False,
        "emotion": "calm",
        "elapsed_base": 1800,
    },
}


def generate_study_state(
    scenario: str = "normal_focus",
    session_id: str = "study_001",
    elapsed_offset: float = 0.0,
) -> dict[str, Any]:
    """
    根据场景名称生成一条标准 StudyState。

    参数:
        scenario: 场景名称，必须是 SCENARIO_PARAMS 中的 key
        session_id: 学习会话 ID
        elapsed_offset: 额外时间偏移（秒），用于模拟时间推进

    返回:
        标准 StudyState 字典
    """
    params = SCENARIO_PARAMS.get(scenario)
    if params is None:
        raise ValueError(
            f"未知场景 '{scenario}'，可选: {list(SCENARIO_PARAMS.keys())}"
        )

    # 添加小幅随机抖动让数据更真实
    jitter = lambda val, pct: val * (1 + random.uniform(-pct, pct))

    head_down = jitter(params["head_down_seconds"], 0.15)
    eye_closed = min(1.0, max(0.0, jitter(params["eye_closed_ratio"], 0.15)))
    dist_count = max(0, int(jitter(params["distraction_count"], 0.2)))
    gaze_away = jitter(params["gaze_away_seconds"], 0.1)
    cont_dist = jitter(params["continuous_distraction_seconds"], 0.1)
    elapsed = params["elapsed_base"] + elapsed_offset

    # 计算核心指标
    focus_score = calculate_focus_score(
        head_down_seconds=head_down,
        eye_closed_ratio=eye_closed,
        distraction_count=dist_count,
        is_user_present=params["is_user_present"],
    )

    fatigue_score = calculate_fatigue_score(
        elapsed_seconds=elapsed,
        eye_closed_ratio=eye_closed,
        head_down_seconds=head_down,
    )

    distraction_level = determine_distraction_level(
        is_user_present=params["is_user_present"],
        gaze_away_seconds=gaze_away,
        continuous_distraction_seconds=cont_dist,
        is_entertainment_app=params["is_entertainment_app"],
        fatigue_score=fatigue_score,
    )

    return {
        "sessionId": session_id,
        "timestamp": int(time.time()),
        "elapsedSeconds": int(elapsed),
        "focusScore": focus_score,
        "fatigueScore": fatigue_score,
        "distractionLevel": distraction_level,
        "emotion": params["emotion"],
        "currentScene": "study",
        "isUserPresent": params["is_user_present"],
        "headDownSeconds": round(head_down, 1),
        "eyeClosedRatio": round(eye_closed, 2),
        "distractionCount": dist_count,
    }


def get_available_scenarios() -> list[str]:
    """返回所有可用场景名称"""
    return list(SCENARIO_PARAMS.keys())


def get_scenario_description(scenario: str) -> str:
    """返回场景的文字描述"""
    params = SCENARIO_PARAMS.get(scenario)
    if params is None:
        return "未知场景"
    return params["description"]


def print_state(state: dict[str, Any]) -> None:
    """格式化打印一条 StudyState"""
    effective = "[OK]" if is_effective_learning(state["focusScore"]) else "[--]"
    fatigue_warn = "[!]" if is_fatigue_alert(state["fatigueScore"]) else "   "

    print(f"\n{'='*60}")
    print(f"  场景: {state['distractionLevel']:5s}  |  "
          f"专注分: {state['focusScore']:3d} {effective}  |  "
          f"疲劳指数: {state['fatigueScore']:3d} {fatigue_warn}")
    print(f"  已学习: {state['elapsedSeconds']}s  |  "
          f"在座: {'是' if state['isUserPresent'] else '否'}  |  "
          f"分心次数: {state['distractionCount']}")
    print(f"  低头: {state['headDownSeconds']}s  |  "
          f"闭眼比: {state['eyeClosedRatio']:.2f}")
    lvl_desc = get_level_description(state["distractionLevel"])
    print(f"  分心等级说明: {lvl_desc}")
    print(f"{'='*60}")
