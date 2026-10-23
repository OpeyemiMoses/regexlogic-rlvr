"""
RegexLogic Deterministic Verifier & ReDoS Safety Engine
Provides strict, multi-stage ground-truth evaluation for regular expression generation:
1. Syntax Validation: Ensures pattern compiles in Python's `re` engine.
2. Positive Test Suite: Ensures all required positive strings match.
3. Negative Test Suite: Ensures all boundary/negative strings are rejected.
4. ReDoS Vulnerability Attack: Simulates pathological backtracking payloads.
5. Reward Calculation: Produces standardized verifiable rewards (0.0 - 1.0) for TRL GRPOTrainer.
"""

import re
import time
import signal
from typing import Dict, List, Any, Optional, Tuple


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException("Regex execution exceeded time limit (catastrophic backtracking / ReDoS).")


def run_with_timeout(func, args=(), kwargs=None, timeout_sec=0.08):
    """Executes a function with a strict wall-clock timeout using signal timer."""
    if kwargs is None:
        kwargs = {}
    
    # Register signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_sec)
    try:
        return func(*args, **kwargs)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


def extract_regex_from_text(text: str) -> Optional[str]:
    """
    Extracts the regex pattern from model outputs.
    Supports markdown code blocks, backticks, or regex literals /pattern/.
    """
    if not text:
        return None
    text = text.strip()

    # Pattern in fenced code block
    fenced_match = re.search(r"```(?:regex|regexp|python)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        cand = fenced_match.group(1).strip()
        # If it's a python statement, extract raw string or pattern
        sub_cand = re.search(r'r?[\'"](.*?)[\'"]', cand)
        if sub_cand:
            return sub_cand.group(1)
        return cand.split("\n")[0].strip()

    # Inline code
    inline_match = re.search(r"`([^`]+)`", text)
    if inline_match:
        cand = inline_match.group(1).strip()
        if cand.startswith("r'") or cand.startswith('r"'):
            cand = cand[2:-1]
        elif cand.startswith("'") or cand.startswith('"'):
            cand = cand[1:-1]
        return cand

    # Slash literal /.../
    slash_match = re.search(r"/([^/\n]+)/", text)
    if slash_match:
        return slash_match.group(1).strip()

    # Raw single line fallback
    first_line = text.split("\n")[0].strip()
    if len(first_line) < 300:
        if (first_line.startswith("'") and first_line.endswith("'")) or (first_line.startswith('"') and first_line.endswith('"')):
            return first_line[1:-1]
        return first_line

    return None


class RegexVerifier:
    """Deterministic verifier for regex correctness and computational safety."""

    def __init__(self, timeout_per_match: float = 0.08):
        self.timeout_per_match = timeout_per_match

    def verify(
        self,
        candidate_pattern: str,
        positive_cases: List[str],
        negative_cases: List[str],
        redos_payloads: Optional[List[str]] = None,
        flags: int = 0
    ) -> Dict[str, Any]:
        """
        Runs the complete 4-stage verification audit:
        Returns structured dictionary with rewards, breakdown, and diagnostic logs.
        """
        result = {
            "pattern": candidate_pattern,
            "compiled": False,
            "syntax_error": None,
            "positive_total": len(positive_cases),
            "positive_passed": 0,
            "positive_failures": [],
            "negative_total": len(negative_cases),
            "negative_passed": 0,
            "negative_failures": [],
            "redos_tested": False,
            "redos_safe": True,
            "redos_max_latency_ms": 0.0,
            "redos_failure_payload": None,
            "passed_all": False,
            "reward": 0.0,
            "status": "FAIL",
            "diagnosis": ""
        }

        if not candidate_pattern:
            result["diagnosis"] = "Empty or unparseable regex candidate."
            return result

        # Stage 1: Syntax compilation
        try:
            compiled_re = re.compile(candidate_pattern, flags)
            result["compiled"] = True
        except re.error as e:
            result["syntax_error"] = str(e)
            result["diagnosis"] = f"Syntax error: {e}"
            result["reward"] = 0.0
            return result

        # Stage 2: Positive match testing
        for s in positive_cases:
            try:
                matched = run_with_timeout(
                    lambda text: bool(compiled_re.fullmatch(text) or compiled_re.search(text)),
                    args=(s,),
                    timeout_sec=self.timeout_per_match
                )
                if matched:
                    result["positive_passed"] += 1
                else:
                    result["positive_failures"].append(s)
            except TimeoutException:
                result["positive_failures"].append(f"{s} (TIMEOUT)")
            except Exception as e:
                result["positive_failures"].append(f"{s} ({e})")

        # Stage 3: Negative match testing
        for s in negative_cases:
            try:
                matched = run_with_timeout(
                    lambda text: bool(compiled_re.fullmatch(text)),
                    args=(s,),
                    timeout_sec=self.timeout_per_match
                )
                if not matched:
                    result["negative_passed"] += 1
                else:
                    result["negative_failures"].append(s)
            except TimeoutException:
                result["negative_failures"].append(f"{s} (TIMEOUT)")
            except Exception as e:
                result["negative_failures"].append(f"{s} ({e})")

        # Stage 4: ReDoS Backtracking Safety Audit
        if redos_payloads:
            result["redos_tested"] = True
            for payload in redos_payloads:
                t0 = time.perf_counter()
                try:
                    run_with_timeout(
                        lambda text: compiled_re.search(text),
                        args=(payload,),
                        timeout_sec=self.timeout_per_match
                    )
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    if latency_ms > result["redos_max_latency_ms"]:
                        result["redos_max_latency_ms"] = round(latency_ms, 2)
                except TimeoutException:
                    result["redos_safe"] = False
                    result["redos_failure_payload"] = payload[:40] + ("..." if len(payload) > 40 else "")
                    result["redos_max_latency_ms"] = round(self.timeout_per_match * 1000.0, 2)
                    break

        # Compute Verifiable Reward
        pos_ratio = (result["positive_passed"] / result["positive_total"]) if result["positive_total"] > 0 else 1.0
        neg_ratio = (result["negative_passed"] / result["negative_total"]) if result["negative_total"] > 0 else 1.0
        accuracy = (pos_ratio + neg_ratio) / 2.0

        if not result["redos_safe"]:
            # Severe penalty for catastrophic backtracking vulnerability
            reward = accuracy * 0.3
            result["diagnosis"] = f"ReDoS Vulnerable: Pattern hung on evil payload '{result['redos_failure_payload']}'."
        elif accuracy == 1.0:
            reward = 1.0
            result["passed_all"] = True
            result["status"] = "PASS"
            result["diagnosis"] = "Fully verified: 100% test pass and ReDoS-immune."
        else:
            reward = accuracy * 0.8
            result["diagnosis"] = (
                f"Partial match: {result['positive_passed']}/{result['positive_total']} positive, "
                f"{result['negative_passed']}/{result['negative_total']} negative passed."
            )

        result["reward"] = round(reward, 4)
        return result


if __name__ == "__main__":
    verifier = RegexVerifier()
    # Test safe semver pattern
    safe_semver = r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    res = verifier.verify(
        safe_semver,
        positive_cases=["1.0.0", "v2.13.4-alpha.1", "0.0.4+build.2026"],
        negative_cases=["01.1.1", "v1.2", "1.2.3-"],
        redos_payloads=["v" + "1." * 40 + "X"]
    )
    print("Safe pattern result:", res["status"], "Reward:", res["reward"], "Latency:", res["redos_max_latency_ms"], "ms")

    # Test dangerous backtracking pattern: (a+)+$ on 'aaaaaaaaaaaaaaaaaaaaaaaaaaaa!'
    bad_redos = r"^(a+)+$"
    res_bad = verifier.verify(
        bad_redos,
        positive_cases=["a", "aaaa"],
        negative_cases=["b", "aab"],
        redos_payloads=["a" * 28 + "!"]
    )
    print("Bad pattern result:", res_bad["status"], "Reward:", res_bad["reward"], "ReDoS Safe:", res_bad["redos_safe"], "Diagnosis:", res_bad["diagnosis"])
