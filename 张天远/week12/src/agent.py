"""
统一入口：单次问答 / 多轮对话 / 恢复会话

使用方式：
  # 单次问答（向后兼容）
  python agent.py --mode manual --question "茅台2023年毛利率？"
  python agent.py --mode fc     --question "五粮液近一年股价涨跌幅？"

  # 多轮对话（交互模式）
  python agent.py --mode chat manual
  python agent.py --mode chat fc

  # 恢复已有会话
  python agent.py --mode chat manual --session abc12345

环境变量：
  DASHSCOPE_API_KEY  必填（手动版用 DashScope）
  DEEPSEEK_API_KEY   必填（FC 版用 DeepSeek）
  AGENT_MODEL        默认 qwen-max 或 deepseek-v4-flash
"""

import os
import sys
import argparse

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

sys.path.insert(0, os.path.dirname(__file__))

DEFAULT_QUESTION = "贵州茅台和五粮液2023年的毛利率哪家更高？差多少个百分点？"


def run_chat_mode(mode: str, session_id: str | None = None):
    """交互式多轮对话"""
    from session import AgentSession

    # 加载或创建会话
    if session_id:
        sess = AgentSession.load(session_id)
        if sess is None:
            print(f"会话 {session_id} 不存在，创建新会话")
            sess = AgentSession(mode=mode)
        else:
            print(f"已恢复会话: {session_id}（{len(sess.history)} 轮历史）")
    else:
        sess = AgentSession(mode=mode)

    # 初始化 system prompt
    if not sess.messages:
        if mode == "manual":
            from react_manual import SYSTEM_PROMPT
        else:
            from react_function_calling import FC_SYSTEM_PROMPT as SYSTEM_PROMPT
        sess.initialize(SYSTEM_PROMPT)

    # 选择引擎
    if mode == "manual":
        from react_manual import chat_from_messages, run_and_print
        model_name = os.getenv("AGENT_MODEL", "qwen-max")
    else:
        from react_function_calling import chat_from_messages
        model_name = os.getenv("AGENT_MODEL", "deepseek-v4-flash")

    sess.save()

    print(f"\n{'='*60}")
    print(f"多轮对话模式 | 模型: {model_name} | 实现: {'手写Prompt解析' if mode == 'manual' else 'Function Calling'}")
    print(f"会话ID: {sess.session_id} | 已对话 {len(sess.history)} 轮")
    print(f"输入问题开始对话，输入 /exit 退出，输入 /history 查看历史")
    print('='*60)

    try:
        while True:
            # 用户输入
            try:
                user_input = input(f"\n[{sess.session_id}]({len(sess.history)+1})> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n退出对话")
                break

            if not user_input:
                continue
            if user_input.lower() in ("/exit", "/quit", "/q"):
                print("退出对话")
                break
            if user_input.lower() == "/history":
                for i, turn in enumerate(sess.history, 1):
                    print(f"\n  ── 第{i}轮 ──")
                    print(f"  Q: {turn['question']}")
                    print(f"  A: {turn['answer'][:200]}")
                continue

            # 执行 ReAct 循环
            sess.add_user_message(user_input)

            print(f"\n{'─'*60}")
            collected_steps = []
            final_answer = ""
            import time
            start = time.time()

            for step_data in chat_from_messages(sess.messages):
                stype = step_data.get("type", "")
                collected_steps.append(step_data)

                if stype == "action":
                    thought = step_data.get("thought", "")
                    if thought:
                        print(f"[Step {step_data['step']}] 🧠 {thought[:150]}")
                    print(f"  🔧 {step_data['action']}({step_data['action_input']})")
                    obs = str(step_data.get("observation", ""))[:200]
                    print(f"  👁 {obs}")

                elif stype == "final":
                    final_answer = step_data.get("answer", "")
                    elapsed = time.time() - start
                    print(f"\n✅ Final Answer ({elapsed:.1f}s):")
                    print(f"  {final_answer}")

                elif stype in ("error", "max_steps"):
                    print(f"⚠️  {step_data.get('answer', step_data.get('observation', ''))}")

            # 记录历史
            sess.record_turn(user_input, final_answer, collected_steps)
            sess.save()

    finally:
        sess.save()
        print(f"\n会话已保存: {sess.session_id}")
        print(f"恢复命令: python agent.py --mode chat {mode} --session {sess.session_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReAct Financial Agent")
    parser.add_argument(
        "--mode",
        default="manual",
        help="manual=手写版  fc=FC版  chat=多轮对话（后跟 manual/fc）",
    )
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--max_steps", type=int, default=10)
    parser.add_argument("--session", default=None, help="恢复指定会话ID")
    args = parser.parse_args()

    # 多轮对话模式
    if args.mode == "chat":
        # args.question 在 chat 模式下作为子模式（manual/fc）
        chat_mode = args.question if args.question != DEFAULT_QUESTION else "manual"
        if chat_mode not in ("manual", "fc"):
            print(f"用法: python agent.py --mode chat [manual|fc] [--session ID]")
            sys.exit(1)
        run_chat_mode(chat_mode, args.session)
        sys.exit(0)

    # 单次问答（向后兼容）
    if args.mode == "manual":
        from react_manual import run_and_print
    else:
        from react_function_calling import run_and_print

    run_and_print(args.question, args.max_steps)
