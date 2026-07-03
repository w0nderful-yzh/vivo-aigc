from __future__ import annotations

import os
import random
import time
from typing import Any, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


DistractionLevel = Literal["NONE", "L1", "L2", "L3"]
Emotion = Literal["calm", "focused", "tired", "anxious", "distracted"]
CurrentScene = Literal["study", "rest", "report"]
CurrentAppType = Literal["study", "neutral", "entertainment"]
InterventionType = Literal["TEXT", "VOICE", "POPUP", "HAPTIC"]


app = FastAPI(title="Smart Study Companion Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now_ts() -> int:
    return int(time.time())


def ok(data: Any) -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data}


def clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, value))


class StudyState(BaseModel):
    sessionId: str
    timestamp: int
    elapsedSeconds: int = Field(ge=0)
    focusScore: int = Field(ge=0, le=100)
    fatigueScore: int = Field(ge=0, le=100)
    distractionLevel: DistractionLevel
    emotion: Emotion
    currentScene: CurrentScene
    isUserPresent: bool
    headDownSeconds: int = Field(ge=0)
    eyeClosedRatio: float = Field(ge=0, le=1)
    gazeAwaySeconds: int = Field(ge=0)
    mouthOpenCount: int = Field(ge=0)
    currentAppType: CurrentAppType
    distractionCount: int = Field(ge=0)


class StartStudyRequest(BaseModel):
    userId: str = "demo_user"
    taskName: str = "考研英语阅读"
    targetMinutes: int = Field(default=45, ge=1)
    mockMode: bool = True


class EndStudyRequest(BaseModel):
    sessionId: str
    endedAt: Optional[int] = None
    oralReview: Optional[str] = None


class InterventionRequest(BaseModel):
    sessionId: str
    state: dict[str, Any]
    triggerReason: Optional[str] = None


class RestChatRequest(BaseModel):
    sessionId: str
    sessionDuration: Optional[int] = None
    totalMinutes: Optional[int] = None
    fatigueScore: Optional[int] = None
    userGoal: Optional[str] = None
    recentState: Optional[str] = None


class OralReviewRequest(BaseModel):
    sessionId: str
    taskName: str = "学习任务"
    focusScore: int = 78
    distractionCount: int = 0
    durationMinutes: int = 45


class ReportRequest(BaseModel):
    sessionId: str = "study_001"
    totalMinutes: Optional[int] = None
    effectiveMinutes: Optional[int] = None
    averageFocusScore: Optional[int] = None
    maxFatigueScore: Optional[int] = None
    distractionCount: int = 0
    focusCurve: Optional[list[int]] = None
    fatigueCurve: Optional[list[int]] = None
    focusHistory: Optional[list[int]] = None
    oralReview: Optional[str] = None


sessions: dict[str, dict[str, Any]] = {}
event_counter = 0

SCENARIOS = [
    {"until": 30, "focus": (82, 95), "fatigue": (20, 40), "level": "NONE", "emotion": "focused", "present": True},
    {"until": 60, "focus": (60, 70), "fatigue": (30, 45), "level": "L1", "emotion": "distracted", "present": True},
    {"until": 85, "focus": (75, 90), "fatigue": (30, 45), "level": "NONE", "emotion": "calm", "present": True},
    {"until": 115, "focus": (40, 55), "fatigue": (45, 60), "level": "L2", "emotion": "distracted", "present": True},
    {"until": 135, "focus": (75, 90), "fatigue": (30, 45), "level": "NONE", "emotion": "calm", "present": True},
    {"until": 155, "focus": (65, 75), "fatigue": (65, 80), "level": "NONE", "emotion": "tired", "present": True},
    {"until": 175, "focus": (15, 30), "fatigue": (45, 60), "level": "L3", "emotion": "anxious", "present": False},
    {"until": 200, "focus": (80, 90), "fatigue": (28, 42), "level": "NONE", "emotion": "calm", "present": True},
]

