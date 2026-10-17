#!/usr/bin/env python3
"""
Model Decision Engine for Agents using Artificial Analysis API.
Filters models by active user subscriptions and ranks them according to task requirements.
Outputs pure JSON (default) or formatted Markdown (--human).
Supports --blind mode for double-blind evaluations free of corporate bias.
Zero external dependencies (pure Python standard library).
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CACHE_TTL_SECONDS = 86400  # 24 hours
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SUBSCRIPTIONS_FILE = SKILL_DIR / "subscriptions.json"
SUBSCRIPTIONS_EXAMPLE = SKILL_DIR / "subscriptions.example.json"
CACHE_FILE = SKILL_DIR / "cache.json"


def find_api_key(explicit_key=None):
    """Locate API key from argument, environment variables, or .env file."""
    if explicit_key:
        return explicit_key

    for env_var in ["ART_ANA", "ARTIFICIAL_ANALYSIS_API_KEY"]:
        if os.environ.get(env_var):
            return os.environ[env_var]

    search_dirs = [
        SKILL_DIR,
        Path.cwd(),
        Path.cwd().parent,
        SKILL_DIR.parent.parent,
        Path.home(),
    ]
    for d in search_dirs:
        env_file = d / ".env"
        if env_file.is_file():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        m = re.match(r"^(?:ART_ANA|ARTIFICIAL_ANALYSIS_API_KEY)=['\"]?([^'\"]+)['\"]?", line)
                        if m:
                            return m.group(1).strip()
            except Exception:
                continue
    return None


def fetch_models_data(api_key, refresh=False):
    """Retrieve model data from cache or Artificial Analysis API."""
    if not refresh and CACHE_FILE.is_file():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_time = cached.get("timestamp", 0)
            if time.time() - cached_time < CACHE_TTL_SECONDS:
                return cached.get("data", [])
        except Exception:
            pass

    if not api_key:
        raise ValueError("Missing API key. Set ART_ANA in .env or pass --api-key. Free key at https://artificialanalysis.ai")

    endpoints = [
        "https://artificialanalysis.ai/api/v2/language/models/free",
        "https://artificialanalysis.ai/api/v2/language/models",
    ]
    data = None
    last_err = None

    for url in endpoints:
        req = urllib.request.Request(
            url,
            headers={
                "x-api-key": api_key,
                "User-Agent": "ModelDecisionSkill/1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_body = json.loads(resp.read().decode("utf-8"))
                data = res_body.get("data", [])
                if data:
                    break
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.reason}"
            continue
        except Exception as e:
            last_err = str(e)
            continue

    if data is None:
        raise RuntimeError(f"Failed to fetch model catalog: {last_err}")

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time(), "data": data}, f)
    except Exception:
        pass

    return data


def load_subscriptions():
    """Load subscriptions configuration with fallback to example file."""
    target_file = SUBSCRIPTIONS_FILE if SUBSCRIPTIONS_FILE.is_file() else SUBSCRIPTIONS_EXAMPLE
    if not target_file.is_file():
        return []
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            content = json.load(f)
            return content.get("subscriptions", [])
    except Exception:
        return []


def filter_models_by_subscriptions(all_models, subscriptions):
    """Filter models from API that belong to the user's active subscriptions, prioritizing latest versions."""
    matched = []
    for m in all_models:
        slug = (m.get("slug") or "").lower()
        name = (m.get("name") or "").lower()

        matched_sub = None
        for sub in subscriptions:
            patterns = sub.get("patterns", [])
            for p in patterns:
                p_lower = p.lower()
                if p_lower in slug or p_lower in name:
                    matched_sub = sub.get("name", "Unknown")
                    break
            if matched_sub:
                break

        if matched_sub:
            matched.append({
                "raw": m,
                "subscription": matched_sub,
                "name": m.get("name", "Unknown"),
                "slug": m.get("slug", ""),
                "creator": (m.get("model_creator") or {}).get("name", "Unknown"),
                "release_date": m.get("release_date") or "",
                "evaluations": m.get("evaluations") or {},
                "performance": m.get("performance") or {},
                "pricing": m.get("pricing") or {},
            })
    return matched


