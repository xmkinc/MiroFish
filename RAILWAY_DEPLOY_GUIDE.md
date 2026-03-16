# MiroFish Railway 部署交接文档与操作手册

**作者：** Manus AI
**日期：** 2026-03-16

本文档详细记录了 MiroFish 项目在 Railway 平台上的部署方案、配置要求、踩坑记录以及后续维护指南。这份文档不仅作为本次部署的交接材料，也可作为未来环境迁移或二次开发的参考手册。

---

## 1. 部署架构概述

原始的 MiroFish 项目采用前后端分离架构（Vue 3 + Flask），在本地开发时分别占用 3000 和 5001 端口。为了适应 Railway 等云平台的单容器部署限制（只暴露一个端口），我们对架构进行了改造：

- **单体架构改造**：通过多阶段构建 Dockerfile，先构建前端静态文件，然后将其复制到后端目录中。
- **静态文件代理**：修改 Flask 路由逻辑，由 Flask 后端统一提供 API 服务和前端静态文件（SPA 回退路由）。
- **环境变量注入**：将硬编码的配置改为环境变量，以适应 Railway 的动态配置注入。

---

## 2. 核心文件修改记录

在本次部署中，我们修改了以下核心文件，这些修改已全部推送到 `xmkinc/MiroFish` 仓库的 `main` 分支。

### 2.1 `Dockerfile`
优化了构建流程，弃用容易产生路径问题的 `uv` 虚拟环境，改用标准的 `pip install` 将依赖安装到系统 Python 中。

### 2.2 `backend/run_prod.py`
新增了专门用于生产环境的启动脚本。该脚本实现了：
- 提供 `/health` 健康检查端点
- 挂载前端 `dist` 目录作为静态文件服务
- 实现 SPA（单页应用）的 404 回退路由，确保前端路由刷新不报错
- 确保 `/api/` 前缀的请求不被静态文件路由拦截

### 2.3 `backend/app/utils/llm_client.py`
增强了 `chat_json` 方法的鲁棒性，以兼容"思考型"大模型（如 Qwen3）。当模型返回包含 `<think>` 标签的非标准 JSON 时，能够通过正则表达式提取出有效的 JSON 内容。

### 2.4 `frontend/src/api/index.js`
修改了前端的 `baseURL` 配置，在生产环境下使用相对路径（同源请求），避免了跨域问题。

---

## 3. 环境变量配置指南

在 Railway 控制台的 **Variables** 面板中，必须配置以下环境变量。如果未来需要更换模型或 API 密钥，请直接在此修改，Railway 会自动触发重新部署。

| 变量名 | 说明 | 当前值示例 |
|--------|------|------------|
| `LLM_API_KEY` | 大语言模型 API Key | `sk-or-v1-...` |
| `LLM_BASE_URL` | LLM API 基础地址 | `https://openrouter.ai/api/v1` |
| `LLM_MODEL_NAME` | 主力模型名称（推荐用高性价比模型） | `openai/gpt-4o-mini` 或 `google/gemini-2.0-flash-001` |
| `ZEP_API_KEY` | Zep Cloud 记忆图谱 API Key | `z_1dWlk...` |
| `FLASK_ENV` | Flask 运行环境 | `production` |
| `PORT` | 运行端口 | **无需手动设置**，Railway 自动注入 |

---

## 4. 踩坑与问题排查记录

在部署过程中，我们遇到了几个关键问题，以下是解决方案的记录，供后续维护参考：

### 4.1 虚拟环境路径问题（ModuleNotFoundError）
- **现象**：使用 `uv sync` 安装依赖后，容器启动时报错找不到 `flask` 模块。
- **原因**：`uv` 默认将包安装在当前工作目录的 `.venv` 中，而 `Dockerfile` 的后续 `COPY` 步骤与 `.dockerignore` 的配置导致虚拟环境路径混乱。
- **解决**：弃用 `uv`，直接在 `Dockerfile` 中使用 `pip install -e ./backend/` 将依赖安装到系统环境中。

### 4.2 API 路由被静态文件拦截（前端显示 Error）
- **现象**：前端调用 `/api/graph/status` 等接口时，返回了 HTML 页面而不是 JSON 数据。
- **原因**：Flask 的通配符路由 `/<path:path>` 优先级高于某些蓝图路由。
- **解决**：在 `run_prod.py` 中改用 `@app.errorhandler(404)` 来实现 SPA 回退，并明确排除以 `/api/` 开头的请求。

### 4.3 思考模型导致 JSON 解析失败（500 错误）
- **现象**：使用 `qwen/qwen3-235b-a22b` 模型生成本体时，后端抛出 `argument of type 'int' is not iterable` 错误。
- **原因**：思考模型在 JSON 模式下会输出 `<think>` 标签，导致原有的 `chat_json` 解析逻辑崩溃。
- **解决**：将默认模型更改为 `openai/gpt-4o-mini`，同时优化了 `llm_client.py` 中的 JSON 提取逻辑，使其能兼容各种格式的输出。

### 4.4 出站网络限制（Network is unreachable）
- **现象**：Railway 容器内调用 LLM API 时出现 `httpcore.ConnectError`。
- **原因**：Railway 的免费计划（Hobby 计划的试用期）偶尔会对出站 TCP 连接进行限制或出现网络抖动。
- **解决**：这是平台层面的限制，如果频繁出现，建议升级 Railway 计划或迁移至 Render 等其他平台。

---

## 5. 改造建议：A 股散户情绪模拟器

如前所述，MiroFish 非常适合改造为**A 股散户情绪模拟器**。以下是改造路线图：

1. **数据源替换**：编写 Python 爬虫（如 `requests` + `BeautifulSoup`）抓取东方财富或同花顺的实时新闻，将抓取结果自动组装成文本，跳过前端的手动上传步骤。
2. **预设 Agent 模板**：修改 `backend/app/services/agent_builder.py`，不再通过 LLM 动态生成角色，而是直接加载预设的 JSON 模板（如"短线追涨散户"、"价值投资信徒"等）。
3. **前端界面定制**：修改 `frontend/src/views/` 下的页面，将"上传文档"改为"输入股票代码"，并增加专门展示情绪指数折线图的组件。

---

## 6. 常用维护命令

如果你需要在本地克隆并测试部署后的版本，可以使用以下命令：

```bash
# 克隆仓库
git clone https://github.com/xmkinc/MiroFish.git
cd MiroFish

# 使用 Docker 本地测试生产镜像
docker build -t mirofish-prod .
docker run -p 8080:5001 --env-file .env.railway mirofish-prod
```

> **注意**：本地测试前，请先复制 `.env.railway.example` 为 `.env.railway` 并填入真实的 API Key。

---
*文档完。祝使用愉快！*
