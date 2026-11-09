#!/usr/bin/env python3
"""AI usage / cost tracker for OpenAI GPT-6 Luna (Flex) and Gemini calls.

No API keys, prompts, or response text are stored here - only token counts,
model, tier, connector, a short task label, and the calculated cost.

Usage:
  python3 tracker.py log --provider openai --model gpt-6-luna --tier flex \
      --input 25000 --output 13000 --cached 0 --task "sermon draft"
  python3 tracker.py log --provider gemini --model gemini-2.5-flash \
      --input 464780 --output 2000 --task "video analysis"
  python3 tracker.py log --provider gemini --model gemini-omni-1.1-flash \
      --tier paid --connector paid --input 0 --output 0 \
      --video-seconds 10.026667 --task "celebration-video" --estimate
  python3 tracker.py log --provider gemini --model gemini-nano-banana-2.1 \
      --tier paid --connector paid --input 0 --output 0 \
      --image-size 2K --task "celebration-image" --estimate
  python3 tracker.py summary

Pricing (per 1M tokens, USD, verified against published rates 2026-10-26;
re-check against the OpenAI invoice after the first real call):
  Rates are per model AND tier. Flex/Batch is half the standard rate.
  Unknown models fall back to Luna Flex rates (the original behaviour).
  GPT-6 Luna: standard input $0.10, cached $0.01, output $0.50;
      Flex input $0.05, cached $0.005, output $0.25
  GPT-6.1 Terra: standard input $1.00, cached $0.05, output $5.00;
      Flex input $0.50, cached $0.025, output $2.50
  GPT-6.1 Sol: standard input $2.00, cached $0.10, output $10.00;
      Flex input $1.00, cached $0.05, output $5.00
  GPT-6 Astra: standard input $10.00, cached $1.00, output $50.00;
      Flex input $5.00, cached $0.50, output $25.00
  Long prompts (> 272,000 input tokens): whole request at 2x input/cached
      rates and 1.5x output rates, for every model above.
  Gemini free tier (--tier free): actual cost $0. Tokens are still logged.
  Gemini paid tier (--tier paid, rates verified against Google's official
      pricing page 2026-11-03):
      Text models, input/output per 1M: gemini-3.5-flash-lite $0.30/$2.50,
      gemini-3.8-flash $0.75/$3.75 (through 2026-12-31).
      Image, gemini-nano-banana-2.1: input $1.50 per 1M, image output
      $30.00 per 1M, equivalent to $0.0336 per 1K, $0.0504 per 2K,
      $0.113 per 4K image.
      Video, gemini-omni-1.1-flash: input $1.50 per 1M, video output
      $17.50 per 1M, billed at 5,792 tokens per second of 720p video,
      equivalent to about $0.10 per second.
      Media calls that do not return token usage are logged with
      --estimate, priced from duration/resolution at the rates above,
      excluding prompt/input-image tokens (a few tenths of a cent).
  GPT-Image-2.5 (Flare/Sunburst, token-billed): text input $5, cached text
      $1.25, image input $8, cached image $2, image output $30 per 1M tokens.
      For an image call, pass --input as text input tokens, --image-input
      as image input tokens, and --image-output as image output tokens.
Budget: OpenAI starting credit $5.00 (user-stated 2026-10-26).
Gemini paid has no fixed budget in this tracker; summary reports its
running total so the user can set a cap.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "usage.jsonl"
OPENAI_BUDGET = 5.00
LONG_CONTEXT = 272_000


def openai_cost(input_tokens, output_tokens, cached_tokens, model="", tier=""):
    # (input, cached, output) per 1M, standard rates; Flex halves them.
    rates = {
        "gpt-6-luna": (0.10, 0.01, 0.50),
        "gpt-6.1-terra": (1.00, 0.05, 5.00),
        "gpt-6.1-sol": (2.00, 0.10, 10.00),
        "gpt-6-astra": (10.00, 1.00, 50.00),
    }
    inp, cached, out = rates.get(model, (0.10, 0.01, 0.50))
    if tier in ("flex", "batch"):
        inp, cached, out = inp / 2, cached / 2, out / 2
    elif model not in rates:
        # Unknown model, old behaviour: Luna Flex rates.
        inp, cached, out = 0.05, 0.005, 0.25
    if input_tokens > LONG_CONTEXT:
        inp, cached, out = inp * 2, cached * 2, out * 1.5
    non_cached = max(input_tokens - cached_tokens, 0)
    return (non_cached * inp + cached_tokens * cached
            + output_tokens * out) / 1_000_000


def load():
    if not LOG.exists():
        return []
    rows = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def image_cost(text_tokens, image_input_tokens, image_output_tokens, cached_text=0, cached_image=0, tier=""):
    mult = 0.5 if tier == "batch" else 1.0
    return round(((text_tokens - cached_text) * 5 * mult + cached_text * 1.25 * mult
                  + (image_input_tokens - cached_image) * 8 * mult + cached_image * 2 * mult
                  + image_output_tokens * 30 * mult) / 1_000_000, 6)


GEMINI_TEXT_RATES = {
    # Standard rates; Flex halves them below (tracker 2026-11-04 model-test fix).
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-4-argon": (2.00, 10.00),  # intro to 2026-11-30, then 4.00/20.00
}
GEMINI_IMAGE_PER_IMAGE = {
    ("gemini-nano-banana-2.1", "1K"): 0.0336,
    ("gemini-nano-banana-2.1", "2K"): 0.0504,
    ("gemini-nano-banana-2.1", "4K"): 0.113,
}
GEMINI_VIDEO_TOKENS_PER_SEC = 5792
GEMINI_VIDEO_OUTPUT_RATE = 17.50


def gemini_cost(args):
    if args.tier in ("", "free"):
        return 0.0
    cost = 0.0
    if args.video_seconds:
        cost += args.video_seconds * GEMINI_VIDEO_TOKENS_PER_SEC * GEMINI_VIDEO_OUTPUT_RATE / 1_000_000
    if args.image_size:
        cost += GEMINI_IMAGE_PER_IMAGE.get((args.model, args.image_size), 0.0)
    if args.model in GEMINI_TEXT_RATES:
        inp, out = GEMINI_TEXT_RATES[args.model]
        if args.tier == "flex":
            inp, out = inp / 2, out / 2
        cost += (args.input * inp + args.output * out) / 1_000_000
    elif args.model in ("gemini-nano-banana-2.1", "gemini-omni-1.1-flash"):
        # Media models: input at $1.50 per 1M, plus any token-based output.
        cost += args.input * 1.50 / 1_000_000
        cost += args.output * 17.50 / 1_000_000 if args.model == "gemini-omni-1.1-flash" else 0.0
        cost += args.image_output * 30.00 / 1_000_000
    else:
        # Unknown Gemini paid model: token-based only, no invented rate.
        cost += 0.0
    return round(cost, 6)


def cmd_log(args):
    if args.provider == "openai" and args.model.startswith("gpt-image"):
        cost = image_cost(args.input, args.image_input, args.image_output, args.cached, tier=args.tier)
    elif args.provider == "openai":
        cost = round(openai_cost(args.input, args.output, args.cached, args.model, args.tier), 6)
    else:  # gemini, free = $0, paid = gemini_cost
        cost = gemini_cost(args)
    rows = load()
    openai_spent = sum(r["cost_usd"] for r in rows if r["provider"] == "openai")
    gemini_paid_spent = sum(r["cost_usd"] for r in rows if r["provider"] == "gemini" and r.get("tier") == "paid")
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "provider": args.provider,
        "model": args.model,
        "tier": args.tier,
        "connector": args.connector,
        "task": args.task,
        "prompt_tokens": args.input,
        "cached_tokens": args.cached,
        "completion_tokens": args.output,
        "image_input_tokens": args.image_input,
        "image_output_tokens": args.image_output,
        "video_seconds": args.video_seconds,
        "image_size": args.image_size,
        "estimate": args.estimate,
        "cost_usd": cost,
        "openai_spent_usd": round(openai_spent + cost, 6) if args.provider == "openai" else round(openai_spent, 6),
        "openai_remaining_usd": round(OPENAI_BUDGET - openai_spent - cost, 6) if args.provider == "openai" else round(OPENAI_BUDGET - openai_spent, 6),
        "gemini_paid_spent_usd": round(gemini_paid_spent + cost, 6) if args.provider == "gemini" and args.tier == "paid" else round(gemini_paid_spent, 6),
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row, indent=2))
    return 0


def cmd_summary(_args):
    rows = load()
    out = {"calls": len(rows), "openai_budget_usd": OPENAI_BUDGET}
    for provider in ("openai", "gemini"):
        sub = [r for r in rows if r["provider"] == provider]
        out[provider] = {
            "calls": len(sub),
            "prompt_tokens": sum(r["prompt_tokens"] for r in sub),
            "completion_tokens": sum(r["completion_tokens"] for r in sub),
            "cost_usd": round(sum(r["cost_usd"] for r in sub), 6),
        }
    gemini_paid = [r for r in rows if r["provider"] == "gemini" and r.get("tier") == "paid"]
    gemini_free = [r for r in rows if r["provider"] == "gemini" and r.get("tier") != "paid"]
    out["gemini_paid"] = {
        "calls": len(gemini_paid),
        "cost_usd": round(sum(r["cost_usd"] for r in gemini_paid), 6),
        "estimated_cost_usd": round(sum(r["cost_usd"] for r in gemini_paid if r.get("estimate")), 6),
    }
    out["gemini_free"] = {
        "calls": len(gemini_free),
        "cost_usd": round(sum(r["cost_usd"] for r in gemini_free), 6),
    }
    out["openai_remaining_usd"] = round(
        OPENAI_BUDGET - out["openai"]["cost_usd"], 6)
    print(json.dumps(out, indent=2))
    return 0


def main(argv):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("log")
    lp.add_argument("--provider", choices=["openai", "gemini"], required=True)
    lp.add_argument("--model", required=True)
    lp.add_argument("--tier", default="")
    lp.add_argument("--connector", default="")
    lp.add_argument("--input", type=int, required=True)
    lp.add_argument("--output", type=int, required=True)
    lp.add_argument("--cached", type=int, default=0)
    lp.add_argument("--image-input", type=int, default=0)
    lp.add_argument("--image-output", type=int, default=0)
    lp.add_argument("--video-seconds", type=float, default=0.0)
    lp.add_argument("--image-size", default="")
    lp.add_argument("--estimate", action="store_true")
    lp.add_argument("--task", default="")
    lp.set_defaults(fn=cmd_log)
    sp = sub.add_parser("summary")
    sp.set_defaults(fn=cmd_summary)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
