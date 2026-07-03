package com.vivoaigc.study;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@SpringBootApplication
public class SmartStudyBackendApplication {
    public static void main(String[] args) {
        SpringApplication.run(SmartStudyBackendApplication.class, args);
    }
}

@RestController
@CrossOrigin(origins = "*")
class StudyController {
    private final Random random = new Random();
    private final AtomicInteger eventCounter = new AtomicInteger();
    private final Map<String, SessionData> sessions = new ConcurrentHashMap<>();

    @GetMapping("/api/health")
    public ApiResponse<Map<String, Object>> health() {
        return ok(mapOf(
                "status", "healthy",
                "mockMode", true,
                "service", "backend-task3-java"
        ));
    }

    @PostMapping("/api/study/start")
    public ApiResponse<Map<String, Object>> startStudy(@RequestBody(required = false) Map<String, Object> body) {
        String taskName = stringValue(body, "taskName", "考研英语阅读");
        String sessionId = "study_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
        SessionData session = ensureSession(sessionId, taskName);
        Map<String, Object> initialState = generateStudyState(sessionId, 0);
        session.states().add(initialState);

        return ok(mapOf(
                "sessionId", sessionId,
                "startedAt", session.startedAt(),
                "initialState", initialState
        ));
    }

    @GetMapping("/api/study/state")
    public ApiResponse<Map<String, Object>> getStudyState(@RequestParam(defaultValue = "study_001") String sessionId) {
        SessionData session = ensureSession(sessionId, "考研英语阅读");
        int elapsedSeconds = latestElapsed(session);
        Map<String, Object> state = generateStudyState(sessionId, elapsedSeconds);
        session.states().add(state);
        return ok(state);
    }

    @PostMapping("/api/study/state")
    public ApiResponse<Map<String, Object>> postStudyState(@RequestBody Map<String, Object> state) {
        String sessionId = stringValue(state, "sessionId", "study_001");
        ensureSession(sessionId, "考研英语阅读").states().add(new LinkedHashMap<>(state));
        return ok(mapOf("accepted", true));
    }

    @PostMapping("/api/study/end")
    public ApiResponse<Map<String, Object>> endStudy(@RequestBody Map<String, Object> body) {
        String sessionId = stringValue(body, "sessionId", "study_001");
        SessionData session = ensureSession(sessionId, "考研英语阅读");
        session.endedAt(now());
        session.oralReview(stringValue(body, "oralReview", null));

        int totalMinutes = 1;
        if (!session.states().isEmpty()) {
            totalMinutes = Math.max(1, Math.round(numberValue(lastState(session), "elapsedSeconds", 60) / 60f));
        }

        return ok(mapOf(
                "sessionId", sessionId,
                "totalMinutes", totalMinutes,
                "shouldGenerateReport", true
        ));
    }

    @GetMapping("/api/study/report/{sessionId}")
    public ApiResponse<Map<String, Object>> getStudyReport(@PathVariable String sessionId) {
        SessionData session = ensureSession(sessionId, "考研英语阅读");
        if (session.report() == null) {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("sessionId", sessionId);
            body.put("oralReview", session.oralReview());
            body.put("distractionCount", session.states().isEmpty() ? 0 : numberValue(lastState(session), "distractionCount", 0));
            session.report(generateReport(body, session));
        }
        return ok(session.report());
    }

    @PostMapping("/api/ai/intervention")
    public ApiResponse<Map<String, Object>> intervention(@RequestBody Map<String, Object> body) {
        String sessionId = stringValue(body, "sessionId", "study_001");
        Map<String, Object> state = mapValue(body, "state");
        String triggerReason = stringValue(body, "triggerReason", null);
        return ok(generateIntervention(sessionId, state, triggerReason));
    }

