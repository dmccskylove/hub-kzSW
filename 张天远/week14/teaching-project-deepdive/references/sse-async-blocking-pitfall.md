# SSE 流式推送：async 函数中直接消费同步 Generator 导致阻塞

## 现象

前端收到 SSE 事件不是逐个到达，而是等 LLM 推理全部完成后一次性刷新。

## 根因

```python
# 错误写法：async 函数中直接 for 消费同步 generator
async def _chat_stream():
    for step_data in chat_from_messages(messages, max_steps):
        # chat_from_messages() 内部有 client.chat.completions.create()
        # 这是同步阻塞调用，阻塞事件循环，HTTP 无法发送数据
        yield _sse(step_data)
```

`client.chat.completions.create()` 在同步 generator 的 `__next__()` 中执行，阻塞了整个事件循环。Starlette 的 `StreamingResponse` 需要事件循环空闲才能把 `yield` 的数据通过网络发送。LLM 推理期间（5-15s）事件循环被阻塞，所有 SSE 数据积压，最后一次性到达。

## 修复

```python
# 正确写法：同步 generator 跑在独立线程，通过 asyncio.Queue 传递
async def _chat_stream():
    queue: asyncio.Queue = asyncio.Queue()
    _SENTINEL = object()

    def _worker():
        try:
            for step_data in chat_from_messages(messages, max_steps):
                queue.put_nowait(step_data)
        finally:
            queue.put_nowait(_SENTINEL)

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _worker)

    while True:
        step_data = await queue.get()
        if step_data is _SENTINEL:
            break
        yield _sse(step_data)
```

## 通用原则

任何在 FastAPI SSE `StreamingResponse` 的 async generator 中被消费的同步 generator，如果其内部有阻塞 I/O，都必须用 `run_in_executor` + `asyncio.Queue` 模式将阻塞操作隔离到独立线程。
