# Task 3 后端与 AI 服务

本目录提供蓝心 AI 学习伴侣的 Mock 后端服务。它优先保证 Demo 闭环可运行，之后再替换真实 vivo AIGC / 蓝心大模型能力。

## 启动

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://localhost:8000/api/health
```

## 已实现接口

学习会话：

1. `POST /api/study/start`
2. `GET /api/study/state?sessionId=study_001`
3. `POST /api/study/state`
4. `POST /api/study/end`
5. `GET /api/study/report/{sessionId}`

AI 服务：

1. `POST /api/ai/intervention`
2. `POST /api/ai/rest-chat`
3. `POST /api/ai/oral-review`
4. `POST /api/ai/report`

所有接口都返回统一结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## 前端联调

后端已经兼容 `app/src/data/api.js` 中定义的接口。前端切真实服务时，先编辑：

```js
export const MOCK_MODE = false
const BASE_URL = 'http://localhost:8000'
```

当前部分页面仍直接引用本地 Mock 文件，完整联调时还需要把这些页面切到 `api.js`：

- `app/src/pages/StudyPage.jsx`
- `app/src/pages/RestChat.jsx`
- `app/src/pages/StudyReport.jsx`

然后启动前端：

```bash
cd app
npm run dev
```

## 说明

- 当前服务使用内存保存学习会话和日报，不依赖数据库。
- `AI_MOCK_MODE=false` 暂不会强制调用真实 vivo 接口；没有真实 Key 时仍以 Mock 兜底，避免阻塞演示。
- 接口字段以 `docs/API.md` 为准，额外返回的 `question`、`restDuration` 用于兼容前端休息伴聊页面。