    @PostMapping("/api/ai/rest-chat")
    public ApiResponse<Map<String, Object>> restChat(@RequestBody Map<String, Object> body) {
        int minutes = numberValue(body, "sessionDuration", numberValue(body, "totalMinutes", 45));
        int fatigueScore = numberValue(body, "fatigueScore", 0);

        List<Map<String, Object>> templates = List.of(
                mapOf("message", "你已经坚持了{minutes}分钟，挺不容易的。现在可以先放松一下眼睛。刚才这段学习里，哪一类题最卡？",
                        "suggestedReplies", List.of("第二篇阅读比较卡", "注意力后半段下降了", "整体还可以")),
                mapOf("message", "辛苦了！{minutes}分钟的学习下来感觉怎么样？有没有哪个部分让你特别头疼？",
                        "suggestedReplies", List.of("公式记忆有点吃力", "前面还行，后面累了", "比昨天好一点")),
                mapOf("message", "不错的一段专注时间。先喝口水休息一下，你觉得刚才哪一步可以做得更好？",
                        "suggestedReplies", List.of("中间分心了两次", "节奏还可以", "需要更多练习"))
        );
        Map<String, Object> template = templates.get(random.nextInt(templates.size()));

        return ok(mapOf(
                "message", ((String) template.get("message")).replace("{minutes}", String.valueOf(minutes)),
                "suggestedReplies", template.get("suggestedReplies"),
                "question", randomQuestion(),
                "restDuration", minutes >= 45 || fatigueScore >= 60 ? 5 : 3
        ));
    }

    @PostMapping("/api/ai/oral-review")
    public ApiResponse<Map<String, Object>> oralReview(@RequestBody Map<String, Object> body) {
        int focusScore = numberValue(body, "focusScore", 78);
        int distractionCount = numberValue(body, "distractionCount", 0);
        int durationMinutes = numberValue(body, "durationMinutes", 45);

        String question;
        if (distractionCount >= 3) {
            question = "刚才这" + durationMinutes + "分钟里，最容易分心的是哪一段？";
        } else if (focusScore >= 80) {
            question = "用一句话说说，刚才这" + durationMinutes + "分钟你完成了什么？";
        } else {
            question = "如果下次想更顺一点，你会先调整哪一个小步骤？";
        }
        return ok(mapOf("question", question));
    }

    @PostMapping("/api/ai/report")
    public ApiResponse<Map<String, Object>> report(@RequestBody Map<String, Object> body) {
        String sessionId = stringValue(body, "sessionId", "study_001");
        SessionData session = ensureSession(sessionId, "考研英语阅读");
        Map<String, Object> report = generateReport(body, session);
        session.report(report);
        return ok(report);
    }

    private Map<String, Object> generateStudyState(String sessionId, int elapsedSeconds) {
        Scenario scenario = scenarioForElapsed(elapsedSeconds);
        String level = scenario.level();
        boolean isL1 = "L1".equals(level);
        boolean isL2 = "L2".equals(level);
        boolean isL3 = "L3".equals(level);
        boolean isFatigue = "tired".equals(scenario.emotion());

        int focusScore = randomInt(scenario.focusMin(), scenario.focusMax());
        int fatigueScore = randomInt(scenario.fatigueMin(), scenario.fatigueMax()) + elapsedSeconds / 300 * 3;

        return mapOf(
                "sessionId", sessionId,
                "timestamp", now(),
                "elapsedSeconds", elapsedSeconds,
                "focusScore", clamp(focusScore),
                "fatigueScore", clamp(fatigueScore),
                "distractionLevel", level,
                "emotion", scenario.emotion(),
                "currentScene", "study",
                "isUserPresent", scenario.present(),
                "headDownSeconds", isL2 ? 12 : isL3 ? 0 : 3,
                "eyeClosedRatio", isFatigue ? 0.25 : isL3 ? 0.05 : 0.08,
                "gazeAwaySeconds", isL1 ? 25 : isL2 ? 65 : isL3 ? 0 : 5,
                "mouthOpenCount", isFatigue ? 3 : 1,
                "currentAppType", isL3 ? "entertainment" : "study",
                "distractionCount", elapsedSeconds / 45
        );
    }

