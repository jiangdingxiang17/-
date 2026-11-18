"""
AgenticTeam 顺序编排器

用法：
  python orchestrator.py status      查看当前阶段
  python orchestrator.py scan        扫描共享文件夹变更
  python orchestrator.py prompt      生成当前阶段智能体提示词
  python orchestrator.py complete    标记当前阶段完成并进入下一阶段
  python orchestrator.py reset       重置流程状态
  python orchestrator.py watch       持续监听共享文件夹变化，默认每 2 秒扫描一次
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SHARED = ROOT / "shared"
AGENTIC = SHARED / ".agentic"
STATE_FILE = AGENTIC / "state.json"
MANIFEST_FILE = AGENTIC / "manifest.json"
EVENTS_FILE = AGENTIC / "events.jsonl"
TASK_LOG_FILE = AGENTIC / "task_log.md"

STAGES = [
    "requirements",
    "system_design",
    "database",
    "backend",
    "frontend",
    "test",
]

STAGE_AGENT = {
    "requirements": "agents/01_Requirements_Analyst.md",
    "system_design": "agents/02_System_Designer.md",
    "database": "agents/03_DBA.md",
    "backend": "agents/04_Flask_Backend_Developer.md",
    "frontend": "agents/05_Frontend_Developer.md",
    "test": "agents/06_Test_Engineer.md",
}

STAGE_DONE_FILE = {
    "requirements": "shared/prd/生鲜商城需求规格说明书.md",
    "system_design": "shared/architecture/系统架构设计说明书.md",
    "database": "shared/database/ddl/schema.sql",
    "backend": "shared/backend/app.py",
    "frontend": "shared/frontend/templates/base.html",
    "test": "shared/test/测试报告/测试报告.md",
}


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_json(path: Path, default):
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def file_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def iter_files():
    for path in SHARED.rglob("*"):
        if path.is_file():
            rel = path.relative_to(ROOT).as_posix()
            if rel.endswith("manifest.json"):
                continue
            yield path


def build_manifest() -> dict:
    manifest = {}
    for path in iter_files():
        rel = path.relative_to(ROOT).as_posix()
        stat = path.stat()
        manifest[rel] = {
            "hash": file_hash(path),
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
        }
    return manifest


def append_event(event: str, file_path: str) -> None:
    record = {
        "time": now(),
        "event": event,
        "file": file_path,
    }
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def scan() -> list[dict]:
    old = load_json(MANIFEST_FILE, {})
    new = build_manifest()
    changes = []

    old_files = set(old.keys())
    new_files = set(new.keys())

    for file_path in sorted(new_files - old_files):
        changes.append({"event": "created", "file": file_path})

    for file_path in sorted(old_files - new_files):
        changes.append({"event": "deleted", "file": file_path})

    for file_path in sorted(old_files & new_files):
        if old[file_path]["hash"] != new[file_path]["hash"]:
            changes.append({"event": "modified", "file": file_path})

    for change in changes:
        append_event(change["event"], change["file"])

    save_json(MANIFEST_FILE, new)
    return changes


def load_state() -> dict:
    return load_json(STATE_FILE, {
        "project": "在线生鲜商城系统",
        "current_stage": "requirements",
        "completed_stages": [],
        "next_stage": "requirements",
        "last_updated_by": None,
        "stages": STAGES,
    })


def save_state(state: dict) -> None:
    save_json(STATE_FILE, state)


def current_stage() -> str:
    state = load_state()
    return state.get("current_stage", "requirements")


def status() -> None:
    state = load_state()
    stage = state.get("current_stage", "requirements")
    done_file = ROOT / STAGE_DONE_FILE[stage]
    print(f"项目：{state.get('project', '未命名项目')}")
    print(f"当前阶段：{stage}")
    print(f"已完成阶段：{', '.join(state.get('completed_stages', [])) or '暂无'}")
    print(f"当前智能体：{STAGE_AGENT[stage]}")
    print(f"阶段完成标志：{STAGE_DONE_FILE[stage]}")
    print(f"完成标志是否存在：{'是' if done_file.exists() else '否'}")


def recent_events(limit: int = 20) -> str:
    if not EVENTS_FILE.exists():
        return "暂无文件变更记录。"
    lines = EVENTS_FILE.read_text(encoding="utf-8").splitlines()
    if not lines:
        return "暂无文件变更记录。"
    return "\n".join(lines[-limit:])


def prompt() -> None:
    stage = current_stage()
    agent_file = ROOT / STAGE_AGENT[stage]
    agent_text = agent_file.read_text(encoding="utf-8")
    changes = scan()
    change_text = "\n".join(
        [f"- {item['event']}: {item['file']}" for item in changes]
    ) or "本次扫描未发现新增修改。"

    print("=" * 80)
    print(f"当前阶段：{stage}")
    print(f"请把下面内容复制给当前智能体执行。")
    print("=" * 80)
    print(agent_text)
    print("\n## 本次运行前发现的文件变化")
    print(change_text)
    print("\n## 最近文件事件")
    print(recent_events())
    print("\n## 执行要求")
    print("请基于最新共享文件夹内容继续工作，并严格遵守你的写入范围。")


def complete() -> None:
    state = load_state()
    stage = state.get("current_stage", "requirements")
    done_file = ROOT / STAGE_DONE_FILE[stage]

    if not done_file.exists():
        print(f"当前阶段尚未满足完成条件：{STAGE_DONE_FILE[stage]}")
        print("如果确认已完成，请先补齐该文件，或手动调整完成标志。")
        return

    completed = state.get("completed_stages", [])
    if stage not in completed:
        completed.append(stage)

    current_index = STAGES.index(stage)
    if current_index + 1 < len(STAGES):
        next_stage = STAGES[current_index + 1]
    else:
        next_stage = "done"

    state["completed_stages"] = completed
    state["last_updated_by"] = STAGE_AGENT[stage]
    state["current_stage"] = next_stage if next_stage != "done" else stage
    state["next_stage"] = next_stage
    state["updated_at"] = now()
    save_state(state)

    with TASK_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now()} 编排器\n\n")
        f.write(f"- 标记阶段完成：{stage}\n")
        f.write(f"- 下一阶段：{next_stage}\n")

    if next_stage == "done":
        print("全部阶段已完成。")
    else:
        print(f"已完成 {stage}，下一阶段是 {next_stage}。")


def reset() -> None:
    state = {
        "project": "在线生鲜商城系统",
        "current_stage": "requirements",
        "completed_stages": [],
        "next_stage": "requirements",
        "last_updated_by": None,
        "stages": STAGES,
        "updated_at": now(),
    }
    save_state(state)
    save_json(MANIFEST_FILE, build_manifest())
    EVENTS_FILE.write_text("", encoding="utf-8")
    print("流程状态已重置。")


def watch(interval: float) -> None:
    print(f"开始监听 shared 文件夹，每 {interval} 秒扫描一次。按 Ctrl+C 停止。")
    try:
        while True:
            changes = scan()
            for item in changes:
                print(f"[{now()}] {item['event']}: {item['file']}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n已停止监听。")


def main() -> None:
    parser = argparse.ArgumentParser(description="AgenticTeam 顺序编排器")
    parser.add_argument("command", choices=["status", "scan", "prompt", "complete", "reset", "watch"])
    parser.add_argument("--interval", type=float, default=2.0, help="watch 模式扫描间隔秒数")
    args = parser.parse_args()

    AGENTIC.mkdir(parents=True, exist_ok=True)

    if args.command == "status":
        status()
    elif args.command == "scan":
        changes = scan()
        if not changes:
            print("未发现文件变化。")
        else:
            for item in changes:
                print(f"{item['event']}: {item['file']}")
    elif args.command == "prompt":
        prompt()
    elif args.command == "complete":
        complete()
    elif args.command == "reset":
        reset()
    elif args.command == "watch":
        watch(args.interval)


if __name__ == "__main__":
    main()
