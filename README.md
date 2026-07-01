# AgenticTeam：在线生鲜商城智能体团队模板

这个模板用于搭建一个按顺序运行、共享文件夹协作、可发现文件修改的智能体团队。

## 团队流程

```text
需求分析智能体
    ↓
系统架构设计智能体
    ↓
数据库管理员智能体
    ↓
Flask 后端开发智能体
    ↓
前端开发智能体
    ↓
测试工程师智能体
```

## 目录说明

```text
AgenticTeam/
├─ agents/                 智能体提示词
├─ shared/                 共享工作区
│  ├─ prd/                 需求文档
│  ├─ architecture/        架构设计文档
│  ├─ database/            数据库脚本
│  ├─ backend/             Flask 后端代码
│  ├─ frontend/            Bootstrap/Jinja2 页面
│  ├─ test/                测试用例和测试报告
│  └─ .agentic/            编排状态、文件快照、变更事件
└─ orchestrator.py         顺序编排器
```

## 基本用法

在 `AgenticTeam` 目录下运行：

```bash
python orchestrator.py status
```

查看当前该哪个智能体运行。

```bash
python orchestrator.py prompt
```

生成当前阶段智能体的完整提示词。把终端输出复制给对应智能体执行。

```bash
python orchestrator.py complete
```

当前阶段产物生成后，标记当前阶段完成并进入下一阶段。

```bash
python orchestrator.py scan
```

扫描 `shared/` 共享文件夹，记录新增、修改、删除事件。

```bash
python orchestrator.py watch
```

持续监听共享文件夹变化。该命令使用轮询方式，不需要安装第三方库。

## 共享文件夹机制

`shared/.agentic/manifest.json` 保存文件快照。

`shared/.agentic/events.jsonl` 保存文件变化事件。

`shared/.agentic/state.json` 保存当前阶段。

`shared/.agentic/task_log.md` 保存智能体执行日志。

`shared/.agentic/change_requests.md` 保存跨阶段变更请求。

## 阶段完成标志

| 阶段 | 完成标志 |
|---|---|
| requirements | `shared/prd/生鲜商城需求规格说明书.md` |
| system_design | `shared/architecture/系统架构设计说明书.md` |
| database | `shared/database/ddl/schema.sql` |
| backend | `shared/backend/app.py` |
| frontend | `shared/frontend/templates/base.html` |
| test | `shared/test/测试报告/测试报告.md` |

## 推荐操作顺序

1. 运行 `python orchestrator.py status` 查看当前阶段。
2. 运行 `python orchestrator.py prompt` 获取当前智能体提示词。
3. 把提示词交给对应智能体，让它读写 `shared/`。
4. 检查阶段完成标志文件是否生成。
5. 运行 `python orchestrator.py complete` 进入下一阶段。
6. 重复直到测试阶段完成。

## 答辩说明

本模板采用文件驱动的 Agentic 智能体团队协作模式。系统通过 `state.json` 控制执行顺序，通过 `manifest.json` 保存共享文件夹快照，通过 `events.jsonl` 记录文件变更事件。每个智能体运行前读取最新变更和上游产物，运行后只写入自己负责的目录，从而实现顺序执行、共享上下文和修改可追踪。
