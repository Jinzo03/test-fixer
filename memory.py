import json
from pathlib import Path


class EpisodicMemory:
    def __init__(self, memory_file: str = "store/episodes.json"):
        self.memory_path = Path(memory_file)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_path.exists():
            self.memory_path.write_text("[]", encoding="utf-8")

    def load_episodes(self) -> list[dict]:
        try:
            return json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def save_successful_episode(
        self, target_file: str, initial_error: str, solution_code: str
    ) -> None:
        episodes = self.load_episodes()
        episodes.append(
            {
                "target_file": target_file,
                "initial_error": initial_error.strip(),
                "solution_code": solution_code.strip(),
            }
        )
        episodes = episodes[-5:]  # Keep latest 5 episodes
        self.memory_path.write_text(
            json.dumps(episodes, indent=2), encoding="utf-8"
        )

    def format_for_prompt(self) -> str:
        episodes = self.load_episodes()
        if not episodes:
            return ""

        formatted = (
            "### Long-Term Episodic Memory (Past Successful Fixes Across Sessions):\n"
        )
        for idx, ep in enumerate(episodes, 1):
            err_snippet = (
                ep["initial_error"][:200] + "..."
                if len(ep["initial_error"]) > 200
                else ep["initial_error"]
            )
            formatted += f"""
--- Episode #{idx} ({ep['target_file']}) ---
Error Log Snippet:
{err_snippet}

Passed Fix Implemented:
{ep['solution_code']}
"""
        return formatted