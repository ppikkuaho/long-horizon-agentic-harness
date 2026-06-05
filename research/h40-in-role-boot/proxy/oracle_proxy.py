#!/usr/bin/env python3
"""H40 oracle proxy — ground-truth capture of what pinned Claude Code actually sends.

Pinned CC is pointed here via ANTHROPIC_BASE_URL=http://127.0.0.1:<port>. Every
outbound request is logged verbatim (esp. the `system` blocks + `tools` + `model`),
then either mocked (no real auth needed) or forwarded to the real API.

Modes (env H40_MODE):
  mock     - return a canned SSE assistant turn; no upstream call, no real token needed.
             Lets us capture the client-assembled system prompt with a DUMMY token.
  forward  - pass the request through to https://api.anthropic.com (real token req'd),
             stream the real SSE back. Captures system prompt AND real model behaviour.
  rewrite  - like forward, but mutate the request body first per H40_REWRITE
             (the step-3c "patch the prompt in flight" path). Logs before+after.

Captures land in H40_CAPTURE_DIR (default ../captures), one JSON per /v1/messages
request plus an index.jsonl line. Auth headers are redacted in the saved files.
"""
import json
import os
import sys
import threading
import http.client
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("H40_PORT", "8099"))
MODE = os.environ.get("H40_MODE", "mock")
CAPTURE_DIR = os.environ.get(
    "H40_CAPTURE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "captures"),
)
LABEL = os.environ.get("H40_LABEL", "run")           # tags capture filenames
UPSTREAM_HOST = "api.anthropic.com"
REWRITE = os.environ.get("H40_REWRITE", "")          # which rewrite to apply in rewrite mode
SEQ = {"n": 0}
SEQ_LOCK = threading.Lock()

os.makedirs(CAPTURE_DIR, exist_ok=True)


def _next_seq():
    with SEQ_LOCK:
        SEQ["n"] += 1
        return SEQ["n"]


def _stamp():
    # monotonic-ish counter + epoch; Date.now-free environments aren't a concern here.
    return time.strftime("%H%M%S", time.localtime()) + f"_{_next_seq():03d}"


def redact_headers(headers):
    out = {}
    for k, v in headers.items():
        kl = k.lower()
        if kl in ("authorization", "x-api-key", "anthropic-oauth-token"):
            out[k] = f"<redacted len={len(v)}>"
        else:
            out[k] = v
    return out


def summarize_system(system):
    """Flatten the system field to plain text for easy reading + a structural summary."""
    if system is None:
        return {"present": False}, ""
    if isinstance(system, str):
        return {"present": True, "type": "str", "len": len(system), "blocks": 1}, system
    if isinstance(system, list):
        texts = []
        cache_marks = 0
        for b in system:
            if isinstance(b, dict):
                if b.get("cache_control"):
                    cache_marks += 1
                texts.append(b.get("text", json.dumps(b)))
            else:
                texts.append(str(b))
        joined = "\n\n===[BLOCK BREAK]===\n\n".join(texts)
        return (
            {
                "present": True,
                "type": "list",
                "blocks": len(system),
                "cache_control_blocks": cache_marks,
                "total_len": len(joined),
            },
            joined,
        )
    return {"present": True, "type": type(system).__name__}, str(system)


