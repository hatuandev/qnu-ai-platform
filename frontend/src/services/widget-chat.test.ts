import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { runInNewContext } from "node:vm";

class Element {
  textContent = "";
  value = "";
  style = {};
  children: Element[] = [];
  handlers: Record<string, () => Promise<void>> = {};
  appendChild(child: Element) {
    this.children.push(child);
  }
  addEventListener(name: string, handler: () => Promise<void>) {
    this.handlers[name] = handler;
  }
  focus() {}
}

async function widget(frames: string[]) {
  const nodes = new Map<string, Element>();
  const node = (id: string) => {
    let result = nodes.get(id);
    if (!result) {
      result = new Element();
      nodes.set(id, result);
    }
    return result;
  };
  const requests: {
    url: string;
    body: { conversation_id?: string };
    headers: Record<string, string>;
  }[] = [];
  const source = await readFile(
    new URL("../../public/embed/qnu-chat-widget.js", import.meta.url),
    "utf8",
  );
  runInNewContext(source, {
    window: { location: { origin: "http://localhost:3000" } },
    document: {
      currentScript: {
        getAttribute: (key: string) =>
          key === "data-assistant" ? "admissions" : null,
      },
      body: new Element(),
      head: new Element(),
      createElement: () => new Element(),
      getElementById: node,
    },
    TextDecoder,
    fetch: async (
      url: string,
      options: { body: string; headers: Record<string, string> },
    ) => {
      const frame = frames[requests.length];
      requests.push({
        url,
        body: JSON.parse(options.body),
        headers: options.headers,
      });
      const bytes = new TextEncoder().encode(frame);
      const stream = new ReadableStream({
        start(controller) {
          for (let index = 0; index < bytes.length; index += 7)
            controller.enqueue(bytes.slice(index, index + 7));
          controller.close();
        },
      });
      return new Response(stream, {
        headers: { "X-Conversation-Token": "fixture-capability" },
      });
    },
  });
  return {
    requests,
    node,
    send: async (message: string) => {
      node("qnu-widget-input").value = message;
      await node("qnu-widget-send").handlers.click();
      return node("qnu-widget-messages").children.at(-1)?.textContent;
    },
  };
}

const complete =
  'event: status\r\ndata: {"conversation_id":"fixture-session"}\r\n\r\nevent: token\r\ndata: {"delta":"Xin chào bạn!"}\r\n\r\nevent: done\r\ndata: {"conversation_id":"fixture-session"}\r\n\r\n';

test("standalone widget handles fragmented UTF-8/SSE and continues its own server conversation", async () => {
  const client = await widget([complete, complete]);
  assert.equal(await client.send("Xin chào"), "Xin chào bạn!");
  assert.equal(await client.send("Cảm ơn"), "Xin chào bạn!");
  assert.equal(client.requests[0].body.conversation_id, undefined);
  assert.equal(client.requests[1].body.conversation_id, "fixture-session");
  assert.equal(
    client.requests[1].headers["X-Conversation-Token"],
    "fixture-capability",
  );
  assert.equal(client.requests[0].url.endsWith("/admissions/chat"), true);
  assert.equal(client.requests[0].url.includes("debug"), false);
});

test("standalone widget displays an explicit stream error without a fabricated answer", async () => {
  const client = await widget([
    'event: error\ndata: {"message":"Thiếu căn cứ đã xuất bản."}\n\n',
  ]);
  assert.equal(await client.send("Một câu hỏi"), "Thiếu căn cứ đã xuất bản.");
});

test("standalone widget never marks a truncated answer as complete", async () => {
  const client = await widget([
    'event: token\ndata: {"delta":"Bản nháp chưa hoàn tất"}\n\n',
  ]);
  assert.match((await client.send("Một câu hỏi")) || "", /bị gián đoạn/);
});