INTERVENTION_TEMPLATES = {
    "L1": {
        "type": "TEXT",
        "title": "注意力提醒",
        "messages": [
            "稍微有点分心了，先回到当前任务吧。",
            "眼睛离开内容有点久了，完成眼前这一小步就好。",
            "先深呼吸一下，把注意力拉回当前题目。",
        ],
        "actions": ["回到当前任务", "继续学习", "重新聚焦"],
        "reason": "视线偏离超过20秒",
    },
    "L2": {
        "type": "VOICE",
        "title": "需要调整一下",
        "messages": [
            "你已经分心一小会儿了，先把注意力拉回当前这一步吧。",
            "连续分心会降低效率，先完成当前小任务再休息一下。",
            "注意到状态有些下滑，试着回到刚才那道题上。",
        ],
        "actions": ["先完成当前小任务，再休息", "回到学习内容", "调整状态，继续学习"],
        "reason": "连续分心超过60秒",
    },
    "L3": {
        "type": "POPUP",
        "title": "暂停一下",
        "messages": [
            "当前状态不太适合继续硬撑，建议暂停一下，回来后重新开始这一小段。",
            "看起来你已经离开学习状态，休息5分钟再重新规划会更高效。",
        ],
        "actions": ["暂停学习", "休息一下"],
        "reason": "离座或严重分心",
    },
}

REST_MESSAGES = [
    {
        "message": "你已经坚持了{minutes}分钟，挺不容易的。现在可以先放松一下眼睛。刚才这段学习里，哪一类题最卡？",
        "suggestedReplies": ["第二篇阅读比较卡", "注意力后半段下降了", "整体还可以"],
    },
    {
        "message": "辛苦了！{minutes}分钟的学习下来感觉怎么样？有没有哪个部分让你特别头疼？",
        "suggestedReplies": ["公式记忆有点吃力", "前面还行，后面累了", "比昨天好一点"],
    },
    {
        "message": "不错的一段专注时间。先喝口水休息一下，你觉得刚才哪一步可以做得更好？",
        "suggestedReplies": ["中间分心了两次", "节奏还可以", "需要更多练习"],
    },
]

ORAL_REVIEW_QUESTIONS = [
    "用一句话说说，刚才这段时间你主要完成了什么？",
    "刚才的学习中，最有收获的一个点是？",
    "如果能重来，你会怎么调整刚才的学习节奏？",
]


def ensure_session(session_id: str = "study_001", task_name: str = "考研英语阅读") -> dict[str, Any]:
    if session_id not in sessions:
        sessions[session_id] = {
            "sessionId": session_id,
            "taskName": task_name,
            "startedAt": now_ts(),
            "states": [],
            "oralReview": None,
            "report": None,
        }
    return sessions[session_id]


def scenario_for_elapsed(elapsed_seconds: int) -> dict[str, Any]:
    cycle = elapsed_seconds % 200
    for scenario in SCENARIOS:
        if cycle < scenario["until"]:
            return scenario
    return SCENARIOS[0]


