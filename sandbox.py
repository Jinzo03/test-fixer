import shutil
import subprocess
import time
from pathlib import Path


class GitSandbox:
    """Manages isolated git worktrees and automated branch commits."""

    def __init__(self, repo_dir: str = "."):
        self.repo_dir = Path(repo_dir).resolve()
        self.timestamp = int(time.time())
        self.branch_name = f"agent-fix-{self.timestamp}"
        self.worktree_dir = self.repo_dir / ".sandboxes" / self.branch_name

    def enter(self) -> Path:
        self.worktree_dir.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "-b",
                self.branch_name,
                str(self.worktree_dir),
            ],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create git worktree: {result.stderr}")

        return self.worktree_dir

    def commit_and_merge(self, target_file_rel: str, commit_message: str) -> str:
        """Copies fix back, creates a dedicated feature branch, and commits cleanly."""
        sandbox_target = self.worktree_dir / target_file_rel
        main_target = self.repo_dir / target_file_rel

        if sandbox_target.exists():
            shutil.copy2(sandbox_target, main_target)

        feature_branch = f"fix/auto-repair-{self.timestamp}"

        # Create new feature branch in main repo and commit
        subprocess.run(
            ["git", "checkout", "-b", feature_branch],
            cwd=self.repo_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "add", target_file_rel],
            cwd=self.repo_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=self.repo_dir,
            capture_output=True,
        )

        return feature_branch

    def cleanup(self) -> None:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(self.worktree_dir)],
            cwd=self.repo_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "branch", "-D", self.branch_name],
            cwd=self.repo_dir,
            capture_output=True,
        )