"""subagent.py — 子任务 Agent 并行执行（Orchestrator-Workers）

SubAgent：轻量 ReAct 循环（无记忆/skills 系统），工具集 = 基础 4 工具（不含 dispatch_subagents，防递归）。
多个 subagent 用 ThreadPoolExecutor 并行执行，步骤事件通过回调推入共享队列（SSE 桥接）。

设计对齐 PPT Graph Engineering：主 agent 派发（fan-out）→ subagent 并行 → 结果回收（fan-in）。
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .llm_config import chat_with_tools
from .tool_executor import ToolExecutor

SUB_MAX_TURNS = 8  # subagent 回合上限（比主 agent 少，防失控）
SUB_RESULT_MAX_CHARS = 500  # 每个 subagent 结果回灌主 agent 时截短（防撑爆 context）
SUB_OBS_MAX_CHARS = 500  # 单步 Observation 截短（展示用）
MAX_SUBAGENTS = 5  # 单次派发上限保护

SUB_SYSTEM = """你是子任务执行 Agent，被主管 Agent 分派了以下子任务：

【子任务】{topic}

可用工具：write_file / read_file / list_files / shell_exec（你不能再次派发其他 agent）

执行规则：
1. 专注完成自己的子任务，不要做任务之外的事
2. 不确定目录结构时先 list_files 一次即可，不要反复探索
3. 子任务要求的输出文件必须按描述中的路径保存
4. ★★ 并行竞争铁律：你与其他 subagent 同时工作，依赖的文件【尚未生成】。
   若 read_file/查找依赖失败——【禁止】反复查找或等待，直接基于子任务描述独立完成
   （描述已自包含接口规格）。任何"找文件"类操作最多 1 次。
