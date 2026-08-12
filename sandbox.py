import shutil
import subprocess
import time
from pathlib import Path


class GitSandbox:
    """Manages isolated git worktrees for agent execution."""

    def __init__(self, repo_dir: str = "."):
        self.repo_dir = Path(repo_dir).resolve()
        self.timestamp = int(time.time())
        self.branch_name = f"agent-fix-{self.timestamp}"
        self.worktree_dir = self.repo_dir / ".sandboxes" / self.branch_name

    def enter(self) -> Path:
        """Creates an isolated git worktree directory and branch."""
        self.worktree_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Create worktree off current HEAD
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
            raise RuntimeError(
                f"Failed to create git worktree: {result.stderr}"
            )

        return self.worktree_dir

    def apply_to_main(self, target_file_rel: str) -> None:
        """Copies successful fixes from the sandbox back to main working directory."""
        sandbox_target = self.worktree_dir / target_file_rel
        main_target = self.repo_dir / target_file_rel

        if sandbox_target.exists():
            shutil.copy2(sandbox_target, main_target)

    def cleanup(self) -> None:
        """Destroys the isolated worktree and branch cleanly."""
        # Force remove worktree directory
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(self.worktree_dir)],
            cwd=self.repo_dir,
            capture_output=True,
        )
        # Delete temporary branch
        subprocess.run(
            ["git", "branch", "-D", self.branch_name],
            cwd=self.repo_dir,
            capture_output=True,
        )