// Client-side SSE reader for the Aura Analyst chat proxy (POST /analyst/chat).
//
// EventSource can't POST, so we stream the fetch body ourselves: read the
// ReadableStream, split on the blank-line frame boundary, and parse each
// `event:` / `data:` block. The caller gets one decoded frame at a time and
// switches on `event` to drive the live "agent thinking" status + answer text.

import { apiBase } from "./api";

export interface AnalystFrame {
  event: string;
  data: unknown;
}

export interface AnalystChatBody {
  message: string;
  session_id?: string;
  included_events?: string[];
}

/**
 * POST a question to the chat proxy and yield each SSE frame as it arrives.
 * Pass an AbortSignal to cancel an in-flight stream (e.g. on unmount / Stop).
 */
export async function* streamAnalystChat(
  body: AnalystChatBody,
  signal?: AbortSignal,
): AsyncGenerator<AnalystFrame> {
  const res = await fetch(`${apiBase()}/analyst/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    cache: "no-store",
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.text()) || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Frames are separated by a blank line. Handle both \n\n and \r\n\r\n.
      let sep: number;
      while ((sep = indexOfFrameEnd(buffer)) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep).replace(/^(\r?\n){2}/, "");
        const frame = parseFrame(raw);
        if (frame) yield frame;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function indexOfFrameEnd(buf: string): number {
  const a = buf.indexOf("\n\n");
  const b = buf.indexOf("\r\n\r\n");
  if (a === -1) return b;
  if (b === -1) return a;
  return Math.min(a, b);
}

function parseFrame(raw: string): AnalystFrame | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of raw.split(/\r?\n/)) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }
  if (dataLines.length === 0) return null;
  const dataStr = dataLines.join("\n");
  let data: unknown = dataStr;
  try {
    data = JSON.parse(dataStr);
  } catch {
    // leave as raw string (e.g. an upstream error body)
  }
  return { event, data };
}
