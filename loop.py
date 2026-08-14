import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from context_builder import ContextBuilder
from memory import EpisodicMemory, ProceduralMemory
from sandbox import GitSandbox
from verifier import Verifier


def write_valid_python(path: Path, code: str) -> None:
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
            "Gemini response did not contain <fixed_code> tags or a Python block."
        )

    def generate_fix(
        self,
        error_trace: str,
        target_path: Path,
        test_path: Path,
        codebase_context: str = "",
        history: list[dict] | None = None,
        episodic_memory_str: str = "",
        procedural_memory_str: str = "",
    ) -> str:
        source_code = target_path.read_text(encoding="utf-8")
        test_code = test_path.read_text(encoding="utf-8")

        working_memory_str = ""
        if history:
            working_memory_str = (
                "### Working Memory (Previous Failed Attempts in THIS Current Run):\n"
            )
            for item in history:
                working_memory_str += f"""
--- Failed Attempt #{item['attempt']} ---
Code Executed:
{item['code']}

Error Produced:
{item['error']}
"""

        prompt = f"""You are an autonomous Python bug-fixing agent.

Modify ONLY the target file so that all unit tests pass.

Return the complete corrected contents inside <fixed_code> tags.
Do not include explanations, markdown fences, or changes to the test file.

{procedural_memory_str}

{episodic_memory_str}

{codebase_context}

Target file: {target_path.name}
<target_code>
{source_code}
</target_code>

Test file: {test_path.name}
<test_code>
{test_code}
</test_code>

Current failing test output:
<error_trace>
{error_trace}
</error_trace>

{working_memory_str}

IMPORTANT:
1. STRICTLY follow all guidelines in Procedural Memory.
2. Review imported helper modules in Codebase Context carefully to understand how data is sanitized/processed.
3. Do not repeat failed approaches from Working Memory.
4. Return ONLY the corrected Python source inside <fixed_code> tags.
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
) -> int:
    agent = CodeFixerAgent(model_name=model_name)
    episodic_memory = EpisodicMemory()
    procedural_memory = ProceduralMemory()

    sandbox = GitSandbox()
    try:
        sandbox_dir = sandbox.enter()
        print(f" Isolated sandbox created at: {sandbox_dir}")
    except Exception as e:
        print(f"Failed to enter sandbox: {e}", file=sys.stderr)
        return 1

    sandbox_target_path = sandbox_dir / target_file
    sandbox_test_dir = sandbox_dir / Path(target_file).parent

    # Initialize AST Context Builder on Sandbox codebase
    context_builder = ContextBuilder(root_dir=sandbox_dir)
    verifier = Verifier(target_dir=str(sandbox_test_dir))

    attempt_history = []
    initial_error_log = ""
    success = False

    try:
        for attempt in range(1, max_attempts + 1):
            result = verifier.run()

            if result.passed:
                print(f" Tests passed on attempt {attempt} inside sandbox!")
                success = True
                break

            print(f"Attempt {attempt} failed inside sandbox. Retrying...")

            if attempt == 1:
                initial_error_log = result.error_trace

            current_code = sandbox_target_path.read_text(encoding="utf-8")
            attempt_history.append({
                "attempt": attempt,
                "code": current_code,
                "error": result.error_trace,
            })

            # Fetch multi-file import dependencies
            codebase_context = context_builder.build_context_prompt(
                target_file=sandbox_target_path,
                test_file=sandbox_dir / test_file,
            )

            episodic_str = episodic_memory.format_for_prompt()
            procedural_str = procedural_memory.get_rules()

            fixed_code = agent.generate_fix(
                error_trace=result.error_trace,
                target_path=sandbox_target_path,
                test_path=sandbox_dir / test_file,
                codebase_context=codebase_context,
                history=attempt_history,
                episodic_memory_str=episodic_str,
                procedural_memory_str=procedural_str,
            )

            write_valid_python(sandbox_target_path, fixed_code)

        if not success:
            final_result = verifier.run()
            success = final_result.passed

        if success:
            commit_msg = (
                f"fix(auto): repair {target_file} to pass unit tests\n\n"
                f"Automated repair verified via pytest."
            )
            branch = sandbox.commit_and_merge(
                target_file_rel=target_file,
                commit_message=commit_msg,
            )
            print(f" Fix committed to new git branch: '{branch}'!")

            final_code = Path(target_file).read_text(encoding="utf-8")
            episodic_memory.save_successful_episode(
                target_file=target_file,
                initial_error=initial_error_log or "Initial failure",
                solution_code=final_code,
            )
            print(" Saved successful fix to store/episodes.json!")
            return 0
        else:
            print(
                " Max attempts reached. Abandoning sandbox without touching main files."
            )
            return 1

    finally:
        sandbox.cleanup()
        print(" Worktree sandbox cleaned up.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair multi-file target_app inside Git Sandbox using Gemini."
    )
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