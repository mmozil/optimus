"""
Agent Optimus — Eval Runner (Phase 16).
Automated evaluation framework to measure agent performance.
Reads test cases from YAML, executes them against agents, and generates reports.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from colorama import Fore, Style, init

from src.core.agent_factory import AgentFactory
from src.core.gateway import gateway

# Initialize colorama
init(autoreset=True)

logger = logging.getLogger(__name__)


@dataclass
class EvalCase:
    id: str
    name: str
    prompt: str
    expected_contains: list[str] = field(default_factory=list)
    expected_tool_use: list[str] = field(default_factory=list)
    target_agent: str = "optimus"
    max_steps: int = 5
    min_len: int = 0


@dataclass
class EvalResult:
    case_id: str
    success: bool
    duration_s: float
    output: str
    tool_calls: list[str]
    error: str = ""
    score: float = 0.0  # 0.0 to 1.0


class EvalRunner:
    """Runs evaluation benchmarks against the agent system."""

    def __init__(self, cases_path: str = "tests/eval/eval_cases.yaml"):
        self.cases_path = Path(cases_path)
        self.results: list[EvalResult] = []

    def load_cases(self) -> list[EvalCase]:
        if not self.cases_path.exists():
            if self.cases_path.is_absolute():
                 logger.error(f"Cases file not found: {self.cases_path}")
                 return []
            
            # Try finding relative to project root if not found
            project_root = Path(__file__).parent.parent.parent
            self.cases_path = project_root / self.cases_path
            
            if not self.cases_path.exists():
                logger.error(f"Cases file not found: {self.cases_path}")
                return []

        with open(self.cases_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return [EvalCase(**c) for c in data.get("cases", [])]

    async def run_case(self, case: EvalCase) -> EvalResult:
        """Execute a single test case."""
        print(f"Running: {case.name} ({case.id})... ", end="", flush=True)
        start_time = time.monotonic()

        try:
            # Use gateway to route correctly (handles session bootstrap etc)
            response = await gateway.route_message(
                message=case.prompt,
                target_agent=case.target_agent,
                user_id="eval_user",
            )
            
            duration = time.monotonic() - start_time
            content = response.get("content", "")
            
            # Extract tool calls from history if available, 
            # otherwise simplistic check on content isn't enough for tool verify.
            # Ideally we'd inspect the actual ReAct steps, but for now we look at content/logs?
            # Actually, gateway returns final response. 
            # To verify tool usage, we might need to inspect the 'steps' if returned,
            # or rely on the agent wrapper exposing it.
            # Current gateway response is simple dict. 
            # We'll assume successful response contains the answer.
            
            # Evaluation Logic
            passed = True
            error_msg = []
            
            # 1. content check
            for expected in case.expected_contains:
                if expected.lower() not in content.lower():
                    passed = False
                    error_msg.append(f"Missing '{expected}'")

            # 2. min length
            if len(content) < case.min_len:
                passed = False
                error_msg.append(f"Too short ({len(content)} < {case.min_len})")

            # 3. Tool use check (hard to do without structured return, assuming passed for now if content ok)
            # Future improvement: return execution steps from gateway
            
            score = 1.0 if passed else 0.0
            
            status_color = Fore.GREEN if passed else Fore.RED
            status_text = "PASS" if passed else "FAIL"
            print(f"{status_color}{status_text} {Style.RESET_ALL}({duration:.2f}s)")
            
            if not passed:
                print(f"  Expected: {case.expected_contains}")
                print(f"  Got: {content[:100]}...")

            return EvalResult(
                case_id=case.id,
                success=passed,
                duration_s=duration,
                output=content,
                tool_calls=[], # Placeholder
                error=", ".join(error_msg),
                score=score
            )

        except Exception as e:
            duration = time.monotonic() - start_time
            print(f"{Fore.RED}ERROR {Style.RESET_ALL}({duration:.2f}s)")
            print(f"  {str(e)}")
            return EvalResult(
                case_id=case.id,
                success=False,
                duration_s=duration,
                output="",
                tool_calls=[],
                error=str(e),
                score=0.0
            )

    async def run_all(self):
        """Run all loaded test cases."""
        cases = self.load_cases()
        if not cases:
            print("No cases loaded.")
            return

        print(f"\n🚀 Starting Evaluation Suite: {len(cases)} cases\n")
        
        # Initialize system once
        await gateway.initialize()
        
        results = []
        for case in cases:
            res = await self.run_case(case)
            results.append(res)
            
        self.print_summary(results)
        self.save_report(results)

    def print_summary(self, results: list[EvalResult]):
        total = len(results)
        passed = sum(1 for r in results if r.success)
        avg_duration = sum(r.duration_s for r in results) / total if total else 0
        
        print(f"\n📊 {Style.BRIGHT}RESULTS SUMMARY{Style.RESET_ALL}")
        print(f"Total Cases: {total}")
        print(f"Passed:      {Fore.GREEN}{passed}{Style.RESET_ALL}")
        print(f"Failed:      {Fore.RED}{total - passed}{Style.RESET_ALL}")
        print(f"Accuracy:    {passed/total*100:.1f}%")
        print(f"Avg Latency: {avg_duration:.2f}s")

    def save_report(self, results: list[EvalResult]):
        report = {
            "timestamp": time.time(),
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.success),
                "accuracy": sum(1 for r in results if r.success) / len(results) if results else 0
            },
            "cases": [
                {
                    "id": r.case_id,
                    "success": r.success,
                    "duration": r.duration_s,
                    "error": r.error,
                    "output_preview": r.output[:100]
                }
                for r in results
            ]
        }
        
        out_path = Path("tests/eval/report.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to {out_path}")


if __name__ == "__main__":
    runner = EvalRunner()
    asyncio.run(runner.run_all())
