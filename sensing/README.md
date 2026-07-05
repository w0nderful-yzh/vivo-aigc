# Task 2：端侧感知与状态计算模块

## 概述

本模块负责输出标准 `StudyState` 学习状态数据，为前端展示和 AI 干预提供数据基础。第一版基于 Mock 数据生成器，不依赖真实摄像头或 MediaPipe。

## 目录结构

```
sensing/
├── mock_generator.py        # Mock 状态生成器（主入口）
├── focus_detector.py        # 专注度计算（focusScore 0-100）
├── fatigue_detector.py      # 疲劳指数计算（fatigueScore 0-100）
├── distraction_detector.py  # 分心等级判定（NONE/L1/L2/L3）
├── test_sensing.py          # 测试脚本
└── README.md                # 本文件
```

## 快速开始

```bash
cd sensing
python test_sensing.py
```

测试脚本会：
1. 运行核心函数单元验证
2. 一次性生成全部 6 种 Mock 场景
3. （可选）每 5 秒循环切换场景

## 使用方法

```python
from mock_generator import generate_study_state, print_state, get_available_scenarios

# 查看可用场景
print(get_available_scenarios())
# ['normal_focus', 'slight_distract', 'severe_distract',
#  'high_fatigue', 'away_from_seat', 'recovery_focus']

# 生成一条状态
state = generate_study_state(scenario="normal_focus")
print_state(state)

# 自定义 sessionId 和时间偏移
state = generate_study_state(
    scenario="slight_distract",
    session_id="study_002",
    elapsed_offset=300
)
```

## 6 种 Mock 场景

| 场景 | 说明 | 典型 focusScore | 典型 fatigueScore | distractionLevel |
|------|------|-----------------|-------------------|------------------|
| normal_focus | 正常专注 | 85-95 | 10-20 | NONE |
| slight_distract | 轻微分心 | 55-70 | 20-35 | L1 |
| severe_distract | 严重分心 | 30-50 | 30-50 | L2 |
| high_fatigue | 疲劳偏高 | 60-75 | 65-85 | NONE |
| away_from_seat | 离座 | 30-40 | 25-40 | L3 |
| recovery_focus | 恢复专注 | 70-85 | 30-45 | NONE |

## 计算规则

### focusScore（专注分，0-100）
- 基础分 100，根据指标扣分
- 离座直接扣 60 分
- 低头每秒扣 1 分（上限 40）
- 闭眼占比每 0.1 扣 5 分（上限 40）
- 分心次数每次扣 3 分（上限 30）
- **focusScore > 70 视为有效学习**

### fatigueScore（疲劳指数，0-100）
- 学习时长每 60 秒 +1 分（上限 50）
- 闭眼占比每 0.1 +5 分
- 低头每秒 +0.5 分（上限 25）
- **fatigueScore > 60 触发疲劳提醒**

### distractionLevel（分心等级）
- 离座或切换娱乐 App → **L3**
- 连续分心超过 60 秒 → **L2**
- 视线偏离超过 20 秒 → **L1**
- 其他 → **NONE**

## 输出数据结构

完全符合 `docs/API.md` 中的 StudyState 定义：

```json
{
  "sessionId": "study_001",
  "timestamp": 1710000000,
  "elapsedSeconds": 1200,
  "focusScore": 82,
  "fatigueScore": 35,
  "distractionLevel": "NONE",
  "emotion": "calm",
  "currentScene": "study",
  "isUserPresent": true,
  "headDownSeconds": 5,
  "eyeClosedRatio": 0.12,
  "distractionCount": 1
}
```

## 后续增强方向

1. 接入真实摄像头采集（CameraX / MediaPipe）
2. 接入系统 API 获取应用使用状态
3. 引入机器学习模型提升检测精度
4. 增加多模态感知（心率、眼动追踪等）