    private Map<String, Object> generateIntervention(String sessionId, Map<String, Object> state, String triggerReason) {
        String level = chooseLevel(state);
        InterventionTemplate template = interventionTemplates().get(level);
        int index = random.nextInt(template.messages().size());

        return mapOf(
                "eventId", "evt_" + String.format("%03d", eventCounter.incrementAndGet()),
                "sessionId", sessionId,
                "level", level,
                "type", template.type(),
                "title", template.title(),
                "message", template.messages().get(index),
                "action", template.actions().get(index % template.actions().size()),
                "triggerReason", triggerReason == null ? template.reason() : triggerReason,
                "timestamp", now()
        );
    }

    private Map<String, Object> generateReport(Map<String, Object> body, SessionData session) {
        List<Integer> focusCurve = intListValue(body, "focusCurve");
        if (focusCurve.isEmpty()) {
            focusCurve = intListValue(body, "focusHistory");
        }
        if (focusCurve.isEmpty()) {
            focusCurve = session.states().stream()
                    .map(state -> numberValue(state, "focusScore", 78))
                    .toList();
        }
        if (focusCurve.isEmpty()) {
            focusCurve = List.of(80, 82, 78, 65, 72, 85);
        }

        List<Integer> fatigueCurve = intListValue(body, "fatigueCurve");
        if (fatigueCurve.isEmpty()) {
            fatigueCurve = session.states().stream()
                    .map(state -> numberValue(state, "fatigueScore", 40))
                    .toList();
        }
        if (fatigueCurve.isEmpty()) {
            fatigueCurve = List.of(20, 24, 28, 45, 60, 66);
        }

        int totalMinutes = numberValue(body, "totalMinutes", defaultTotalMinutes(session));
        int averageFocusScore = numberValue(body, "averageFocusScore", average(focusCurve));
        int maxFatigueScore = numberValue(body, "maxFatigueScore", fatigueCurve.stream().mapToInt(Integer::intValue).max().orElse(66));
        int effectiveMinutes = numberValue(body, "effectiveMinutes", Math.round(totalMinutes * averageFocusScore / 100f));
        int distractionCount = numberValue(body, "distractionCount", session.states().isEmpty() ? 0 : numberValue(lastState(session), "distractionCount", 0));
        String oralReview = stringValue(body, "oralReview", session.oralReview());

        String summary;
        String advantage;
        if (averageFocusScore >= 75) {
            summary = "今天整体学习状态较好，有效学习时间占比较高。";
            advantage = "你能持续完成当前学习任务，并且保持了不错的专注度。";
        } else if (averageFocusScore >= 60) {
            summary = "今天学习状态中等，有一些波动，但整体仍然在轨道上。";
            advantage = "你坚持完成了计划的学习时长，这一点很稳定。";
        } else {
            summary = "今天状态有些起伏，分心次数偏多，适合调整下次的学习节奏。";
            advantage = "即使状态不完美，你仍然完成了一次完整复盘。";
        }
        if (oralReview != null && !oralReview.isBlank()) {
            summary += " 你的复盘也提供了明确线索，下一次可以围绕这个薄弱点优化。";
        }

        String problem = distractionCount > 3
                ? "分心次数达到" + distractionCount + "次，可能需要减少外部干扰或缩短单次学习单元。"
                : "分心控制得不错，后续可以继续保持当前学习环境。";

        List<String> suggestions = List.of(
                distractionCount > 3 ? "下次可以把任务拆成更小的25分钟单元" : "继续保持当前学习节奏，并记录最容易进入状态的时间段",
                totalMinutes >= 45 ? "每30分钟安排一次3到5分钟休息，降低疲劳影响" : "可以逐步把单次专注时长增加到45分钟"
        );

        return mapOf(
                "sessionId", stringValue(body, "sessionId", "study_001"),
                "createdAt", now(),
                "totalMinutes", totalMinutes,
                "effectiveMinutes", effectiveMinutes,
                "averageFocusScore", clamp(averageFocusScore),
                "maxFatigueScore", clamp(maxFatigueScore),
                "distractionCount", distractionCount,
                "focusCurve", focusCurve,
                "fatigueCurve", fatigueCurve,
                "oralReview", oralReview,
                "summary", summary,
                "advantage", advantage,
                "problem", problem,
                "suggestions", suggestions,
                "encouragement", randomEncouragement()
        );
    }

