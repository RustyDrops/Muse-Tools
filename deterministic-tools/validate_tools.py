"""Validate tools: json-schema validator, check-url, health, estimate-cost."""

import json
import re
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

MAX_ERRORS = 10


# ---------- minimal JSON-schema validator ----------

def _type_ok(value, want):
    if want == "string":
        return isinstance(value, str)
    if want == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if want == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if want == "boolean":
        return isinstance(value, bool)
    if want == "object":
        return isinstance(value, dict)
    if want == "array":
        return isinstance(value, list)
    if want == "null":
        return value is None
    return True  # unknown type name: do not invent a failure


def _check(value, schema, path, errors):
    if not isinstance(schema, dict):
        return
    want = schema.get("type")
    if want is not None and not _type_ok(value, want):
        errors.append({"path": path or "$",
                       "error": f"expected type {want}"})
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append({"path": path or "$", "error": "not in enum"})
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append({"path": path or "$", "error": "too short"})
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append({"path": path or "$", "error": "too long"})
        if "pattern" in schema:
            try:
                if not re.search(schema["pattern"], value):
                    errors.append({"path": path or "$",
                                   "error": "pattern mismatch"})
            except re.error as exc:
                errors.append({"path": path or "$",
                               "error": f"bad pattern: {exc}"})
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append({"path": path or "$", "error": "below minimum"})
        if "maximum" in schema and value > schema["maximum"]:
            errors.append({"path": path or "$", "error": "above maximum"})
    if isinstance(value, dict):
        for req in schema.get("required", []) or []:
            if req not in value:
                errors.append({"path": (path or "$") + "." + str(req),
                               "error": "required property missing"})
        props = schema.get("properties", {}) or {}
        for key, subschema in props.items():
            if key in value and len(errors) < MAX_ERRORS:
                _check(value[key], subschema,
                       (path or "$") + "." + str(key), errors)
    if isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(value):
                if len(errors) >= MAX_ERRORS:
                    break
                _check(item, items, f"{path or '$'}[{i}]", errors)