def apply_rewrite(body):
    """Step-3c interception: mutate the request body in flight. Returns (new_body, note)."""
    if not REWRITE:
        return body, "noop"
    system = body.get("system")
    note = REWRITE
    if REWRITE.startswith("replace:"):
        # replace entire system with the file contents after 'replace:'
        path = REWRITE.split(":", 1)[1]
        with open(path) as f:
            new_text = f.read()
        body["system"] = new_text
        note = f"replaced system with {path} ({len(new_text)} chars)"
    elif REWRITE.startswith("strip_first_block"):
        # drop the first system block (the CC base identity block) entirely
        if isinstance(system, list) and len(system) > 1:
            dropped = system[0]
            body["system"] = system[1:]
            dlen = len(dropped.get("text", "")) if isinstance(dropped, dict) else 0
            note = f"stripped first system block ({dlen} chars)"
    elif REWRITE.startswith("swap_framing:"):
        # keep billing(block0)+identity(block1); replace the big framing block (the
        # largest text block) with the role brief. Surgical 3c: strip CC's SWE
        # framing in flight, inject role, on a flag-less vanilla CC.
        path = REWRITE.split(":", 1)[1]
        with open(path) as f:
            role = f.read()
        if isinstance(system, list) and system:
            big = max(range(len(system)),
                      key=lambda i: len(system[i].get("text", "")) if isinstance(system[i], dict) else 0)
            old_len = len(system[big].get("text", ""))
            system[big] = {"type": "text", "text": role,
                           "cache_control": {"type": "ephemeral", "ttl": "1h"}}
            body["system"] = system
            note = f"swapped framing block #{big} ({old_len}->{len(role)} chars) with {path}"
    elif REWRITE.startswith("prepend:"):
        path = REWRITE.split(":", 1)[1]
        with open(path) as f:
            inject = f.read()
        if isinstance(system, list):
            body["system"] = [{"type": "text", "text": inject}] + system
        elif isinstance(system, str):
            body["system"] = inject + "\n\n" + system
        note = f"prepended {path}"
    return body, note


