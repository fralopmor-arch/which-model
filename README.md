# Which Model (`which-model`)

An objective, zero-bias AI model router and decision skill for AI agents (Claude Code, Cursor, Antigravity, Codex, etc.), powered by live benchmark, latency, and pricing data from the **[Artificial Analysis Data API](https://artificialanalysis.ai/data-api/docs#overview-hero)**.

Filters over 200+ models down to the user's active subscriptions (`Google AI Pro`, `Claude Max`, `Grok`, `ChatGPT Plus`, or the full public API catalog) and evaluates them in **double-blind mode** (`Candidate_A`, `Candidate_B`...) to eliminate LLM corporate self-preference.

---

## Features

- **Zero Vendor Bias (Double-Blind by Default):** Masks model identities during evaluation so the host LLM cannot favor its own creator.
- **Subscription-Aware:** Recommends only models you actually pay for (configured in `subscriptions.json`), or evaluates the entire market with `--all-models`.
- **Smart Task Detection:** Automatically routes across 6 domains:
  - `frontend` — Vibe coding, UI/UX, React, Tailwind (60% Coding + 40% Agentic composite).
  - `coding` — Backend, refactoring, testing, algorithms (`coding_index`).
  - `agentic` — Terminal/CLI workflows, bash, tool use, TerminalBench (`agentic_index`).
  - `speed` — Real-time streaming and low latency (`output_tokens_per_second`).
  - `cost` — High-volume batch processing at lowest price per 1M tokens.
  - `intelligence` — Deep reasoning, math, science, strategy (`intelligence_index`).
- **Zero External Dependencies:** 100% Python 3 standard library (`urllib`, `json`, `argparse`, `pathlib`). No `pip install` required.
- **24h Local Cache:** Instant responses without burning API rate limits.

---

## Installation

### Using Skills CLI
```bash
npx skills add fralopmor-arch/which-model
```

### Manual Installation
Clone directly into your `.agents/skills/` or `.claude/skills/` directory:
```bash
git clone https://github.com/fralopmor-arch/which-model.git skills/which-model
```

---

## Quick Setup

1. Get a free API key at **[artificialanalysis.ai](https://artificialanalysis.ai)**.
2. Run the interactive onboarding wizard:
   ```bash
   python skills/which-model/scripts/which_model.py --setup
   ```
   Or create a `.env` file with:
   ```env
   ART_ANA='your_api_key_here'
   ```
3. Customize your active subscriptions in `subscriptions.json` (see `subscriptions.example.json` for presets).

---

## Usage

### For Humans (Markdown Summary)
```bash
python skills/which-model/scripts/which_model.py --task "Frontend vibe coding in React and Tailwind" --human
```

**Output:**
```markdown
🏆 #1 Recomendado: Claude Opus 5 (Xhigh) (`Claude Max`)
- Criterio: `frontend` (Score: 68.44)
- Vibe Composite Score: 68.44
- Coding Index: 77.0

🥈 Top del resto:
2. Grok 4.6 (Medium) (`Grok`) — Score: 64.88
3. Claude Sonnet 5 (Max) (`Claude Max`) — Score: 60.34
4. Gemini 3.5 Flash (High) (`Google AI Pro`) — Score: 52.46
```

### For AI Agents (Pure JSON Contract)
```bash
python skills/which-model/scripts/which_model.py --task "Terminal bench v4.0 CLI automation"
```

### CLI Options
| Flag | Description |
|---|---|
| `--task "<TEXT>"` | Task description or prompt to evaluate |
| `--criterion <TYPE>` | Force criterion: `auto`, `frontend`, `coding`, `agentic`, `speed`, `cost`, `intelligence` |
| `--human` | Output concise Markdown instead of JSON |
| `--no-blind`, `--unmask` | Disable double-blind mode and show brand names directly |
| `--all-models` | Evaluate all 200+ models in the market ignoring subscription filters |
| `--refresh` | Force refresh the 24-hour local cache |
| `--setup` | Run interactive setup wizard |