def infer_criterion(task_text):
    """Infer the primary evaluation criterion from the task description."""
    text = task_text.lower()

    frontend_keywords = [
        "vibe", "vibecoding", "vibe coding", "frontend", "ui", "ux", "interface",
        "react", "vue", "tailwind", "css", "html", "landing", "component",
        "web design", "wireframe", "dashboard", "gui"
    ]
    coding_keywords = [
        "code", "coding", "program", "script", "refactor", "bug", "fix",
        "debug", "python", "javascript", "typescript", "sql",
        "api", "endpoint", "test", "unittest", "pytest",
        "backend", "git", "function", "class", "algorithm",
        "human-eval", "livecodebench", "mbpp"
    ]
    agentic_keywords = [
        "agent", "agentic", "workflow", "automate", "automation",
        "multi-step", "tool", "browse", "scrape", "pipeline",
        "terminal", "cli", "shell", "bash", "powershell", "command line",
        "terminal bench", "terminalbench", "swe-bench", "swebench",
        "benchmark", "bench", "tool use", "autonomous"
    ]
    speed_keywords = [
        "fast", "speed", "quick", "realtime", "instant", "latency",
        "short", "streaming", "low latency", "throughput"
    ]
    cost_keywords = [
        "cheap", "cost", "budget", "pricing", "free", "bulk", "batch",
        "economic", "low cost", "efficient"
    ]

    scores = {
        "frontend": sum(1 for w in frontend_keywords if w in text),
        "coding": sum(1 for w in coding_keywords if w in text),
        "agentic": sum(1 for w in agentic_keywords if w in text),
        "speed": sum(1 for w in speed_keywords if w in text),
        "cost": sum(1 for w in cost_keywords if w in text),
    }

    best_cat, best_val = max(scores.items(), key=lambda x: x[1])
    if best_val > 0:
        return best_cat

    return "intelligence"


def rank_models(models, criterion):
    """Rank models according to the selected criterion, using release_date for recency."""
    scored = []
    for item in models:
        evals = item["evaluations"]
        perf = item["performance"]
        pricing = item["pricing"]

        score = 0.0
        details = {}

        if criterion == "frontend":
            coding_idx = evals.get("artificial_analysis_coding_index") or 0.0
            agentic_idx = evals.get("artificial_analysis_agentic_index") or 0.0
            score = (coding_idx * 0.6) + (agentic_idx * 0.4)
            details["vibe_composite_score"] = round(score, 2)
            details["coding_index"] = coding_idx
            details["agentic_index"] = agentic_idx

        elif criterion == "coding":
            score = evals.get("artificial_analysis_coding_index") or 0.0
            details["coding_index"] = score
            details["agentic_index"] = evals.get("artificial_analysis_agentic_index") or 0.0

        elif criterion == "agentic":
            score = evals.get("artificial_analysis_agentic_index") or 0.0
            details["agentic_index"] = score
            details["coding_index"] = evals.get("artificial_analysis_coding_index") or 0.0

        elif criterion == "speed":
            score = perf.get("median_output_tokens_per_second") or 0.0
            details["output_tokens_per_second"] = score
            details["time_to_first_token_sec"] = perf.get("median_time_to_first_token_seconds")

        elif criterion == "cost":
            price_in = pricing.get("price_1m_input_tokens") or 999.0
            price_out = pricing.get("price_1m_output_tokens") or 999.0
            total_price = price_in + price_out
            score = -total_price
            details["price_1m_input_tokens"] = price_in
            details["price_1m_output_tokens"] = price_out

        else:  # intelligence / reasoning / general
            score = evals.get("artificial_analysis_intelligence_index") or 0.0
            details["intelligence_index"] = score
            details["coding_index"] = evals.get("artificial_analysis_coding_index") or 0.0

        scored.append({
            "name": item["name"],
            "slug": item["slug"],
            "subscription": item["subscription"],
            "creator": item["creator"],
            "release_date": item.get("release_date") or "",
            "score": round(score, 2),
            "metric_details": details,
        })

    # Sort primarily by score, secondarily by release_date (fresher models preferred)
    scored.sort(key=lambda x: (x["score"], x["release_date"]), reverse=True)
    return scored


