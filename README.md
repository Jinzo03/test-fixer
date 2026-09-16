# Test-Fixer

**Test-Fixer** is an autonomous code-repair agent. Point it at a Python module and its failing pytest suite, and it iteratively rewrites the module — using Gemini — until the tests pass, learning from both its in-session attempts and past successful runs.

## How It Works

1. **Verify** — `verifier.py` runs `pytest` against the target directory and captures the failure output.
2. **Fix** — `loop.py` sends the failing test, the current source, and the error trace to Gemini, which returns a corrected version of the target file inside `<fixed_code>` tags.
3. **Apply & Repeat** — the fix is written back (after a syntax check via `compile()`) and the suite is re-run, up to a configurable number of attempts.
4. **Remember** — on success, the fix is saved to long-term episodic memory so future runs on similar failures can reference what already worked.

```
pytest ──▶ failing? ──▶ Gemini generates fix ──▶ write & re-run ──▶ pass? ──▶ save episode
   ▲                                                                  │
   └──────────────────────────── retry (max_attempts) ────────────────┘
```

## Key Components

- **`loop.py`** — The main agent loop: drives the fix/verify cycle and orchestrates memory and the Gemini client (`gemini-2.5-flash` by default).
- **`verifier.py`** — Runs pytest as a subprocess and returns a structured pass/fail result, including captured stdout/stderr.
- **`memory.py`** — Two-tier memory system:
  - *Procedural memory* — static rules loaded from `store/SKILL.md`, injected into every prompt.
  - *Episodic memory* — the last 5 successful fixes, persisted to `store/episodes.json`, reused as few-shot context in later runs.
- **`sandbox.py`** — Isolates each agent run in its own git worktree/branch so fixes can be trialed and applied without touching the main working tree.
- **`target_app/`** — The sample buggy module (`calculator.py`) and its pytest suite (`test_calculator.py`) used to demonstrate the loop.

## Getting Started

### Requirements

- Python 3.10+
- A [Gemini API key](https://ai.google.dev/)

### Installation

```bash
git clone https://github.com/Jinzo03/test-fixer.git
cd test-fixer
python -m venv venv && source venv/bin/activate
pip install google-genai python-dotenv pytest
```

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_api_key_here
```

### Usage

Run the agent against the bundled sample app:

```bash
python loop.py
```

Or target a different module and test file:

```bash
python loop.py --target-file path/to/module.py --test-file path/to/test_module.py --max-attempts 5 --model gemini-2.5-flash
```

## Project Structure

```
test-fixer/
├── loop.py                       # Agent loop: verify → generate fix → apply → repeat
├── verifier.py                   # Pytest execution and result capture
├── memory.py                     # Procedural + episodic memory
├── sandbox.py                    # Git worktree isolation for agent runs
├── pytest.ini
├── target_app/
│   ├── calculator.py              # Sample module to be fixed
│   └── test_calculator.py         # Sample failing test suite
└── store/                        # Generated at runtime: SKILL.md, episodes.json (gitignored)
```

## Disclaimer

This is an experimental, educational project demonstrating an LLM-driven self-correcting code loop on a small sample application. It is not intended for unsupervised use against production codebases.
