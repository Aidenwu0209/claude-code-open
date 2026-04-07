#!/usr/bin/env python3
"""
Anthropic-to-OpenAI proxy for ZhiPu GLM-5
Full SSE streaming support with tool_use/tool_result conversion
"""

import json
import os
import sys
import time
import uuid
import urllib.request
import urllib.error
from pathlib import Path
from flask import Flask, request, Response

# Load .env file from same directory as this script
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for _line in f:
            _line = _line.strip()
            if _line and '=' in _line and not _line.startswith('#'):
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

app = Flask(__name__)

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
DEFAULT_MODEL = os.environ.get("MODEL", "glm-5")
DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")


def log(*args):
    if DEBUG:
        print(f"[proxy] {' '.join(str(a) for a in args)}", file=sys.stderr)


def gen_id(prefix="msg"):
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def convert_anthropic_to_openai_messages(body):
    """Convert Anthropic messages format to OpenAI format"""
    messages = []
    
    system = body.get("system", "")
    if isinstance(system, list):
        system = "\n".join(b.get("text", "") for b in system if b.get("type") == "text")
    if system:
        messages.append({"role": "system", "content": system})

    for msg in body.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, str):
            if content:
                messages.append({"role": role, "content": content})
            continue

        if not isinstance(content, list):
            messages.append({"role": role, "content": str(content) if content else ""})
            continue

        text_parts = []
        tool_calls_to_add = []
        pending_tool_results = []

        for block in content:
            if not isinstance(block, dict):
                continue
                
            btype = block.get("type", "")

            if btype == "text":
                text = block.get("text", "")
                if text:
                    text_parts.append(text)

            elif btype == "image":
                source = block.get("source", {})
                if source.get("type") == "base64":
                    img_data = source.get("data", "")
                    media_type = source.get("media_type", "image/png")
                    text_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{img_data}"}
                    })

            elif btype == "tool_use":
                tool_calls_to_add.append({
                    "id": block.get("id", gen_id("call")),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {}), ensure_ascii=False)
                    }
                })

            elif btype == "tool_result":
                tool_content = block.get("content", "")
                if isinstance(tool_content, list):
                    tool_content = "\n".join(
                        b.get("text", "") if isinstance(b, dict) and b.get("type") == "text" else str(b)
                        for b in tool_content
                    )
                pending_tool_results.append({
                    "role": "tool",
                    "tool_call_id": block.get("tool_use_id", ""),
                    "content": str(tool_content) if tool_content else ""
                })

        if role == "assistant":
            if tool_calls_to_add:
                assistant_msg = {
                    "role": "assistant",
                    "content": " ".join(text_parts) if text_parts else None,
                    "tool_calls": tool_calls_to_add
                }
                messages.append(assistant_msg)
            elif text_parts:
                content_str = " ".join(text_parts)
                if content_str:
                    messages.append({"role": role, "content": content_str})
        else:
            if pending_tool_results:
                if text_parts:
                    content_str = " ".join(p for p in text_parts if isinstance(p, str))
                    if content_str:
                        messages.append({"role": role, "content": content_str})
                for tr in pending_tool_results:
                    messages.append(tr)
            elif text_parts:
                content_str = " ".join(p for p in text_parts if isinstance(p, str))
                if content_str:
                    messages.append({"role": role, "content": content_str})
                for p in text_parts:
                    if isinstance(p, dict):
                        messages.append({"role": role, "content": [p]})

    return messages


def convert_anthropic_tools_to_openai(tools):
    """Convert Anthropic tools format to OpenAI format"""
    if not tools:
        return None

    openai_tools = []
    for tool in tools:
        tool_type = tool.get("type", "")
        
        if tool_type == "computer_20241022":
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": "computer_use",
                    "description": tool.get("name", "computer"),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "coordinate": {"type": "array", "items": {"type": "integer"}},
                            "text": {"type": "string"}
                        }
                    }
                }
            })
            continue
        
        if tool_type in ("custom", "function", "") or "function" in tool_type:
            func_def = {
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                }
            }
            input_schema = tool.get("input_schema", {})
            if input_schema:
                params = dict(input_schema)
                if "$schema" in params:
                    del params["$schema"]
                func_def["function"]["parameters"] = params
            openai_tools.append(func_def)

    return openai_tools if openai_tools else None