def capture(path, headers, raw_body, phase, extra=None):
    stamp = _stamp()
    rec = {"stamp": stamp, "label": LABEL, "phase": phase, "path": path,
           "headers": redact_headers(headers)}
    parsed = None
    try:
        parsed = json.loads(raw_body) if raw_body else None
    except Exception as e:
        rec["body_parse_error"] = str(e)
    if isinstance(parsed, dict):
        sys_summary, sys_text = summarize_system(parsed.get("system"))
        rec["model"] = parsed.get("model")
        rec["stream"] = parsed.get("stream")
        rec["system_summary"] = sys_summary
        rec["n_messages"] = len(parsed.get("messages", []))
        rec["n_tools"] = len(parsed.get("tools", []))
        rec["tool_names"] = [t.get("name") for t in parsed.get("tools", []) if isinstance(t, dict)]
        rec["max_tokens"] = parsed.get("max_tokens")
        rec["betas"] = headers.get("anthropic-beta") or headers.get("Anthropic-Beta")
        # write the full system prompt to a sidecar .txt for direct reading
        if sys_text:
            sys_file = os.path.join(CAPTURE_DIR, f"{LABEL}_{stamp}_{phase}_SYSTEM.txt")
            with open(sys_file, "w") as f:
                f.write(sys_text)
            rec["system_text_file"] = os.path.basename(sys_file)
        # full request body for forensic detail
        body_file = os.path.join(CAPTURE_DIR, f"{LABEL}_{stamp}_{phase}_BODY.json")
        with open(body_file, "w") as f:
            json.dump(parsed, f, indent=2)
        rec["body_file"] = os.path.basename(body_file)
    if extra:
        rec.update(extra)
    with open(os.path.join(CAPTURE_DIR, "index.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")
    return parsed, rec


MOCK_SSE_EVENTS = None


def build_mock_sse(text="[H40-MOCK] request captured by oracle proxy."):
    msg_start = {"type": "message_start", "message": {"id": "msg_h40mock", "type": "message",
                 "role": "assistant", "model": "claude-opus-4-8", "content": [],
                 "stop_reason": None, "stop_sequence": None,
                 "usage": {"input_tokens": 10, "output_tokens": 1}}}
    events = [
        ("message_start", msg_start),
        ("content_block_start", {"type": "content_block_start", "index": 0,
                                 "content_block": {"type": "text", "text": ""}}),
        ("ping", {"type": "ping"}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                 "delta": {"type": "text_delta", "text": text}}),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ("message_delta", {"type": "message_delta",
                           "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                           "usage": {"output_tokens": 8}}),
        ("message_stop", {"type": "message_stop"}),
    ]
    out = []
    for ev, data in events:
        out.append(f"event: {ev}\ndata: {json.dumps(data)}\n\n")
    return "".join(out).encode()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[proxy] " + (fmt % args) + "\n")

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(length) if length else b""

    def _is_messages(self):
        return self.path.startswith("/v1/messages") and "count_tokens" not in self.path

    def do_POST(self):
        body = self._read_body()
        phase = "messages" if self._is_messages() else "other"
        parsed, rec = capture(self.path, self.headers, body, phase)

        if self._is_messages() and self.path.endswith("count_tokens"):
            return self._json(200, {"input_tokens": 100})

        if MODE in ("forward", "rewrite") and self._is_messages():
            send_body = body
            if MODE == "rewrite" and isinstance(parsed, dict):
                new_parsed, note = apply_rewrite(parsed)
                send_body = json.dumps(new_parsed).encode()
                capture(self.path, self.headers, send_body, "rewritten",
                        extra={"rewrite_note": note})
            return self._forward(body=send_body)

        if MODE in ("forward", "rewrite"):
            # non-messages housekeeping calls: forward verbatim so CC stays happy
            return self._forward(body=body)

        # MOCK mode
        if self._is_messages():
            stream = isinstance(parsed, dict) and parsed.get("stream")
            if stream:
                return self._sse(build_mock_sse())
            return self._json(200, {"id": "msg_h40mock", "type": "message", "role": "assistant",
                                    "model": "claude-opus-4-8",
                                    "content": [{"type": "text", "text": "[H40-MOCK] captured."}],
                                    "stop_reason": "end_turn", "stop_sequence": None,
                                    "usage": {"input_tokens": 10, "output_tokens": 8}})
        if self.path.endswith("count_tokens"):
            return self._json(200, {"input_tokens": 100})
        # unknown POST housekeeping -> benign empty success
        return self._json(200, {})

    def do_GET(self):
        capture(self.path, self.headers, b"", "get")
        if MODE in ("forward", "rewrite"):
            return self._forward(method="GET", body=b"")
        # mock benign responses for startup housekeeping
        if "oauth/profile" in self.path:
            return self._json(200, {"account": {"email": "h40-mock@local",
                                    "uuid": "00000000-0000-0000-0000-000000000000"},
                                    "organization": {"uuid": "00000000-0000-0000-0000-000000000001"}})
        return self._json(200, {})

    # --- response helpers ---
    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _sse(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _forward(self, method=None, body=b""):
        method = method or self.command
        conn = http.client.HTTPSConnection(UPSTREAM_HOST, timeout=120)
        fwd_headers = {}
        for k, v in self.headers.items():
            if k.lower() in ("host", "content-length", "connection", "accept-encoding"):
                continue
            fwd_headers[k] = v
        fwd_headers["Host"] = UPSTREAM_HOST
        # Auth-shim: in --bare mode CC sends only x-api-key (OAuth/keychain disabled).
        # If H40_OAUTH_INJECT points at an OAuth token file, swap to Bearer auth so a
        # subscription token still works through the proxy. (Lets us behaviorally test
        # bare configs without a pay-per-token API key.)
        inj = os.environ.get("H40_OAUTH_INJECT", "")
        if inj and os.path.exists(inj):
            tok = open(inj).read().strip()
            for hk in [k for k in fwd_headers if k.lower() in ("x-api-key", "authorization")]:
                del fwd_headers[hk]
            fwd_headers["Authorization"] = f"Bearer {tok}"
            fwd_headers["anthropic-beta"] = fwd_headers.get("anthropic-beta", "oauth-2025-04-20")
        if body:
            fwd_headers["Content-Length"] = str(len(body))
        try:
            conn.request(method, self.path, body=body, headers=fwd_headers)
            resp = conn.getresponse()
        except Exception as e:
            return self._json(502, {"error": f"proxy forward failed: {e}"})
        self.send_response(resp.status)
        hop = ("transfer-encoding", "connection", "content-encoding", "content-length")
        body_bytes = resp.read()
        for k, v in resp.getheaders():
            if k.lower() in hop:
                continue
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)
        conn.close()


def main():
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    sys.stderr.write(f"[proxy] H40 oracle on http://127.0.0.1:{PORT}  mode={MODE} "
                     f"label={LABEL} rewrite={REWRITE!r} capture_dir={CAPTURE_DIR}\n")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
