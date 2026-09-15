"""Lab: Server-Sent Events, reconnection and event replay.

A minimal SSE server (asyncio, standard library only) plus a client that
disconnects on purpose, to show:

  1. how events are framed on the wire
  2. what a client misses when it reconnects without Last-Event-ID
  3. how the server replays missed events when the client sends Last-Event-ID
  4. that keep-alive comments do not disturb event parsing

The server keeps every event in a list, standing in for the agent_events table.

Run:  python sse_lab.py   (standard library only)
"""

from __future__ import annotations

import asyncio
import time

HOST, PORT = "127.0.0.1", 8421
KEEPALIVE_SECONDS = 0.3

events: list[tuple[int, str, str]] = []  # (seq, event name, data)
start = time.monotonic()


def log(who: str, message: str) -> None:
    print(f"  [{time.monotonic() - start:5.2f}s] {who:<6} {message}")


async def produce_events() -> None:
    """Emit events on a fixed schedule, whether or not a client is connected."""
    script = [
        (0.2, "message.delta", '{"text":"我先看看你衣橱里有哪些下装。"}'),
        (0.6, "tool.started", '{"tool":"search_wardrobe"}'),
        (1.0, "tool.finished", '{"tool":"search_wardrobe","count":4}'),
        (1.4, "render.stage", '{"renderId":"R-3391","stageNo":1}'),
        (1.8, "render.stage", '{"renderId":"R-3391","stageNo":2}'),
        (2.2, "done", '{"turnId":"T-77"}'),
    ]
    for delay, name, data in script:
        await asyncio.sleep(max(0.0, start + delay - time.monotonic()))
        events.append((len(events) + 1, name, data))
        log("server", f"produced seq={len(events)} {name}")


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    request = await reader.readuntil(b"\r\n\r\n")
    headers = request.decode().split("\r\n")
    last_event_id = 0
    for line in headers:
        if line.lower().startswith("last-event-id:"):
            last_event_id = int(line.split(":", 1)[1].strip())
    log("server", f"client connected, Last-Event-ID={last_event_id or 'none'}")

    writer.write(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/event-stream\r\n"
        b"Cache-Control: no-cache\r\n"
        b"Connection: keep-alive\r\n\r\n"
    )
    # Replay everything the client has not seen yet, then follow new events live.
    replayed = [e for e in events if e[0] > last_event_id]
    if replayed:
        log("server", f"replaying {len(replayed)} event(s): seq {[e[0] for e in replayed]}")
    sent = last_event_id
    try:
        while True:
            pending = [e for e in events if e[0] > sent]
            if pending:
                for seq, name, data in pending:
                    frame = f"id: {seq}\nevent: {name}\ndata: {data}\n\n"
                    writer.write(frame.encode())
                    sent = seq
                await writer.drain()
            else:
                writer.write(b": keep-alive\n\n")  # comment line, ignored by parsers
                await writer.drain()
            await asyncio.sleep(KEEPALIVE_SECONDS)
    except (ConnectionResetError, BrokenPipeError):
        log("server", "client disconnected")
    finally:
        writer.close()


class SSEParser:
    """Incremental parser for the text/event-stream format."""

    def __init__(self) -> None:
        self.buffer = ""
        self.comments = 0

    def feed(self, chunk: str) -> list[tuple[int | None, str, str]]:
        self.buffer += chunk
        out: list[tuple[int | None, str, str]] = []
        while "\n\n" in self.buffer:
            block, self.buffer = self.buffer.split("\n\n", 1)
            seq: int | None = None
            name = "message"
            data_lines: list[str] = []
            is_comment = False
            for line in block.split("\n"):
                if line.startswith(":"):
                    is_comment = True
                elif line.startswith("id:"):
                    seq = int(line[3:].strip())
                elif line.startswith("event:"):
                    name = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
            if is_comment:
                self.comments += 1
                continue
            out.append((seq, name, "\n".join(data_lines)))
        return out


async def consume(label: str, last_event_id: int | None, stop_after: int | None, duration: float) -> int:
    """Connect, read events, and return the last seq seen."""
    reader, writer = await asyncio.open_connection(HOST, PORT)
    request = f"GET /v1/conversations/C-1/events HTTP/1.1\r\nHost: {HOST}\r\nAccept: text/event-stream\r\n"
    if last_event_id is not None:
        request += f"Last-Event-ID: {last_event_id}\r\n"
    writer.write((request + "\r\n").encode())
    await writer.drain()
    await reader.readuntil(b"\r\n\r\n")  # skip response headers

    parser = SSEParser()
    seen = last_event_id or 0
    count = 0
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        try:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=deadline - time.monotonic())
        except (asyncio.TimeoutError, ConnectionResetError):
            break
        if not chunk:
            break
        for seq, name, data in parser.feed(chunk.decode()):
            seen = seq or seen
            count += 1
            log(label, f"received seq={seq} {name} {data}")
            if stop_after is not None and count >= stop_after:
                writer.close()
                log(label, "disconnecting on purpose")
                return seen
    writer.close()
    log(label, f"keep-alive comments ignored: {parser.comments}")
    return seen


async def main() -> None:
    server = await asyncio.start_server(handle_client, HOST, PORT)
    producer = asyncio.create_task(produce_events())

    print("\n[1] connect from the beginning, then drop the connection after 2 events")
    seen = await consume("client", None, stop_after=2, duration=3.0)

    print(f"\n[2] reconnect WITHOUT Last-Event-ID (client had seen up to seq={seen})")
    await asyncio.sleep(0.9)  # events keep being produced while the client is away
    await consume("naive", None, stop_after=None, duration=0.8)

    print(f"\n[3] reconnect WITH Last-Event-ID: {seen}")
    await consume("client", seen, stop_after=None, duration=1.5)

    await producer
    server.close()
    await server.wait_closed()

    print("\n[4] what the server stored")
    for seq, name, _ in events:
        print(f"  seq={seq} {name}")


if __name__ == "__main__":
    asyncio.run(main())
