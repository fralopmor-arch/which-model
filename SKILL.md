---
name: which-model
description: Recommends the optimal AI model for a task based on active subscriptions (Google AI, Claude, Grok) and live Artificial Analysis benchmarks. Triggers on "which model", "¿qué modelo uso?", "choose model for", "best model for", or benchmark queries.
---

# Which Model

Routes tasks to the optimal AI model using live Artificial Analysis benchmarks and active user subscriptions in double-blind mode.

## Rules & Protocol

1. **Zero Vendor Bias:** Strictly obey the ranking from `which_model.py`. Never promote or excuse your creator LLM.
2. **Execute:** Run `python skills/which-model/scripts/which_model.py --task "<TASK>"`.
3. **Response:**
   - **To Humans:** Ultra-brief. State **🏆 #1 Winner** (subscription + key score) followed by **🥈 Top del resto** (#2, #3, #4 in 1 line each). **NEVER output raw JSON blocks to human users.**
   - **To Agents:** Output the pure JSON contract for programmatic routing.

## CLI & Criteria

```bash
python skills/which-model/scripts/which_model.py --task "<TASK>" [--criterion <auto|frontend|coding|agentic|speed|cost>] [--all-models] [--human]
```

- **Criteria:** `frontend` (UI/vibe), `coding` (backend/tests), `agentic` (CLI/terminal/tools), `speed` (latency/throughput), `cost` (budget), `intelligence` (reasoning).
- **Flags:** `--no-blind` (show brands), `--all-models` (entire market catalog), `--refresh` (invalidate 24h cache), `--setup` (wizard).

## JSON Contract (Agents only)

```json
{
  "status": "success", "detected_criterion": "coding", "blind_mode": true,
  "recommended_model": { "candidate_id": "Candidate_A", "score": 77.0, "metrics": { ... } },
  "alternatives": [ { "candidate_id": "Candidate_B", "score": 74.4 } ],
  "reveal": { "Candidate_A": { "name": "Claude Opus 5 (Xhigh)", "subscription": "Claude Max" } }
}
```
