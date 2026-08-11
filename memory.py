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

    def save_successful_episode(self, target_file: str, initial_error: str, final_code: str):
        episodes = self.load_episodes()
        episodes.append({
            "target_file": target_file,
            "initial_error": initial_error,
            "solution_code": final_code
        })
        # Keep only the last 10 episodes to keep context clean
        episodes = episodes[-10:]
        self.memory_path.write_text(json.dumps(episodes, indent=2), encoding="utf-8")

    def format_for_prompt(self) -> str:
        episodes = self.load_episodes()
        if not episodes:
            return ""

        formatted = "### Long-Term Episodic Memory (Past Successful Fixes in Other Files/Sessions):\n"
        for idx, ep in enumerate(episodes, 1):
            formatted += f"""
--- Past Fix #{idx} ---
Error Context: {ep['initial_error'][:150]}...
Working Solution Snippet:
{ep['solution_code']}
"""
        return formatted