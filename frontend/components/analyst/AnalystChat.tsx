"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BarChart3, Bot, Loader2, Send, Sparkles, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import { streamAnalystChat, type AnalystFrame } from "@/lib/analystStream";
import {
  VizBlock,
  parseViz,
  looksLikeViz,
  type VizBlob,
} from "./VizBlocks";

// The answer streams in as a sequence of parts: some are prose, some are a
// self-contained chart/table JSON blob. We model each as a typed block so the
// blobs render as real charts/tables instead of raw JSON. Each streaming text
// part carries a stable key (`outputIndex:contentIndex`) so deltas land in the
// right block.
type Block =
  | { kind: "text"; key: string; text: string }
  | { kind: "viz"; key: string; blob: VizBlob };

interface Turn {
  role: "user" | "assistant";
  text?: string; // user turns
  blocks?: Block[]; // assistant turns
  steps?: string[];
  error?: string;
}

const SUGGESTIONS = [
  // Pillar 1 — real-time operational intelligence over live business data.
  "Why did claim approvals slow down in the last 24 hours? Break down average approval time by product line and show a chart.",
  "Which underwriting queues are most backlogged right now — by open count and average age in hours?",
  "Which payment systems have elevated failure rates over the last 24 hours, and what's the top failure reason? Show a bar chart.",
  "Where are fraud investigations increasing — compare cases opened in the last 30 days vs the prior 30 days by product line.",
  // Pillar 2 — AI Customer Intelligence: predict & prevent negative outcomes.
  "How many high-value customers are currently at risk, broken down by risk signal? Show a chart.",
  "What's the single best next-best-action to take right now by total customer lifetime value at risk?",
  "Which feedback topic has the lowest customer sentiment, and how does that relate to churn risk?",
  "Show me customers with repeated payment retries and auth failures in the last 24 hours who are flagged for retention outreach.",
];

// Pulled from the part.title on reasoning frames; if a frame has no title we
// fall back to this generic line so the status never goes blank mid-think.
const DEFAULT_STATUS = "Analyzing your data";

