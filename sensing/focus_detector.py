"""
专注度检测器：根据原始感知数据计算 focusScore (0-100)。

计算逻辑：
- 基础分 100，根据各项指标扣分
- headDownSeconds: 每秒扣 1 分（低头看手机/趴桌）
- eyeClosedRatio: 每 0.1 扣 5 分（闭眼占比高说明不专注）
- distractionCount: 每次分心扣 3 分（累计影响）
- isUserPresent=False: 直接大幅扣分（人不在 = 完全不专注）
- focusScore > 70 视为有效学习
"""


def calculate_focus_score(
    head_down_seconds: float = 0.0,
    eye_closed_ratio: float = 0.0,
    distraction_count: int = 0,
    is_user_present: bool = True,
) -> int:
    score = 100.0

    if not is_user_present:
        score -= 60

    # 低头扣分：每秒扣 1 分，上限 40
    score -= min(head_down_seconds * 1.0, 40)

    # 闭眼扣分：每 0.1 扣 5 分，上限 40
    score -= min(eye_closed_ratio * 50, 40)

    # 分心次数扣分：每次 3 分，上限 30
    score -= min(distraction_count * 3, 30)

    return max(0, min(100, int(score)))


def is_effective_learning(focus_score: int) -> bool:
    """focusScore > 70 视为有效学习"""
    return focus_score > 70
