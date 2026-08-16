"""CLI 前端 — 与 Agent 后端交互

职责：
  1. 发送消息到后端 /chat（SSE 流式接收）
  2. 展示 Skills 匹配、记忆加载、Context 组装全过程
  3. 支持命令：/flush, /skills, /status, /new, /exit

用法：python -m src.cli [--port PORT]
"""
import sys
import json
import argparse
import httpx

BASE_URL = "http://localhost:8000"
SESSION_ID = None


def print_header():
    print("=" * 60)
    print("  Agent 记忆系统 + Skills 渐进式加载")
    print("  输入消息开始对话，输入 /help 查看命令")
    print("=" * 60)


def print_help():
    print("""
命令：
  /flush    - 手动触发 Memory Flush
  /skills   - 列出所有可用 Skills
  /status   - 查看系统状态
  /new      - 开始新会话（自动 Flush 旧会话）
  /help     - 显示此帮助
  /exit     - 退出

直接输入文字即可对话。系统会自动匹配 Skills 并渐进式加载。
""")


def get_status():
    r = httpx.get(f"{BASE_URL}/status")
    if r.status_code == 200:
        s = r.json()
        print(f"\n📊 系统状态")
        print(f"  会话 ID: {s['session_id']}")
        print(f"  消息数:  {s['message_count']}")
        print(f"  记忆量:  {s['memory_chars']} 字符")
        print(f"  Skills:  {len(s['skills_available'])} 个")
        for sk in s['skills_available']:
            print(f"    - {sk['name']}  [{', '.join(sk['triggers'])}]")
        global SESSION_ID
        SESSION_ID = s['session_id']
    else:
        print(f"❌ 获取状态失败: {r.status_code}")


def list_skills():
    r = httpx.get(f"{BASE_URL}/skills")
    if r.status_code == 200:
        skills = r.json()
        print(f"\n🔧 可用 Skills ({len(skills)} 个):")
        for s in skills:
            print(f"  📌 {s['name']}")
            print(f"     {s['description']}")
            print(f"     触发: {', '.join(s['triggers'])}")
    else:
        print(f"❌ 获取 Skills 失败: {r.status_code}")


def do_flush():
    r = httpx.post(f"{BASE_URL}/flush")
    if r.status_code == 200:
        result = r.json()
        print(f"\n💾 {result['summary']}")
        if result.get('user_updates'):
            print("  用户画像更新:")
            for u in result['user_updates']:
                print(f"    - {u}")
        if result.get('memory_entries'):
            print("  记忆条目:")
            for m in result['memory_entries']:
                print(f"    - {m}")
    else:
        print(f"❌ Flush 失败: {r.status_code}")


def do_new_session():
    r = httpx.post(f"{BASE_URL}/new")
    if r.status_code == 200:
        global SESSION_ID
        SESSION_ID = r.json()['session_id']
        print(f"\n🆕 新会话已创建: {SESSION_ID}")
    else:
        print(f"❌ 创建会话失败: {r.status_code}")


