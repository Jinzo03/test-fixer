import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerificationResult:
    passed: bool
    exit_code: int
    output: str
    error_trace: str


class Verifier:
    def __init__(self, target_dir: str = "target_app"):
        self.target_dir = Path(target_dir).resolve()

    def run(self) -> VerificationResult:
        """Executes pytest on the target directory and captures execution details."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(self.target_dir)],
                capture_output=True,
                text=True,
                timeout=30,  # Prevent infinite execution loops
            )

            return VerificationResult(
                passed=(result.returncode == 0),
                exit_code=result.returncode,
                output=result.stdout,
                error_trace=result.stderr or result.stdout,
            )
        except subprocess.TimeoutExpired:
            return VerificationResult(
                passed=False,
                exit_code=-1,
                output="",
                error_trace="Verification timed out after 30 seconds.",
            )
        except Exception as e:
            return VerificationResult(
                passed=False,
                exit_code=-2,
                output="",
                error_trace=f"Verifier system failure: {str(e)}",
            )


if __name__ == "__main__":
    # Test execution
    verifier = Verifier()
    res = verifier.run()

    print(f"Passed: {res.passed}")
    print(f"Exit Code: {res.exit_code}")
    print("\n--- Raw Output ---\n")
    print(res.output)