5. 完成后用最终回复输出：任务完成摘要（做了什么、关键结果/文件路径）；未完成则说明原因与已做部分
"""


class SubAgent:
    """单个子任务 Agent：独立 ToolExecutor（无 dispatch 工具）+ 独立 ReAct 循环"""

    def __init__(self, sid: int, topic: str, work_dir: str,
                 on_step: Callable | None = None, on_done: Callable | None = None):
        self.sid = sid
        self.topic = topic
        self.work_dir = work_dir
        self.tool_exec = ToolExecutor(work_dir=work_dir)  # 独立实例：工具集自动排除 dispatch_subagents
        self.on_step = on_step  # (sid, step_dict)
        self.on_done = on_done  # (sid, duration, summary)
        self.trace: list[dict] = []
        self.duration = 0.0

    def run(self) -> str:
        """运行 ReAct 循环，返回最终摘要"""
        start = time.time()
        system = SUB_SYSTEM.format(topic=self.topic, work_dir=self.work_dir)
        messages = [{"role": "user", "content": self.topic}]
        tools = self.tool_exec.get_schemas()
        final = ""
        turn = 0

        while turn < SUB_MAX_TURNS:
            turn += 1
            result = chat_with_tools(messages, system=system, tools=tools)

            if result.tool_calls:
                for tc in result.tool_calls:
                    name = tc["name"]
                    args = tc["arguments"]
                    step = {"type": "react_act", "turn": turn, "tool": name, "args": args}
                    self.trace.append(step)
                    if self.on_step:
                        self.on_step(self.sid, step)

                    obs = self.tool_exec.execute(name, args)
                    obs_step = {"type": "react_observe", "turn": turn, "tool": name,
                                "result": obs[:SUB_OBS_MAX_CHARS]}
                    self.trace.append(obs_step)
                    if self.on_step:
                        self.on_step(self.sid, obs_step)

                    # 构造 assistant tool_calls 消息（★ 必须回传 reasoning_content）
                    asst_msg = {
                        "role": "assistant", "content": None,
                        "tool_calls": [{
                            "id": tc["id"], "type": "function",
                            "function": {"name": name,
                                         "arguments": json.dumps(args, ensure_ascii=False)},
                        }],
                    }
                    if result.reasoning_content:
                        asst_msg["reasoning_content"] = result.reasoning_content
                    messages.append(asst_msg)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": obs})

            elif result.content:
                final = result.content
                break
            else:
                break

        if not final:
            final = f"(subagent {self.sid} reached max turns without final answer)"
        self.duration = time.time() - start
        if self.on_done:
            self.on_done(self.sid, self.duration, final)
        return final


def run_subagents(subtasks: list[str], work_dir: str,
                  on_step: Callable | None = None, on_done: Callable | None = None,
                  serial: bool = False) -> tuple[list[dict], dict]:
    """并行执行多个 subagent（fan-out / fan-in）。

    serial=True 时退化为 for 循环（串行基线，A/B 对比用）。
    返回 (results, stats)：
      results: [{sid, topic, duration, summary}]
      stats:   {subagent_count, wall_clock, serial_sum, parallel_mode}
    """
    subtasks = subtasks[:MAX_SUBAGENTS]
    agents = [SubAgent(i, t, work_dir, on_step=on_step, on_done=on_done)
              for i, t in enumerate(subtasks)]

    wall_start = time.time()
    if serial:
        finals = [a.run() for a in agents]
    else:
        with ThreadPoolExecutor(max_workers=len(agents)) as pool:
            finals = list(pool.map(lambda a: a.run(), agents))
    wall_clock = time.time() - wall_start

    results = [{"sid": a.sid, "topic": a.topic,
                "duration": round(a.duration, 2), "summary": finals[i]}
               for i, a in enumerate(agents)]
    stats = {
        "subagent_count": len(agents),
        "wall_clock": round(wall_clock, 2),
        "serial_sum": round(sum(a.duration for a in agents), 2),
        "parallel_mode": "serial" if serial else "threadpool",
    }
    return results, stats


def format_dispatch_observation(results: list[dict], stats: dict) -> str:
    """把 subagent 结果汇总成 Observation 字符串，回灌主 agent"""
    parts = []
    for r in results:
        summary = r["summary"][:SUB_RESULT_MAX_CHARS]
        parts.append(f"[Subagent {r['sid']}] ({r['duration']}s) {summary}")
    speedup = round(stats["serial_sum"] / stats["wall_clock"], 2) if stats["wall_clock"] > 0 else 0
    parts.append(
        f"并行统计: {stats['subagent_count']} 个 subagent，"
        f"并行墙钟 {stats['wall_clock']}s vs 串行基线 {stats['serial_sum']}s，"
        f"并行加速 {speedup}×"
    )
    return "\n\n".join(parts)


def parse_subtasks(raw: str) -> list[str]:
    """解析 dispatch_subagents 的 subtasks 参数。
    优先 JSON 数组；失败时按 | 或换行拆分。
    """
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except json.JSONDecodeError:
        pass
    for sep in ("|", "\n", ";"):
        if sep in raw:
            return [x.strip() for x in raw.split(sep) if x.strip()]
    return [raw]


def build_dispatch_handler(work_dir: str, event_queue) -> Callable[[dict], str]:
    """构造 dispatch_subagents 工具的 execute 函数（由 server 注入）。

    event_queue：thread-safe queue.Queue，subagent 事件经此桥接回 SSE 主循环。
    返回函数签名 (params: dict) -> str（Observation 汇总）。
    """
    def dispatch(params: dict) -> str:
        subtasks = parse_subtasks(params.get("subtasks", ""))
        if not subtasks:
            return "Error: dispatch_subagents requires non-empty subtasks"
        if len(subtasks) > MAX_SUBAGENTS:
            subtasks = subtasks[:MAX_SUBAGENTS]

        event_queue.put({"type": "dispatch", "subtasks": subtasks})

        def on_step(sid: int, step: dict):
            # ★ step 内自带 "type":"react_act/observe"，需强制覆盖为 subagent_step（否则 type 被内层覆盖，前端收不到）
            event_queue.put({"sid": sid, **step, "type": "subagent_step"})

        def on_done(sid: int, duration: float, summary: str):
            event_queue.put({"type": "subagent_done", "sid": sid,
                             "duration": round(duration, 2), "summary": summary[:500]})

        results, stats = run_subagents(subtasks, work_dir,
                                       on_step=on_step, on_done=on_done)
        event_queue.put({"type": "dispatch_done", "stats": stats})
        return format_dispatch_observation(results, stats)

    return dispatch