def validate(jsonfile, schemafile):
    """Minimal stdlib JSON-schema validation. First 10 errors."""
    for label, f in (("json", jsonfile), ("schema", schemafile)):
        if not Path(f).is_file():
            return 2, {"error": f"{label} file not found: {f}"}
    try:
        data = json.loads(Path(jsonfile).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return 2, {"error": f"bad json file: {exc}"}
    try:
        schema = json.loads(Path(schemafile).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return 2, {"error": f"bad schema file: {exc}"}
    errors = []
    _check(data, schema, "$", errors)
    errors = errors[:MAX_ERRORS]
    if errors:
        return 1, {"json": str(jsonfile), "schema": str(schemafile),
                   "pass": False, "errors": errors, "count": len(errors)}
    return 0, {"json": str(jsonfile), "schema": str(schemafile),
               "pass": True, "errors": [], "count": 0}


# ---------- check-url ----------

class _RedirectCap(urllib.request.HTTPRedirectHandler):
    """HTTPRedirectHandler allowing at most 3 redirects."""

    def __init__(self):
        super().__init__()
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        if self.count > 3:
            raise urllib.error.HTTPError(
                newurl, 310, "too many redirects (>3)", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def check_url(url, timeout=3):
    """HTTP HEAD, 3s timeout, max 3 redirects, no auth, no body download."""
    if not isinstance(url, str) or not url.startswith(("http://",
                                                       "https://")):
        return 2, {"url": str(url),
                   "error": "only http:// and https:// URLs are allowed"}
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": "toolbox-check/1.0"})
    opener = urllib.request.build_opener(_RedirectCap())
    t0 = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as resp:
            status = resp.status
            final = resp.geturl()
    except urllib.error.HTTPError as exc:
        # HTTP error responses still count as a reached server.
        elapsed = int((time.monotonic() - t0) * 1000)
        return 0, {"url": url, "status": exc.code,
                   "final_url": getattr(exc, "url", url) or url,
                   "elapsed_ms": elapsed, "error": None}
    except Exception as exc:  # timeout, DNS, refused, redirect cap
        elapsed = int((time.monotonic() - t0) * 1000)
        return 2, {"url": url, "status": None, "final_url": None,
                   "elapsed_ms": elapsed,
                   "error": f"{type(exc).__name__}: {exc}"[:300]}
    elapsed = int((time.monotonic() - t0) * 1000)
    return 0, {"url": url, "status": status, "final_url": final,
               "elapsed_ms": elapsed, "error": None}


# ---------- health ----------

def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def health():
    """Best-effort host health. Never exit 2 for a missing field."""
    out = {"mem_kb": None, "loadavg": None, "disk": {}, "cgroup_max": None}
    mem = _read_text("/proc/meminfo")
    if mem:
        info = {}
        for line in mem.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].endswith(":"):
                try:
                    info[parts[0][:-1]] = int(parts[1])
                except ValueError:
                    pass
        out["mem_kb"] = {
            "total": info.get("MemTotal"),
            "available": info.get("MemAvailable"),
            "free": info.get("MemFree")}
    lavg = _read_text("/proc/loadavg")
    if lavg:
        out["loadavg"] = lavg.split()[:3]
    for label, d in (("home", Path.home()),
                     ("workspace", Path.home() / "workspace")):
        try:
            u = shutil.disk_usage(d)
            out["disk"][label] = {"total": u.total, "used": u.used,
                                  "free": u.free}
        except OSError:
            out["disk"][label] = None
    for cand in ("/sys/fs/cgroup/memory.max",
                 "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        txt = _read_text(cand)
        if txt:
            out["cgroup_max"] = txt.strip()[:64]
            break
    return 0, out


# ---------- estimate-cost ----------

def _rates_from(obj):
    """Map a rates JSON object to (input, output) USD per token.

    Accepted shapes (per-token, per-1k, or per-1m keys). Returns
    (in_rate, out_rate) per token, or (None, None) if unrecognized.
    """
    if not isinstance(obj, dict):
        return None, None
    flat = obj
    # allow {"rates": {...}} or {"pricing": {...}} wrappers
    for key in ("rates", "pricing", "prices"):
        if isinstance(obj.get(key), dict):
            flat = obj[key]
            break
    pairs = [
        ("input_usd_per_token", "output_usd_per_token", 1),
        ("input_per_token", "output_per_token", 1),
        ("input", "output", 1),
        ("input_per_1k", "output_per_1k", 1000),
        ("input_per_1m", "output_per_1m", 1000000),
    ]
    for ik, ok, div in pairs:
        if ik in flat and ok in flat:
            try:
                return float(flat[ik]) / div, float(flat[ok]) / div
            except (TypeError, ValueError):
                return None, None
    return None, None


def estimate_cost(path, output_tokens=0, rates=None):
    """Token estimate (chars/4). cost_usd only with a --rates file."""
    p = Path(path)
    if not p.is_file():
        return 2, {"error": f"file not found: {path}"}
    try:
        output_tokens = int(output_tokens)
    except (TypeError, ValueError):
        return 2, {"error": "output-tokens must be an integer"}
    try:
        raw = p.read_bytes()
    except OSError as exc:
        return 2, {"error": f"cannot read: {exc}"}
    try:
        chars = len(raw.decode("utf-8"))
    except UnicodeDecodeError:
        chars = len(raw)
    in_tokens = round(chars / 4)
    payload = {"path": str(path), "chars": chars,
               "input_tokens": in_tokens, "output_tokens": output_tokens,
               "total_tokens": in_tokens + output_tokens,
               "cost_usd": None, "note": None}
    if rates is None:
        payload["note"] = "no rates supplied; cost_usd is null (no rates invented)"
        return 0, payload
    if not Path(rates).is_file():
        return 2, {"error": f"rates file not found: {rates}"}
    try:
        robj = json.loads(Path(rates).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return 2, {"error": f"bad rates file: {exc}"}
    in_r, out_r = _rates_from(robj)
    if in_r is None:
        payload["note"] = ("unrecognized rates shape; cost_usd is null "
                           "(no rates invented)")
        return 0, payload
    payload["cost_usd"] = round(in_tokens * in_r + output_tokens * out_r, 6)
    payload["note"] = "cost from supplied --rates file"
    return 0, payload