    private SessionData ensureSession(String sessionId, String taskName) {
        return sessions.computeIfAbsent(sessionId, id -> new SessionData(id, taskName, now()));
    }

    private int latestElapsed(SessionData session) {
        if (!session.states().isEmpty()) {
            return numberValue(lastState(session), "elapsedSeconds", 0) + 5;
        }
        return Math.max(0, (int) (now() - session.startedAt()));
    }

    private Map<String, Object> lastState(SessionData session) {
        return session.states().get(session.states().size() - 1);
    }

    private Scenario scenarioForElapsed(int elapsedSeconds) {
        int cycle = elapsedSeconds % 200;
        for (Scenario scenario : scenarios()) {
            if (cycle < scenario.until()) {
                return scenario;
            }
        }
        return scenarios().get(0);
    }

    private String chooseLevel(Map<String, Object> state) {
        String level = stringValue(state, "distractionLevel", null);
        if ("L1".equals(level) || "L2".equals(level) || "L3".equals(level)) {
            return level;
        }
        if (Boolean.FALSE.equals(state.get("isUserPresent")) || "entertainment".equals(state.get("currentAppType"))) {
            return "L3";
        }
        if (numberValue(state, "focusScore", 80) < 50 || numberValue(state, "gazeAwaySeconds", 0) >= 60) {
            return "L2";
        }
        return "L1";
    }

    private List<Scenario> scenarios() {
        return List.of(
                new Scenario(30, 82, 95, 20, 40, "NONE", "focused", true),
                new Scenario(60, 60, 70, 30, 45, "L1", "distracted", true),
                new Scenario(85, 75, 90, 30, 45, "NONE", "calm", true),
                new Scenario(115, 40, 55, 45, 60, "L2", "distracted", true),
                new Scenario(135, 75, 90, 30, 45, "NONE", "calm", true),
                new Scenario(155, 65, 75, 65, 80, "NONE", "tired", true),
                new Scenario(175, 15, 30, 45, 60, "L3", "anxious", false),
                new Scenario(200, 80, 90, 28, 42, "NONE", "calm", true)
        );
    }

    private Map<String, InterventionTemplate> interventionTemplates() {
        return Map.of(
                "L1", new InterventionTemplate(
                        "TEXT",
                        "注意力提醒",
                        List.of("稍微有点分心了，先回到当前任务吧。", "眼睛离开内容有点久了，完成眼前这一小步就好。", "先深呼吸一下，把注意力拉回当前题目。"),
                        List.of("回到当前任务", "继续学习", "重新聚焦"),
                        "视线偏离超过20秒"
                ),
                "L2", new InterventionTemplate(
                        "VOICE",
                        "需要调整一下",
                        List.of("你已经分心一小会儿了，先把注意力拉回当前这一步吧。", "连续分心会降低效率，先完成当前小任务再休息一下。", "注意到状态有些下滑，试着回到刚才那道题上。"),
                        List.of("先完成当前小任务，再休息", "回到学习内容", "调整状态，继续学习"),
                        "连续分心超过60秒"
                ),
                "L3", new InterventionTemplate(
                        "POPUP",
                        "暂停一下",
                        List.of("当前状态不太适合继续硬撑，建议暂停一下，回来后重新开始这一小段。", "看起来你已经离开学习状态，休息5分钟再重新规划会更高效。"),
                        List.of("暂停学习", "休息一下"),
                        "离座或严重分心"
                )
        );
    }

