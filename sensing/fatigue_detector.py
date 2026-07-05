"""
疲劳检测器：根据学习时长和身体指标计算 fatigueScore (0-100)。

计算逻辑：
- 基础分从 elapsedSeconds 推算：每学习 60 秒 +1 分（随学习时间增长）
- eyeClosedRatio 加剧疲劳：每 0.1 +5 分
- headDownSeconds 加剧疲劳：每秒 +0.5 分
- fatigueScore > 60 触发疲劳提醒
"""


def calculate_fatigue_score(
    elapsed_seconds: float = 0.0,
    eye_closed_ratio: float = 0.0,
    head_down_seconds: float = 0.0,
) -> int:
    # 学习时间带来的基础疲劳：每 60 秒 +1 分，上限 50
    time_fatigue = min(elapsed_seconds / 60.0, 50)

    # 闭眼占比加剧疲劳
    eye_fatigue = eye_closed_ratio * 50

    # 低头时间加剧疲劳
    head_fatigue = min(head_down_seconds * 0.5, 25)

    score = time_fatigue + eye_fatigue + head_fatigue

    return max(0, min(100, int(score)))


def is_fatigue_alert(fatigue_score: int) -> bool:
    """fatigueScore > 60 触发疲劳提醒"""
    return fatigue_score > 60
