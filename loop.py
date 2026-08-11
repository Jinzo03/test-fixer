import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from memory import EpisodicMemory
from verifier import Verifier


def write_valid_python(path: Path, code: str) -> None:
    """Validate Python syntax before replacing the target file."""
    compile(code, str(path), "exec")
    path.write_text(code, encoding="utf-8")


class CodeFixerAgent:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def extract_code(self, response_text: str) -> str:
        """Extract corrected Python source from a model response."""
        if not response_text:
            raise ValueError("Gemini returned an empty response.")

        tagged = re.search(
            r"<fixed_code>\s*(.*?)\s*</fixed_code>",
            response_text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        if tagged:
            return tagged.group(1).strip()

        python_block = re.search(
            r"```(?:python|py)\s*(.*?)```",
            response_text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        if python_block:
            return python_block.group(1).strip()

        raise ValueError(
            "Gemini response did not contain <fixed_code> tags "
            "or a Python code block."
        )

    def generate_fix(
        self,
        error_trace: str,
        target_file: str = "target_app/calculator.py",
        test_file: str = "target_app/test_calculator.py",
        history: list[dict] | None = None,
    ) -> str:

        target_path = Path(target_file)
        test_path = Path(test_file)

        source_code = target_path.read_text(encoding="utf-8")
        test_code = test_path.read_text(encoding="utf-8")

        history_str = ""

        if history:
            history_str = (
                "### Previous Failed Attempts in This Session:\n"
            )

            for item in history:
                history_str += f"""
--- Attempt #{item['attempt']} ---
Code Executed:
{item['code']}

Error Produced:
{item['error']}
"""

        prompt = f"""You are an autonomous Python bug-fixing agent.

A Python unit test suite is failing.

Your task is to modify ONLY the target file so that all tests pass.

Return the complete corrected contents of {target_file}
inside <fixed_code> tags.

Do not include explanations.
Do not include markdown fences.
Do not modify the test file.

Target file: {target_file}

<target_code>
{source_code}
</target_code>

Test file: {test_file}

<test_code>
{test_code}
</test_code>

Failing test output:

<error_trace>
{error_trace}
</error_trace>

{history_str}

IMPORTANT:
Do not repeat failed approaches from previous attempts.
Return ONLY the corrected Python source inside <fixed_code> tags.
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        return self.extract_code(response.text or "")


def run_loop(
    target_file: str = "target_app/calculator.py",
    test_file: str = "target_app/test_calculator.py",
    max_attempts: int = 3,
    model_name: str = "gemini-2.5-flash",
    memory: EpisodicMemory | None = None,
) -> int:

    verifier = Verifier()
    agent = CodeFixerAgent(model_name=model_name)

    target_path = Path(target_file)

    attempt_history = []

    for attempt in range(1, max_attempts + 1):

        result = verifier.run()

        if result.passed:
            print(f"Tests passed on attempt {attempt}!")
            print(result.output)
            return 0

        print(
            f"Attempt {attempt} failed. "
            "Generating a fix with Gemini..."
        )

        try:
            # Save the code that ACTUALLY produced this failure.
            current_code = target_path.read_text(encoding="utf-8")

            attempt_history.append({
                "attempt": attempt,
                "code": current_code,
                "error": result.error_trace,
            })

            fixed_code = agent.generate_fix(
                error_trace=result.error_trace,
                target_file=target_file,
                test_file=test_file,
                history=attempt_history,
            )

            write_valid_python(target_path, fixed_code)

        except Exception as exc:
            print(
                f"Could not generate/apply fix: {exc}",
                file=sys.stderr,
            )
            return 1

    # Test the final generated code.
    final_result = verifier.run()

    if final_result.passed:
        print("Final generated fix passed!")
        print(final_result.output)
        return 0

    print(final_result.output or final_result.error_trace)
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair target_app with Gemini until pytest passes."
    )

    parser.add_argument(
        "--target-file",
        default="target_app/calculator.py",
    )

    parser.add_argument(
        "--test-file",
        default="target_app/test_calculator.py",
    )

    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    raise SystemExit(
        run_loop(
            memory=EpisodicMemory(),
            target_file=args.target_file,
            test_file=args.test_file,
            max_attempts=args.max_attempts,
            model_name=args.model,
        )
    )