import argparse
import os
import re
import sys
from pathlib import Path

from google import genai

from verifier import Verifier


class CodeFixerAgent:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        load_env_file()
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
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

        any_block = re.search(r"```\s*(.*?)```", response_text, flags=re.DOTALL)
        if any_block:
            return any_block.group(1).strip()

        return response_text.strip()

    def generate_fix(
        self,
        error_trace: str,
        target_file: str = "target_app/calculator.py",
        test_file: str = "target_app/test_calculator.py",
    ) -> str:
        target_path = Path(target_file)
        test_path = Path(test_file)
        source_code = target_path.read_text(encoding="utf-8")
        test_code = test_path.read_text(encoding="utf-8")

        prompt = f"""You are an autonomous bug-fixing agent.

A Python unit test suite is failing. Update only the target file so all tests pass.

Return the complete corrected contents of {target_file} inside <fixed_code> tags.
Do not include explanations, diffs, markdown fences, or changes to the test file.

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
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return self.extract_code(getattr(response, "text", "") or str(response))


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def write_valid_python(path: Path, code: str) -> None:
    if not code.strip():
        raise ValueError("Refusing to write empty generated code.")

    compile(code, str(path), "exec")
    path.write_text(code.rstrip() + "\n", encoding="utf-8")


def run_loop(
    target_file: str = "target_app/calculator.py",
    test_file: str = "target_app/test_calculator.py",
    max_attempts: int = 3,
    model_name: str = "gemini-2.5-flash",
) -> int:
    verifier = Verifier()
    agent = CodeFixerAgent(model_name=model_name)
    target_path = Path(target_file)

    for attempt in range(1, max_attempts + 1):
        result = verifier.run()

        if result.passed:
            print(f"Tests passed on attempt {attempt}.")
            print(result.output)
            return 0

        print(f"Attempt {attempt} failed. Asking Gemini for a fix...")
        print(result.error_trace)

        try:
            fixed_code = agent.generate_fix(
                error_trace=result.error_trace,
                target_file=target_file,
                test_file=test_file,
            )
            write_valid_python(target_path, fixed_code)
        except Exception as exc:
            print(f"Could not generate/apply fix: {exc}", file=sys.stderr)
            return 1

    final_result = verifier.run()
    print(final_result.output or final_result.error_trace)
    return 0 if final_result.passed else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair target_app with Gemini until pytest passes.")
    parser.add_argument("--target-file", default="target_app/calculator.py")
    parser.add_argument("--test-file", default="target_app/test_calculator.py")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--model", default="gemini-2.5-flash")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        run_loop(
            target_file=args.target_file,
            test_file=args.test_file,
            max_attempts=args.max_attempts,
            model_name=args.model,
        )
    )