    private String randomQuestion() {
        List<String> questions = List.of(
                "用一句话说说，刚才这段时间你主要完成了什么？",
                "刚才的学习中，最有收获的一个点是？",
                "如果能重来，你会怎么调整刚才的学习节奏？"
        );
        return questions.get(random.nextInt(questions.size()));
    }

    private String randomEncouragement() {
        List<String> encouragements = List.of(
                "今天已经完成了一段有效学习，继续保持这种复盘习惯。",
                "每一步都在靠近目标，今天的努力是算数的。",
                "你已经把这段学习闭环跑完了，下一次会更顺。"
        );
        return encouragements.get(random.nextInt(encouragements.size()));
    }

    private int defaultTotalMinutes(SessionData session) {
        if (session.states().isEmpty()) {
            return 45;
        }
        return Math.max(1, Math.round(numberValue(lastState(session), "elapsedSeconds", 2700) / 60f));
    }

    private int average(List<Integer> values) {
        return Math.round((float) values.stream().mapToInt(Integer::intValue).average().orElse(78));
    }

    private int randomInt(int min, int max) {
        return min + random.nextInt(max - min + 1);
    }

    private int clamp(int value) {
        return Math.max(0, Math.min(100, value));
    }

    private long now() {
        return Instant.now().getEpochSecond();
    }

    private String stringValue(Map<String, Object> map, String key, String defaultValue) {
        if (map == null || map.get(key) == null) {
            return defaultValue;
        }
        return String.valueOf(map.get(key));
    }

    private int numberValue(Map<String, Object> map, String key, int defaultValue) {
        if (map == null || map.get(key) == null) {
            return defaultValue;
        }
        Object value = map.get(key);
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return defaultValue;
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Map<String, Object> map, String key) {
        Object value = map == null ? null : map.get(key);
        if (value instanceof Map<?, ?> rawMap) {
            return (Map<String, Object>) rawMap;
        }
        return new LinkedHashMap<>();
    }

    private List<Integer> intListValue(Map<String, Object> map, String key) {
        Object value = map == null ? null : map.get(key);
        if (!(value instanceof List<?> rawList)) {
            return new ArrayList<>();
        }
        return rawList.stream()
                .filter(item -> item instanceof Number)
                .map(item -> ((Number) item).intValue())
                .toList();
    }

    private Map<String, Object> mapOf(Object... pairs) {
        Map<String, Object> map = new LinkedHashMap<>();
        for (int i = 0; i < pairs.length; i += 2) {
            map.put(String.valueOf(pairs[i]), pairs[i + 1]);
        }
        return map;
    }

    private <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(0, "ok", data);
    }
}

record ApiResponse<T>(int code, String message, T data) {
}

record Scenario(
        int until,
        int focusMin,
        int focusMax,
        int fatigueMin,
        int fatigueMax,
        String level,
        String emotion,
        boolean present
) {
}

record InterventionTemplate(
        String type,
        String title,
        List<String> messages,
        List<String> actions,
        String reason
) {
}

class SessionData {
    private final String sessionId;
    private final String taskName;
    private final long startedAt;
    private final List<Map<String, Object>> states = new ArrayList<>();
    private Long endedAt;
    private String oralReview;
    private Map<String, Object> report;

    SessionData(String sessionId, String taskName, long startedAt) {
        this.sessionId = sessionId;
        this.taskName = taskName;
        this.startedAt = startedAt;
    }

    String sessionId() {
        return sessionId;
    }

    String taskName() {
        return taskName;
    }

    long startedAt() {
        return startedAt;
    }

    List<Map<String, Object>> states() {
        return states;
    }

    Long endedAt() {
        return endedAt;
    }

    void endedAt(Long endedAt) {
        this.endedAt = endedAt;
    }

    String oralReview() {
        return oralReview;
    }

    void oralReview(String oralReview) {
        this.oralReview = oralReview;
    }

    Map<String, Object> report() {
        return report;
    }

    void report(Map<String, Object> report) {
        this.report = report;
    }
}