def send_message(message: str):
    """SSE 流式发送消息"""
    global SESSION_ID
    if SESSION_ID is None:
        get_status()
        if SESSION_ID is None:
            print("❌ 无法获取会话 ID，请检查后端是否运行")
            return

    print()  # blank line before response

    with httpx.stream(
        "POST",
        f"{BASE_URL}/chat",
        json={"session_id": SESSION_ID, "message": message},
        timeout=120.0,
    ) as r:
        if r.status_code != 200:
            print(f"❌ 请求失败: {r.status_code}")
            return

        in_reply = False
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            etype = data.get("type", "")

            if etype == "skill_match":
                print(f"🔍 Skills 索引匹配中...")
                print(f"🔧 命中: {data['name']} (置信度: {data['confidence']}, 触发词: {data['triggers']})")

            elif etype == "skill_loaded":
                print(f"📥 加载 Skill: {data['name']} (+{data['size_chars']} 字符)")

            elif etype == "context_assembly":
                print(f"🧠 Context 组装: {data['total_chars']} 字符, {data['history_turns']} 轮历史")
                if data.get('skills_loaded'):
                    print(f"   Skills 已加载: {', '.join(data['skills_loaded'])}")

            elif etype == "react_turn":
                print(f"\n🔄 ReAct 轮次 {data['turn']}")

            elif etype == "react_act":
                args_str = json.dumps(data['args'], ensure_ascii=False)
                if len(args_str) > 80:
                    args_str = args_str[:80] + "..."
                print(f"   🛠️ 调用工具: {data['tool']}({args_str})")

            elif etype == "react_observe":
                result_preview = data['result'][:120].replace('\n', ' ')
                print(f"   👁️ 观察结果: {result_preview}")

            elif etype == "dispatch":
                print(f"🚀 派发 {len(data['subtasks'])} 个 subagent 并行执行:")
                for i, t in enumerate(data['subtasks']):
                    print(f"   [{i}] {t[:60]}{'...' if len(t) > 60 else ''}")

            elif etype == "subagent_step":
                tag = f"[sub{data['sid']}]"
                if data.get('tool'):
                    args_str = json.dumps(data['args'], ensure_ascii=False)
                    if len(args_str) > 80:
                        args_str = args_str[:80] + "..."
                    print(f"   {tag} 🛠️ 调用工具: {data['tool']}({args_str})")
                else:
                    result_preview = data['result'][:100].replace('\n', ' ')
                    print(f"   {tag} 👁️ {result_preview}")

            elif etype == "subagent_done":
                print(f"   [sub{data['sid']}] ✅ 完成 ({data['duration']}s): {data['summary'][:80]}")

            elif etype == "dispatch_done":
                s = data['stats']
                speedup = round(s['serial_sum'] / s['wall_clock'], 2) if s['wall_clock'] > 0 else 0
                print(f"⚡ 并行统计: {s['subagent_count']} 个 subagent · 墙钟 {s['wall_clock']}s "
                      f"vs 串行基线 {s['serial_sum']}s · 加速 {speedup}×")

            elif etype == "context_preloaded":
                print(f"📦 预加载项目上下文: +{data['chars']} 字符")

            elif etype == "token":
                if not in_reply:
                    print("💬 ", end="", flush=True)
                    in_reply = True
                print(data["content"], end="", flush=True)

            elif etype == "skill_released":
                print(f"\n📤 Skill Context 已释放")

            elif etype == "done":
                if not in_reply:
                    print("💬 (空回复)", end="")
                print(f"\n   [消息数: {data['message_count']}]")
                if data.get('auto_flush_triggered'):
                    print("   ⚡ 自动 Flush 已触发")

            elif etype == "auto_flush":
                print(f"   💾 自动 Flush: 画像 {len(data.get('user_updates',[]))} 项, 记忆 {len(data.get('memory_entries',[]))} 条")

            elif etype == "error":
                print(f"\n❌ 错误: {data['message']}")


def main():
    parser = argparse.ArgumentParser(description="Agent Skills System CLI")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = f"http://localhost:{args.port}"
    print_header()

    # 检查后端
    try:
        r = httpx.get(f"{BASE_URL}/status", timeout=5.0)
        if r.status_code != 200:
            print("❌ 后端未就绪，请先启动: uvicorn src.server:app --host 0.0.0.0 --port 8000")
            return
    except Exception:
        print("❌ 无法连接后端，请先启动: uvicorn src.server:app --host 0.0.0.0 --port 8000")
        return

    get_status()
    print()

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见")
            break

        if not user_input:
            continue

        # Commands
        if user_input.startswith("/"):
            cmd = user_input[1:].lower()
            if cmd == "exit":
                print("👋 再见")
                break
            elif cmd == "help":
                print_help()
            elif cmd == "status":
                get_status()
            elif cmd == "skills":
                list_skills()
            elif cmd == "flush":
                do_flush()
            elif cmd == "new":
                do_new_session()
            else:
                print(f"未知命令: {user_input}")
            continue

        # Normal message
        send_message(user_input)


if __name__ == "__main__":
    main()
