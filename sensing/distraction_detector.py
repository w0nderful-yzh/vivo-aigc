"""
分心等级判定器：根据感知数据判断 distractionLevel。

规则：
- 离座（isUserPresent=False）或切换娱乐 App → L3
- 连续分心超过 60 秒 → L2
- 视线偏离超过 20 秒 → L1
- 其他情况 → NONE
- fatigueScore > 60 时也触发疲劳提醒（但等级由分心判断决定）
"""

from enum import Enum


class DistractionLevel(str, Enum):
    NONE = "NONE"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


def determine_distraction_level(
    is_user_present: bool = True,
    gaze_away_seconds: float = 0.0,
    continuous_distraction_seconds: float = 0.0,
    is_entertainment_app: bool = False,
    fatigue_score: int = 0,
) -> str:
    if not is_user_present or is_entertainment_app:
        return DistractionLevel.L3.value

    if continuous_distraction_seconds > 60:
        return DistractionLevel.L2.value

    if gaze_away_seconds > 20:
        return DistractionLevel.L1.value

    return DistractionLevel.NONE.value


def get_level_description(level: str) -> str:
    descriptions = {
        "NONE": "正常专注状态",
        "L1": "视线偏离超过20秒，轻微分心",
        "L2": "连续分心超过60秒，需要干预",
        "L3": "用户离座或切换娱乐应用，严重分心",
    }
    return descriptions.get(level, "未知状态")