def format_markdown_output(result, blind=False):
    """Format model recommendation into concise Markdown: Top 1 + brief top list of the rest."""
    rec = result["recommended_model"]
    reveal = result.get("reveal", {})
    if blind and reveal:
        winner_info = reveal.get(rec.get("candidate_id"), {})
        name = winner_info.get("name", rec.get("candidate_id"))
        sub = winner_info.get("subscription", "")
    else:
        name = rec.get("name", "Unknown")
        sub = rec.get("subscription", "")

    lines = [
        f"**🏆 #1 Recomendado: {name}** (`{sub}`)",
        f"- **Criterio:** `{result['detected_criterion']}` (Score: **{rec['score']}**)",
    ]
    for k, v in list(rec["metrics"].items())[:2]:
        lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")

    if result.get("alternatives"):
        lines.append("\n**🥈 Top del resto:**")
        for i, alt in enumerate(result["alternatives"][:3], start=2):
            if blind and reveal:
                alt_info = reveal.get(alt.get("candidate_id"), {})
                alt_name = alt_info.get("name", alt.get("candidate_id"))
                alt_sub = alt_info.get("subscription", "")
            else:
                alt_name = alt.get("name", "Unknown")
                alt_sub = alt.get("subscription", "")
            lines.append(f"{i}. {alt_name} (`{alt_sub}`) — Score: **{alt['score']}**")

    return "\n".join(lines)


def run_setup():
    """Interactive onboarding to set up API key and subscription files."""
    print("=== Configuración Inicial de Model Decision Skill ===")
    print("1. Consigue tu API key gratuita en: https://artificialanalysis.ai/api-key-management-redirect")
    entered_key = input("Introduce tu API key de Artificial Analysis: ").strip()

    if entered_key:
        env_dest = Path.cwd() / ".env"
        with open(env_dest, "a", encoding="utf-8") as f:
            f.write(f"\nART_ANA='{entered_key}'\n")
        print(f" Clave guardada en {env_dest}")

    if not SUBSCRIPTIONS_FILE.is_file() and SUBSCRIPTIONS_EXAMPLE.is_file():
        import shutil
        shutil.copyfile(SUBSCRIPTIONS_EXAMPLE, SUBSCRIPTIONS_FILE)
        print(f" Creado {SUBSCRIPTIONS_FILE} desde la plantilla de ejemplo.")

    print(" Configuración completada con éxito.")