def generate_study_state(session_id: str, elapsed_seconds: int) -> StudyState:
    scenario = scenario_for_elapsed(elapsed_seconds)
    level = scenario["level"]
    is_l1 = level == "L1"
    is_l2 = level == "L2"
    is_l3 = level == "L3"
    is_fatigue = scenario["emotion"] == "tired"

    focus_score = random.randint(*scenario["focus"])
    fatigue_score = random.randint(*scenario["fatigue"]) + (elapsed_seconds // 300) * 3

    return StudyState(
        sessionId=session_id,
        timestamp=now_ts(),
        elapsedSeconds=elapsed_seconds,
        focusScore=clamp(focus_score),
        fatigueScore=clamp(fatigue_score),
        distractionLevel=level,
        emotion=scenario["emotion"],
        currentScene="study",
        isUserPresent=scenario["present"],
        headDownSeconds=12 if is_l2 else 0 if is_l3 else 3,
        eyeClosedRatio=0.25 if is_fatigue else 0.05 if is_l3 else 0.08,
        gazeAwaySeconds=25 if is_l1 else 65 if is_l2 else 0 if is_l3 else 5,
        mouthOpenCount=3 if is_fatigue else 1,
        currentAppType="entertainment" if is_l3 else "study",
        distractionCount=elapsed_seconds // 45,
    )


def store_state(state: StudyState) -> None:
    session = ensure_session(state.sessionId)
    session["states"].append(state.model_dump())


def latest_elapsed(session: dict[str, Any]) -> int:
    if session["states"]:
        return int(session["states"][-1]["elapsedSeconds"]) + 5
    return max(0, now_ts() - int(session["startedAt"]))


def choose_intervention_level(state: dict[str, Any]) -> Literal["L1", "L2", "L3"]:
    level = state.get("distractionLevel")
    if level in ("L1", "L2", "L3"):
        return level
    if state.get("isUserPresent") is False or state.get("currentAppType") == "entertainment":
        return "L3"
    if int(state.get("focusScore", 80)) < 50 or int(state.get("gazeAwaySeconds", 0)) >= 60:
        return "L2"
    return "L1"


def generate_intervention(session_id: str, state: dict[str, Any], trigger_reason: Optional[str] = None) -> dict[str, Any]:
    global event_counter
    event_counter += 1
    level = choose_intervention_level(state)
    template = INTERVENTION_TEMPLATES[level]
    index = random.randrange(len(template["messages"]))
    return {
        "eventId": f"evt_{event_counter:03d}",
        "sessionId": session_id,
        "level": level,
        "type": template["type"],
        "title": template["title"],
        "message": template["messages"][index],
        "action": template["actions"][index % len(template["actions"])],
        "triggerReason": trigger_reason or template["reason"],
        "timestamp": now_ts(),
    }


def normalize_report_input(payload: ReportRequest, session: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    states = session["states"] if session else []
    focus_curve = payload.focusCurve or payload.focusHistory or [s["focusScore"] for s in states]
    fatigue_curve = payload.fatigueCurve or [s["fatigueScore"] for s in states]

    if not focus_curve:
        focus_curve = [80, 82, 78, 65, 72, 85]
    if not fatigue_curve:
        fatigue_curve = [20, 24, 28, 45, 60, 66]

    total_minutes = payload.totalMinutes
    if total_minutes is None:
        if states:
            total_minutes = max(1, round(states[-1]["elapsedSeconds"] / 60))
        else:
            total_minutes = 45

    average_focus = payload.averageFocusScore
    if average_focus is None:
        average_focus = round(sum(focus_curve) / len(focus_curve))

    max_fatigue = payload.maxFatigueScore
    if max_fatigue is None:
        max_fatigue = max(fatigue_curve)

    effective_minutes = payload.effectiveMinutes
    if effective_minutes is None:
        effective_minutes = round(total_minutes * average_focus / 100)

    return {
        "sessionId": payload.sessionId,
        "createdAt": now_ts(),
        "totalMinutes": total_minutes,
        "effectiveMinutes": effective_minutes,
        "averageFocusScore": clamp(average_focus),
        "maxFatigueScore": clamp(max_fatigue),
        "distractionCount": payload.distractionCount,
        "focusCurve": focus_curve,
        "fatigueCurve": fatigue_curve,
        "oralReview": payload.oralReview,
    }


def generate_report(payload: ReportRequest, session: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    report = normalize_report_input(payload, session)
    avg_focus = report["averageFocusScore"]
    total_minutes = report["totalMinutes"]
    distraction_count = report["distractionCount"]
    oral_review = report["oralReview"]

    if avg_focus >= 75:
        summary = "今天整体学习状态较好，有效学习时间占比较高。"
        advantage = "你能持续完成当前学习任务，并且保持了不错的专注度。"
    elif avg_focus >= 60:
        summary = "今天学习状态中等，有一些波动，但整体仍然在轨道上。"
        advantage = "你坚持完成了计划的学习时长，这一点很稳定。"
    else:
        summary = "今天状态有些起伏，分心次数偏多，适合调整下次的学习节奏。"
        advantage = "即使状态不完美，你仍然完成了一次完整复盘。"

    if distraction_count > 3:
        problem = f"分心次数达到{distraction_count}次，可能需要减少外部干扰或缩短单次学习单元。"
        first_suggestion = "下次可以把任务拆成更小的25分钟单元"
    else:
        problem = "分心控制得不错，后续可以继续保持当前学习环境。"
        first_suggestion = "继续保持当前学习节奏，并记录最容易进入状态的时间段"

    second_suggestion = (
        "每30分钟安排一次3到5分钟休息，降低疲劳影响"
        if total_minutes >= 45
        else "可以逐步把单次专注时长增加到45分钟"
    )

    if oral_review:
        summary += " 你的复盘也提供了明确线索，下一次可以围绕这个薄弱点优化。"

    report.update(
        {
            "summary": summary,
            "advantage": advantage,
            "problem": problem,
            "suggestions": [first_suggestion, second_suggestion],
            "encouragement": random.choice(
                [
                    "今天已经完成了一段有效学习，继续保持这种复盘习惯。",
                    "每一步都在靠近目标，今天的努力是算数的。",
                    "你已经把这段学习闭环跑完了，下一次会更顺。",
                ]
            ),
        }
    )
    return report


@app.get("/api/health")
def health() -> dict[str, Any]:
    return ok(
        {
            "status": "healthy",
            "mockMode": os.getenv("AI_MOCK_MODE", "true").lower() != "false",
            "service": "backend-task3",
        }
    )


@app.post("/api/study/start")
def start_study(payload: StartStudyRequest) -> dict[str, Any]:
    session_id = f"study_{uuid4().hex[:8]}"
    session = ensure_session(session_id, payload.taskName)
    initial_state = generate_study_state(session_id, 0)
    store_state(initial_state)
    return ok(
        {
            "sessionId": session_id,
            "startedAt": session["startedAt"],
            "initialState": initial_state.model_dump(),
        }
    )


@app.get("/api/study/state")
def get_study_state(sessionId: str = "study_001") -> dict[str, Any]:
    session = ensure_session(sessionId)
    state = generate_study_state(sessionId, latest_elapsed(session))
    store_state(state)
    return ok(state.model_dump())


@app.post("/api/study/state")
def post_study_state(payload: StudyState) -> dict[str, Any]:
    store_state(payload)
    return ok({"accepted": True})


@app.post("/api/study/end")
def end_study(payload: EndStudyRequest) -> dict[str, Any]:
    session = ensure_session(payload.sessionId)
    session["endedAt"] = payload.endedAt or now_ts()
    session["oralReview"] = payload.oralReview
    total_minutes = 1
    if session["states"]:
        total_minutes = max(1, round(session["states"][-1]["elapsedSeconds"] / 60))
    return ok({"sessionId": payload.sessionId, "totalMinutes": total_minutes, "shouldGenerateReport": True})


@app.get("/api/study/report/{session_id}")
def get_study_report(session_id: str) -> dict[str, Any]:
    session = ensure_session(session_id)
    if not session.get("report"):
        last_state = session["states"][-1] if session["states"] else {}
        payload = ReportRequest(
            sessionId=session_id,
            totalMinutes=max(1, round(int(last_state.get("elapsedSeconds", 2700)) / 60)),
            distractionCount=int(last_state.get("distractionCount", 0)),
            oralReview=session.get("oralReview"),
        )
        session["report"] = generate_report(payload, session)
    return ok(session["report"])


@app.post("/api/ai/intervention")
def ai_intervention(payload: InterventionRequest) -> dict[str, Any]:
    return ok(generate_intervention(payload.sessionId, payload.state, payload.triggerReason))


@app.post("/api/ai/rest-chat")
def ai_rest_chat(payload: RestChatRequest) -> dict[str, Any]:
    minutes = payload.sessionDuration or payload.totalMinutes or 45
    template = random.choice(REST_MESSAGES)
    return ok(
        {
            "message": template["message"].replace("{minutes}", str(minutes)),
            "suggestedReplies": template["suggestedReplies"],
            "question": random.choice(ORAL_REVIEW_QUESTIONS),
            "restDuration": 5 if minutes >= 45 or (payload.fatigueScore or 0) >= 60 else 3,
        }
    )


@app.post("/api/ai/oral-review")
def ai_oral_review(payload: OralReviewRequest) -> dict[str, Any]:
    if payload.distractionCount >= 3:
        question = f"刚才这{payload.durationMinutes}分钟里，最容易分心的是哪一段？"
    elif payload.focusScore >= 80:
        question = f"用一句话说说，刚才这{payload.durationMinutes}分钟你完成了什么？"
    else:
        question = "如果下次想更顺一点，你会先调整哪一个小步骤？"
    return ok({"question": question})


@app.post("/api/ai/report")
def ai_report(payload: ReportRequest) -> dict[str, Any]:
    session = ensure_session(payload.sessionId)
    report = generate_report(payload, session)
    session["report"] = report
    return ok(report)