export function AnalystChat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const sessionRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Keep the transcript pinned to the newest content as it streams in.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns, status]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const ask = useCallback(
    async (raw: string) => {
      const message = raw.trim();
      if (!message || busy) return;

      setQuestion("");
      setBusy(true);
      setStatus("Connecting to Aura Analyst");
      setTurns((prev) => [
        ...prev,
        { role: "user", text: message },
        { role: "assistant", blocks: [], steps: [] },
      ]);

      const controller = new AbortController();
      abortRef.current = controller;

      // Mutate the last (assistant) turn in place as frames arrive.
      const patchAssistant = (fn: (t: Turn) => Turn) =>
        setTurns((prev) => {
          const next = [...prev];
          const i = next.length - 1;
          if (i >= 0 && next[i].role === "assistant") next[i] = fn(next[i]);
          return next;
        });

      try {
        const body = {
          message,
          ...(sessionRef.current && { session_id: sessionRef.current }),
        };
        for await (const frame of streamAnalystChat(body, controller.signal)) {
          handleFrame(frame, { setStatus, patchAssistant, sessionRef });
        }
      } catch (e) {
        if (!controller.signal.aborted) {
          const msg = e instanceof Error ? e.message : String(e);
          patchAssistant((t) => ({ ...t, error: msg }));
        }
      } finally {
        setBusy(false);
        setStatus(null);
        abortRef.current = null;
      }
    },
    [busy],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setBusy(false);
    setStatus(null);
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    sessionRef.current = null;
    setTurns([]);
    setStatus(null);
    setBusy(false);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {/* Transcript */}
      <div
        ref={scrollRef}
        className="flex min-h-[34rem] max-h-[68vh] flex-col gap-4 overflow-y-auto rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
      >
        {turns.length === 0 ? (
          <EmptyState onPick={ask} disabled={busy} />
        ) : (
          turns.map((turn, i) => <Bubble key={i} turn={turn} />)
        )}

        {/* Live "agent thinking" indicator while the stream is open. */}
        {busy && status && <ThinkingIndicator status={status} />}
      </div>

      {/* Composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        className="flex items-center gap-2"
      >
        {turns.length > 0 && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={reset}
            disabled={busy}
            title="Start a new conversation"
          >
            New
          </Button>
        )}
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about claims, underwriting, payments, fraud, at-risk customers, next-best actions…"
          disabled={busy}
          aria-label="Ask a question"
        />
        {busy ? (
          <Button type="button" variant="outline" onClick={stop}>
            Stop
          </Button>
        ) : (
          <Button type="submit" disabled={!question.trim()}>
            <Send className="h-4 w-4" />
            Ask
          </Button>
        )}
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Frame handling — translate Analyst SSE events into UI state.
// ---------------------------------------------------------------------------

interface FrameCtx {
  setStatus: (s: string | null) => void;
  patchAssistant: (fn: (t: Turn) => Turn) => void;
  sessionRef: React.MutableRefObject<string | null>;
}

// Append a delta to the text block with the given key, creating it if needed.
function upsertText(blocks: Block[], key: string, append: string): Block[] {
  const i = blocks.findIndex((b) => b.key === key);
  if (i === -1) return [...blocks, { kind: "text", key, text: append }];
  const b = blocks[i];
  if (b.kind !== "text") return blocks; // already finalized into a viz
  const next = [...blocks];
  next[i] = { ...b, text: b.text + append };
  return next;
}

// On part completion, replace the text block with a viz block if its full text
// parsed as a chart/table blob; otherwise keep the authoritative final text.
function finalizeText(blocks: Block[], key: string, fullText: string): Block[] {
  const i = blocks.findIndex((b) => b.key === key);
  const viz = parseViz(fullText);
  const next = [...blocks];
  if (i === -1) {
    next.push(viz ? { kind: "viz", key, blob: viz } : { kind: "text", key, text: fullText });
    return next;
  }
  next[i] = viz
    ? { kind: "viz", key, blob: viz }
    : { kind: "text", key, text: fullText };
  return next;
}

function partKey(d: Record<string, any>): string {
  return `${d.output_index ?? 0}:${d.content_index ?? 0}`;
}

function handleFrame(frame: AnalystFrame, ctx: FrameCtx) {
  const { event, data } = frame;
  const d = (data ?? {}) as Record<string, any>;

  switch (event) {
    case "response.created":
      // Capture the session so follow-up questions resolve "that"/"those".
      ctx.sessionRef.current = d?.response?.session_id ?? ctx.sessionRef.current;
      ctx.setStatus("Thinking");
      break;

    case "response.content_part.added": {
      const part = d?.part ?? {};
      if (part?.type === "reasoning") {
        // A new reasoning step — its title is the human-readable status line.
        const title: string = part.title || DEFAULT_STATUS;
        ctx.setStatus(title);
        ctx.patchAssistant((t) => ({
          ...t,
          steps: [...(t.steps ?? []), title],
        }));
      } else if (part?.type === "output_text") {
        // Start a fresh answer block keyed to this part.
        const key = partKey(d);
        ctx.patchAssistant((t) => ({
          ...t,
          blocks: upsertText(t.blocks ?? [], key, part.text || ""),
        }));
      }
      break;
    }

    case "response.output_text.delta":
      if (typeof d?.delta === "string") {
        const key = partKey(d);
        ctx.setStatus("Writing the answer");
        ctx.patchAssistant((t) => ({
          ...t,
          blocks: upsertText(t.blocks ?? [], key, d.delta),
        }));
      }
      break;

    case "response.output_text.done": {
      // Authoritative full text for the part — parse into a viz if applicable.
      const key = partKey(d);
      const full = typeof d?.text === "string" ? d.text : undefined;
      if (full !== undefined) {
        ctx.patchAssistant((t) => ({
          ...t,
          blocks: finalizeText(t.blocks ?? [], key, full),
        }));
      }
      break;
    }

    case "response.failed":
    case "error": {
      const msg =
        d?.error?.message || d?.message || d?.response?.error || "Analyst error";
      ctx.patchAssistant((t) => ({ ...t, error: String(msg) }));
      break;
    }

    default:
      // response.protocol / reasoning.* / *.done / completed — no UI change.
      break;
  }
}

// ---------------------------------------------------------------------------
// Presentational pieces
// ---------------------------------------------------------------------------

function ThinkingIndicator({ status }: { status: string }) {
  return (
    <div className="flex items-center gap-3 rounded-md bg-s2-purple/5 px-3 py-2 ring-1 ring-inset ring-s2-purple/15">
      <Loader2 className="h-4 w-4 animate-spin text-s2-purple" />
      <span className="text-sm font-medium text-s2-purple">{status}</span>
      <span className="flex gap-1">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="h-1.5 w-1.5 animate-pulse rounded-full bg-s2-purple/60"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </span>
    </div>
  );
}

function BlockView({ block }: { block: Block }) {
  if (block.kind === "viz") return <VizBlock blob={block.blob} />;

  // While a chart/table blob is still streaming its text reads as raw JSON;
  // show a building placeholder instead of dumping the JSON.
  const pending = looksLikeViz(block.text);
  if (pending) {
    return (
      <div className="my-1 flex items-center gap-2 rounded-md border border-dashed border-s2-purple/30 bg-s2-purple/5 px-3 py-3 text-sm text-s2-purple">
        <BarChart3 className="h-4 w-4 animate-pulse" />
        Building {pending}…
      </div>
    );
  }
  if (!block.text.trim()) return null;
  return <Prose text={block.text} />;
}

// Aura returns GitHub-flavored markdown (bold, bullet lists, tables). Render it
// as real markdown so **bold** and tables display instead of literal asterisks.
function Prose({ text }: { text: string }) {
  return (
    <div
      className={cn(
        "leading-relaxed",
        "[&_p]:my-1 [&_strong]:font-semibold [&_strong]:text-gray-900",
        "[&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5",
        "[&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5",
        "[&_h1]:mt-2 [&_h1]:mb-1 [&_h1]:text-base [&_h1]:font-semibold",
        "[&_h2]:mt-2 [&_h2]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold",
        "[&_h3]:mt-2 [&_h3]:mb-1 [&_h3]:text-sm [&_h3]:font-semibold",
        "[&_a]:text-s2-purple [&_a]:underline",
        "[&_code]:rounded [&_code]:bg-gray-200/70 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[0.85em]",
        "[&_table]:my-2 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs",
        "[&_th]:border [&_th]:border-gray-200 [&_th]:bg-gray-100 [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:font-semibold",
        "[&_td]:border [&_td]:border-gray-200 [&_td]:px-2 [&_td]:py-1",
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

function Bubble({ turn }: { turn: Turn }) {
  const isUser = turn.role === "user";
  const blocks = turn.blocks ?? [];
  const hasViz = blocks.some((b) => b.kind === "viz");
  const hasBody = isUser ? !!turn.text : blocks.length > 0 || !!turn.error;

  return (
    <div className={cn("flex animate-fade-in gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-meridian-teal text-white" : "bg-s2-purple text-white",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          "space-y-2 rounded-lg px-4 py-3 text-sm",
          // Let charts/tables use the available width; keep prose comfortable.
          hasViz ? "w-full max-w-full" : "max-w-[85%]",
          isUser
            ? "bg-meridian-teal/10 text-gray-900"
            : "bg-gray-50 text-gray-800 ring-1 ring-inset ring-gray-200",
        )}
      >
        {/* Reasoning trail for assistant turns. */}
        {!isUser && turn.steps && turn.steps.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {turn.steps.map((s, i) => (
              <Badge key={i} variant="default" className="gap-1">
                <Sparkles className="h-3 w-3" />
                {s}
              </Badge>
            ))}
          </div>
        )}

        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{turn.text}</p>
        ) : (
          blocks.map((b) => <BlockView key={b.key} block={b} />)
        )}

        {/* Assistant turn that has started but produced nothing yet. */}
        {!isUser && !hasBody && <p className="text-gray-400">…</p>}

        {turn.error && (
          <p role="alert" className="text-red-700">
            {turn.error}
          </p>
        )}
      </div>
    </div>
  );
}

function EmptyState({
  onPick,
  disabled,
}: {
  onPick: (q: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-5 py-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-s2-purple/10">
        <Sparkles className="h-6 w-6 text-s2-purple" />
      </div>
      <div>
        <p className="text-base font-semibold text-gray-900">
          Ask every policyholder signal in plain English
        </p>
        <p className="mt-1 text-sm text-gray-500">
          Aura Analyst plans, writes the SQL, and runs it live on the unified
          SingleStore layer — real-time operations (claims, underwriting,
          payments, fraud) and the Customer Intelligence Platform (identity,
          policies, VoC, transcripts, clickstream & telemetry) that predicts and
          prevents negative outcomes. It streams back the answer with its
          reasoning shown live — governed, so every answer is grounded in your
          own data.
        </p>
      </div>
      <div className="grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            disabled={disabled}
            onClick={() => onPick(s)}
            className="rounded-md border border-gray-200 bg-white px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:border-s2-purple/40 hover:bg-s2-purple/5 disabled:opacity-50"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