def main():
    parser = argparse.ArgumentParser(description="Recommend the best AI model for a task based on user subscriptions.")
    parser.add_argument("--task", type=str, help="Task description or prompt to evaluate")
    parser.add_argument("--criterion", type=str, choices=["auto", "frontend", "coding", "agentic", "speed", "cost", "intelligence"],
                        default="auto", help="Evaluation criterion (default: auto-detected from task)")
    parser.add_argument("--api-key", type=str, default=None, help="Explicit Artificial Analysis API key")
    parser.add_argument("--all-models", action="store_true", help="Evaluate all available models without subscription filtering")
    parser.add_argument("--no-blind", "--unmask", dest="blind", action="store_false", default=True,
                        help="Disable double-blind mode and show brand names directly (blind is active by default)")
    parser.add_argument("--format", type=str, choices=["json", "markdown"], default="json", help="Output format (default: json)")
    parser.add_argument("--human", action="store_true", help="Shortcut for --format markdown (human-readable)")
    parser.add_argument("--refresh", action="store_true", help="Force refresh cache from Artificial Analysis API")
    parser.add_argument("--setup", action="store_true", help="Run interactive onboarding wizard")

    args = parser.parse_args()

    if args.setup:
        run_setup()
        return

    if not args.task:
        parser.error("the following arguments are required: --task (or run with --setup)")

    use_markdown = args.human or (args.format == "markdown")

    try:
        api_key = find_api_key(args.api_key)
        if not api_key:
            err_msg = "Missing API key. Set ART_ANA in .env or pass --api-key. Get a free key at https://artificialanalysis.ai"
            if use_markdown:
                print(f"❌ **Error:** {err_msg}")
            else:
                print(json.dumps({"status": "error", "message": err_msg, "task": args.task}, indent=2))
            sys.exit(1)

        all_models = fetch_models_data(api_key, refresh=args.refresh)
        if args.all_models:
            available_models = [
                {
                    "raw": m,
                    "subscription": "Public API / Universal",
                    "name": m.get("name", "Unknown"),
                    "slug": m.get("slug", ""),
                    "creator": (m.get("model_creator") or {}).get("name", "Unknown"),
                    "release_date": m.get("release_date") or "",
                    "evaluations": m.get("evaluations") or {},
                    "performance": m.get("performance") or {},
                    "pricing": m.get("pricing") or {},
                }
                for m in all_models
            ]
        else:
            subscriptions = load_subscriptions()
            available_models = filter_models_by_subscriptions(all_models, subscriptions)

        if not available_models:
            err_msg = "No models matched the active subscriptions defined in subscriptions.json"
            if use_markdown:
                print(f"❌ **Error:** {err_msg}")
            else:
                print(json.dumps({"status": "error", "message": err_msg, "task": args.task}, indent=2))
            sys.exit(1)

        detected_criterion = args.criterion
        if detected_criterion == "auto":
            detected_criterion = infer_criterion(args.task)

        ranked = rank_models(available_models, detected_criterion)
        recommended = ranked[0]
        alternatives = ranked[1:4] if len(ranked) > 1 else []

        if args.blind:
            letters = ["Candidate_A", "Candidate_B", "Candidate_C", "Candidate_D"]
            reveal_map = {
                letters[0]: {
                    "name": recommended["name"],
                    "slug": recommended["slug"],
                    "subscription": recommended["subscription"],
                    "creator": recommended["creator"],
                }
            }
            alt_blind = []
            for i, a in enumerate(alternatives, start=1):
                cid = letters[i]
                reveal_map[cid] = {
                    "name": a["name"],
                    "slug": a["slug"],
                    "subscription": a["subscription"],
                    "creator": a["creator"],
                }
                alt_blind.append({
                    "candidate_id": cid,
                    "score": a["score"],
                    "metrics": a["metric_details"],
                })

            result = {
                "status": "success",
                "task": args.task,
                "detected_criterion": detected_criterion,
                "blind_mode": True,
                "recommended_model": {
                    "candidate_id": letters[0],
                    "score": recommended["score"],
                    "reason": f"Top score ({recommended['score']}) on objective benchmark '{detected_criterion}'.",
                    "metrics": recommended["metric_details"],
                },
                "alternatives": alt_blind,
                "reveal": reveal_map,
                "total_available_models_evaluated": len(ranked),
            }
        else:
            reason_text = (
                f"Top model for '{detected_criterion}' with score {recommended['score']} "
                f"under active subscription '{recommended['subscription']}'."
            )
            result = {
                "status": "success",
                "task": args.task,
                "detected_criterion": detected_criterion,
                "blind_mode": False,
                "recommended_model": {
                    "name": recommended["name"],
                    "slug": recommended["slug"],
                    "subscription": recommended["subscription"],
                    "creator": recommended["creator"],
                    "score": recommended["score"],
                    "reason": reason_text,
                    "metrics": recommended["metric_details"],
                },
                "alternatives": [
                    {
                        "name": a["name"],
                        "slug": a["slug"],
                        "subscription": a["subscription"],
                        "creator": a["creator"],
                        "score": a["score"],
                        "metrics": a["metric_details"],
                    }
                    for a in alternatives
                ],
                "total_available_models_evaluated": len(ranked),
            }

        if use_markdown:
            print(format_markdown_output(result, blind=args.blind))
        else:
            print(json.dumps(result, indent=2))

    except Exception as e:
        if use_markdown:
            print(f"❌ **Error:** {str(e)}")
        else:
            print(json.dumps({"status": "error", "message": str(e), "task": args.task}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