def sse_event(event_type, data):
    """Format SSE event"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def anthropic_message_start(msg_id, model, input_tokens=0):
    return {
        "type": "message_start",
        "message": {
            "id": msg_id,
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": model,
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": input_tokens, "output_tokens": 0}
        }
    }


def anthropic_content_block_start(index, block_type, **kwargs):
    content_block = {"type": block_type}
    if block_type == "text":
        content_block["text"] = kwargs.get("text", "")
    elif block_type == "tool_use":
        content_block["id"] = kwargs.get("id", gen_id("toolu"))
        content_block["name"] = kwargs.get("name", "")
        content_block["input"] = {}
    return {"type": "content_block_start", "index": index, "content_block": content_block}


def anthropic_content_block_delta(index, delta_type, **kwargs):
    delta = {"type": delta_type}
    if delta_type == "text_delta":
        delta["text"] = kwargs.get("text", "")
    elif delta_type == "input_json_delta":
        delta["partial_json"] = kwargs.get("partial_json", "")
    return {"type": "content_block_delta", "index": index, "delta": delta}


def anthropic_content_block_stop(index):
    return {"type": "content_block_stop", "index": index}


def anthropic_message_delta(stop_reason, output_tokens=0):
    return {
        "type": "message_delta",
        "delta": {"stop_reason": stop_reason, "stop_sequence": None},
        "usage": {"output_tokens": output_tokens}
    }


def anthropic_message_stop():
    return {"type": "message_stop"}


def anthropic_error(error_type, message):
    return {
        "type": "error",
        "error": {"type": error_type, "message": message}
    }


def call_zhipu_api(payload):
    """Call ZhiPu API with payload"""
    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ZHIPU_API_KEY}"
    }
    
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    
    log(f"POST {url}")
    return urllib.request.urlopen(req, timeout=300)


def parse_sse_lines(data):
    """Parse SSE data into lines, yields (event_type, json_data) or None"""
    lines = data.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("data: "):
            data_str = line[6:]
            if data_str == "[DONE]":
                yield {"done": True}
            else:
                try:
                    yield json.loads(data_str)
                except json.JSONDecodeError:
                    pass


def stream_anthropic_response(openai_stream, model, input_tokens):
    """Convert OpenAI streaming response to Anthropic SSE format"""
    msg_id = gen_id("msg")
    yield sse_event("message_start", anthropic_message_start(msg_id, model, input_tokens))

    block_index = -1
    block_type = None
    tool_states = {}
    output_tokens = 0
    stop_reason = "end_turn"
    has_content = False
    buffer = b""

    try:
        for chunk in openai_stream:
            buffer += chunk
            
            while b"\n" in buffer:
                line_bytes, buffer = buffer.split(b"\n", 1)
                line = line_bytes.decode("utf-8", errors="replace").strip()
                
                if not line or not line.startswith("data: "):
                    continue
                
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                
                try:
                    parsed = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = parsed.get("choices", [])
                if not choices:
                    usage = parsed.get("usage", {})
                    if usage:
                        output_tokens = max(output_tokens, usage.get("completion_tokens", 0))
                    continue

                choice = choices[0]
                delta = choice.get("delta", {})
                finish_reason = choice.get("finish_reason")

                if finish_reason:
                    if finish_reason == "tool_calls":
                        stop_reason = "tool_use"
                    elif finish_reason == "length":
                        stop_reason = "max_tokens"
                    elif finish_reason != "stop":
                        stop_reason = finish_reason

                content = delta.get("content")
                tool_calls = delta.get("tool_calls", [])

                if content:
                    has_content = True
                    if block_type != "text":
                        if block_index >= 0:
                            yield sse_event("content_block_stop", anthropic_content_block_stop(block_index))
                        block_index += 1
                        block_type = "text"
                        yield sse_event("content_block_start", anthropic_content_block_start(block_index, "text"))

                    yield sse_event("content_block_delta", anthropic_content_block_delta(block_index, "text_delta", text=content))
                    output_tokens += 1

                for tc in tool_calls:
                    has_content = True
                    tc_id = tc.get("id")
                    tc_idx = tc.get("index", 0)
                    tc_func = tc.get("function", {})
                    tc_name = tc_func.get("name", "")
                    tc_args = tc_func.get("arguments", "")

                    if tc_id:
                        tool_states[tc_idx] = {"id": tc_id, "name": tc_name, "args": ""}
                        new_block_idx = block_index + 1 + tc_idx - len([k for k in tool_states if k < tc_idx])
                        
                        if block_index >= 0 and block_type != "tool_use":
                            yield sse_event("content_block_stop", anthropic_content_block_stop(block_index))
                        
                        block_index = new_block_idx
                        block_type = "tool_use"
                        
                        yield sse_event("content_block_start", anthropic_content_block_start(
                            block_index, "tool_use", id=tc_id, name=tc_name
                        ))

                    if tc_args and tc_idx in tool_states:
                        tool_states[tc_idx]["args"] += tc_args
                        actual_idx = block_index - len(tool_states) + 1 + tc_idx
                        yield sse_event("content_block_delta", anthropic_content_block_delta(
                            actual_idx, "input_json_delta", partial_json=tc_args
                        ))
                        output_tokens += 1

                usage = parsed.get("usage", {})
                if usage:
                    output_tokens = max(output_tokens, usage.get("completion_tokens", 0))

        if block_index >= 0:
            yield sse_event("content_block_stop", anthropic_content_block_stop(block_index))

        if not has_content:
            yield sse_event("content_block_start", anthropic_content_block_start(0, "text"))
            yield sse_event("content_block_delta", anthropic_content_block_delta(0, "text_delta", text=""))
            yield sse_event("content_block_stop", anthropic_content_block_stop(0))

        yield sse_event("message_delta", anthropic_message_delta(stop_reason, output_tokens))
        yield sse_event("message_stop", anthropic_message_stop())

    except Exception as e:
        log(f"Streaming error: {e}")
        yield sse_event("error", anthropic_error("api_error", str(e)))


def convert_non_streaming_response(oai_response, model):
    """Convert OpenAI non-streaming response to Anthropic format"""
    if "error" in oai_response:
        return anthropic_error("api_error", str(oai_response["error"]))

    choice = oai_response.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage = oai_response.get("usage", {})

    content = []

    text = message.get("content")
    if text:
        content.append({"type": "text", "text": text})

    for tc in message.get("tool_calls", []):
        tc_func = tc.get("function", {})
        args_str = tc_func.get("arguments", "{}")
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}

        content.append({
            "type": "tool_use",
            "id": tc.get("id", gen_id("toolu")),
            "name": tc_func.get("name", ""),
            "input": args
        })

    if not content:
        content.append({"type": "text", "text": ""})

    stop_reason = "end_turn"
    finish_reason = choice.get("finish_reason")
    if finish_reason == "tool_calls":
        stop_reason = "tool_use"
    elif finish_reason == "length":
        stop_reason = "max_tokens"
    elif finish_reason and finish_reason != "stop":
        stop_reason = finish_reason

    return {
        "id": gen_id("msg"),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0)
        }
    }


def estimate_tokens(messages):
    """Rough token estimation"""
    return sum(len(json.dumps(m, ensure_ascii=False)) // 4 for m in messages)


@app.route("/api/hello", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "proxy": "anthropic-to-openai", "model": DEFAULT_MODEL}


@app.route("/v1/oauth/hello", methods=["GET"])
def oauth_hello():
    return {"status": "ok"}


@app.route("/v1/messages", methods=["POST", "OPTIONS"])
@app.route("/messages", methods=["POST", "OPTIONS"])
def handle_messages():
    if request.method == "OPTIONS":
        resp = Response()
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "*"
        return resp

    anthropic_version = request.headers.get("anthropic-version", "")
    log(f"anthropic-version: {anthropic_version}")

    try:
        body = request.get_json(force=True)
    except Exception:
        return Response(json.dumps(anthropic_error("invalid_request_error", "Invalid JSON")), 
                       mimetype="application/json"), 400

    model = body.get("model", DEFAULT_MODEL)
    if model.startswith("claude"):
        model = DEFAULT_MODEL

    messages = convert_anthropic_to_openai_messages(body)
    tools = convert_anthropic_tools_to_openai(body.get("tools", []))
    max_tokens = body.get("max_tokens", 4096)
    stream = body.get("stream", False)
    temperature = body.get("temperature")

    input_tokens = estimate_tokens(messages)

    log(f"-> model={model}, msgs={len(messages)}, stream={stream}, tools={len(tools) if tools else 0}")

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": stream
    }
    if tools:
        payload["tools"] = tools
    if temperature is not None:
        payload["temperature"] = temperature

    try:
        if stream:
            openai_stream = call_zhipu_api(payload)

            def generate():
                yield from stream_anthropic_response(openai_stream, model, input_tokens)

            resp = Response(generate(), mimetype="text/event-stream")
            resp.headers["Cache-Control"] = "no-cache"
            resp.headers["Connection"] = "keep-alive"
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["X-Accel-Buffering"] = "no"
            return resp
        else:
            with call_zhipu_api(payload) as resp:
                oai_response = json.loads(resp.read().decode("utf-8"))
            
            result = convert_non_streaming_response(oai_response, model)
            log(f"<- stop_reason={result.get('stop_reason')}, content_blocks={len(result.get('content', []))}")
            
            resp = Response(json.dumps(result, ensure_ascii=False), mimetype="application/json")
            resp.headers["Access-Control-Allow-Origin"] = "*"
            return resp

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        log(f"HTTP Error {e.code}: {error_body}")
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get("error", {}).get("message", error_body)
        except:
            error_msg = error_body or f"HTTP {e.code}"
        return Response(json.dumps(anthropic_error("api_error", error_msg)), 
                       mimetype="application/json"), e.code
    except Exception as e:
        log(f"Error: {e}")
        return Response(json.dumps(anthropic_error("api_error", str(e))), 
                       mimetype="application/json"), 500


@app.route("/<path:path>", methods=["GET", "POST", "OPTIONS"])
@app.route("/", methods=["GET", "POST", "OPTIONS"])
def catch_all(path=""):
    if request.method == "OPTIONS":
        resp = Response()
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "*"
        return resp

    if request.method == "GET":
        return {"status": "ok"}

    if "messages" in request.url or "messages" in path:
        return handle_messages()

    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4000))
    print(f"Anthropic->OpenAI proxy on http://127.0.0.1:{port}")
    print(f"  -> {OPENAI_BASE_URL} ({DEFAULT_MODEL})")
    print(f"  ZHIPU_API_KEY: {'*' * 8 if ZHIPU_API_KEY else 'NOT SET'}")
    app.run(host="127.0.0.1", port=port, threaded=True)
