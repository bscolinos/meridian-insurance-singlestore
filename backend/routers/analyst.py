"""Aura Analyst proxy router.

Holds the server-side Analyst API key and forwards natural-language questions
to SingleStore Aura Analyst (text-to-SQL). Mounted at /analyst by main.py.

Two routes, same key + domain context:
  POST /analyst/query  -> single JSON object (sql / data / chart / text)
  POST /analyst/chat   -> passthrough SSE stream (reasoning titles + token
                          deltas) so the UI can show "agent thinking" status

The key is read from the environment at request time and never returned to the
browser — the frontend only ever talks to this proxy.
"""
from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["analyst"])


def _cfg() -> tuple[str, str]:
    url = os.environ.get("ANALYST_API_URL")
    key = os.environ.get("ANALYST_API_KEY")
    if not url or not key:
        raise HTTPException(
            status_code=503,
            detail="Analyst not configured: set ANALYST_API_URL and ANALYST_API_KEY",
        )
    return url, key


def _query_url(url: str) -> str:
    return url[:-5] + "/query" if url.endswith("/chat") else url


def _chat_url(url: str) -> str:
    return url[:-6] + "/chat" if url.endswith("/query") else url


# ---------------------------------------------------------------------------
# Structured query — single JSON object. Used for programmatic calls; the demo
# UI uses /chat for the live "thinking" status, but this stays available.
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    message: str = Field(min_length=1)
    output_modes: list[str] | None = None       # e.g. ["sql","data","chart"]
    session_id: str | None = None


@router.post("/query")
async def query(req: QueryRequest) -> dict:
    url, key = _cfg()
    payload: dict = {"message": req.message}
    if req.output_modes:
        payload["output_modes"] = req.output_modes
    if req.session_id:
        payload["session_id"] = req.session_id

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                _query_url(url),
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json=payload,
            )
    except httpx.HTTPError as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Analyst upstream error: {e}")

    trace_id = resp.headers.get("singlestore-trace-id")
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:  # noqa: BLE001
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)

    data = resp.json()
    if trace_id:
        data["_trace_id"] = trace_id
    return data


# ---------------------------------------------------------------------------
# Streaming chat — SSE passthrough. Streams the upstream frames verbatim so the
# frontend sees response.created (session_id), response.content_part.added
# (reasoning titles -> the live status line), response.reasoning.* and
# response.output_text.delta (the streamed answer), and response.completed.
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    included_events: list[str] | None = None     # omit/[] -> all events
    session_id: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    url, key = _cfg()
    payload: dict = {"message": req.message}
    if req.included_events:
        payload["included_events"] = req.included_events
    if req.session_id:
        payload["session_id"] = req.session_id

    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    _chat_url(url),
                    headers={"Authorization": f"Bearer {key}",
                             "Content-Type": "application/json",
                             "Accept": "text/event-stream"},
                    json=payload,
                ) as resp:
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        yield f"event: error\ndata: {body.decode('utf-8', 'replace')}\n\n"
                        return
                    # Raw passthrough preserves SSE framing exactly.
                    async for chunk in resp.aiter_raw():
                        if chunk:
                            yield chunk
        except httpx.HTTPError as e:  # noqa: BLE001
            yield f'event: error\ndata: {{"message": "Analyst upstream error: {e}"}}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
