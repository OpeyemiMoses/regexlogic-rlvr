"""
Beam RegexLogic Trace Generator & Verifier
Queries reflection/Beam-1.0-501B-A23B across benchmark problems,
supporting multi-effort sweeps (low, medium), capturing full internal reasoning_content,
and evaluating with the deterministic 4-stage RegexVerifier.
Outputs complete datasets:
1. beam_full_traces.json: All verified attempts with reasoning traces
2. preference_pairs.json: DPO / Bradley-Terry preference pairs (chosen vs rejected)
3. rlvr_dataset.json: Prompts + ground truth specs for TRL GRPOTrainer
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from huggingface_hub import InferenceClient

from problems import PROBLEMS
from verifier import RegexVerifier, extract_regex_from_text


def run_benchmark(
    efforts: List[str] = ["low"],
    max_problems: Optional[int] = None,
    output_traces_file: str = "beam_traces.json",
    output_pairs_file: str = "preference_pairs.json"
) -> Dict[str, Any]:
    client = InferenceClient()
    verifier = RegexVerifier()

    target_problems = PROBLEMS[:max_problems] if max_problems else PROBLEMS
    total_runs = len(target_problems) * len(efforts)
    print(f"Starting Beam-1.0-501B-A23B benchmark run ({total_runs} runs: {len(target_problems)} problems x {efforts})...")

    all_traces = []
    effort_stats = {eff: {"total": 0, "passed": 0, "redos_safe": 0, "avg_latency": 0.0} for eff in efforts}
    problem_results = {p["id"]: {} for p in target_problems}

    run_idx = 0
    for eff in efforts:
        print(f"\n{'='*50}\nEVALUATING REASONING EFFORT: {eff.upper()}\n{'='*50}")
        latencies = []

        for p in target_problems:
            run_idx += 1
            pid = p["id"]
            category = p["category"]
            prompt = p["prompt"]
            print(f"[{run_idx}/{total_runs}] [{eff}] {p['title']} ({pid})...", end="", flush=True)

            t0 = time.perf_counter()
            try:
                response = client.chat.completions.create(
                    model="reflection/Beam-1.0-501B-A23B",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are Beam, an expert formal language and regular expressions reasoning assistant. "
                                "Reason carefully through the problem constraints, state transitions, and edge cases. "
                                "Ensure the pattern avoids catastrophic backtracking (ReDoS). "
                                "Output your final regular expression pattern enclosed in backticks."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=3072,
                    temperature=0.2,
                    extra_body={"reasoning_effort": eff}
                )
                elapsed_sec = round(time.perf_counter() - t0, 2)
                latencies.append(elapsed_sec)
                msg = response.choices[0].message
                content = msg.content or ""
                reasoning = getattr(msg, "reasoning_content", "") or ""

                # Extract candidate regex
                extracted_regex = extract_regex_from_text(content)
                if not extracted_regex and reasoning:
                    extracted_regex = extract_regex_from_text(reasoning)

                # Deterministic verification
                verif = verifier.verify(
                    candidate_pattern=extracted_regex,
                    positive_cases=p["positive"],
                    negative_cases=p["negative"],
                    redos_payloads=p.get("redos_payloads", [])
                )

                effort_stats[eff]["total"] += 1
                if verif["passed_all"]:
                    effort_stats[eff]["passed"] += 1
                if verif["redos_safe"]:
                    effort_stats[eff]["redos_safe"] += 1

                record = {
                    "problem_id": pid,
                    "title": p["title"],
                    "category": category,
                    "effort": eff,
                    "prompt": prompt,
                    "positive_tests": p["positive"],
                    "negative_tests": p["negative"],
                    "redos_payloads": p.get("redos_payloads", []),
                    "canonical_ref": p["canonical_ref"],
                    "extracted_regex": extracted_regex,
                    "reasoning_content": reasoning,
                    "reasoning_chars": len(reasoning),
                    "response_content": content,
                    "status": verif["status"],
                    "reward": verif["reward"],
                    "positive_passed": verif["positive_passed"],
                    "positive_total": verif["positive_total"],
                    "negative_passed": verif["negative_passed"],
                    "negative_total": verif["negative_total"],
                    "redos_safe": verif["redos_safe"],
                    "redos_latency_ms": verif["redos_max_latency_ms"],
                    "diagnosis": verif["diagnosis"],
                    "latency_sec": elapsed_sec,
                    "model": "reflection/Beam-1.0-501B-A23B"
                }
                all_traces.append(record)
                problem_results[pid][eff] = record

                print(f" -> {verif['status']} (reward={verif['reward']}) in {elapsed_sec}s | ReDoS: {verif['redos_safe']}")

            except Exception as e:
                print(f" -> ERROR: {e}")
                record = {
                    "problem_id": pid,
                    "title": p["title"],
                    "category": category,
                    "effort": eff,
                    "status": "ERROR",
                    "error": str(e)
                }
                all_traces.append(record)
                problem_results[pid][eff] = record

        if latencies:
            effort_stats[eff]["avg_latency"] = round(sum(latencies) / len(latencies), 2)

    # Build DPO Preference Pairs (chosen vs rejected)
    preference_pairs = []
    for pid, runs in problem_results.items():
        # Find high-reward run (chosen) vs lower-reward run or canonical vs failure
        candidates = [r for r in runs.values() if "reward" in r]
        if not candidates:
            continue
        sorted_runs = sorted(candidates, key=lambda x: x["reward"], reverse=True)
        best_run = sorted_runs[0]
        worst_run = sorted_runs[-1]

        p = next(x for x in target_problems if x["id"] == pid)
        # If best run passed, use it as chosen
        if best_run["reward"] >= 0.8:
            chosen_content = best_run["response_content"]
            chosen_reasoning = best_run["reasoning_content"]
            # If worst run failed, pair them
            if worst_run["reward"] < best_run["reward"]:
                rejected_content = worst_run["response_content"]
                rejected_reasoning = worst_run["reasoning_content"]
            else:
                # Synthetic naive bad regex (demonstrating why ReDoS happens)
                rejected_content = f"`{p['canonical_ref'][:-1]}+?$`"
                rejected_reasoning = "Let us use greedy nested quantifier directly without boundary protection."

            preference_pairs.append({
                "problem_id": pid,
                "title": best_run["title"],
                "category": best_run["category"],
                "prompt": best_run["prompt"],
                "chosen": {
                    "reasoning": chosen_reasoning,
                    "response": chosen_content,
                    "regex": best_run["extracted_regex"],
                    "reward": best_run["reward"]
                },
                "rejected": {
                    "reasoning": rejected_reasoning,
                    "response": rejected_content,
                    "reward": worst_run.get("reward", 0.0)
                }
            })

    # Save outputs
    with open(output_traces_file, "w") as f:
        json.dump(all_traces, f, indent=2)

    with open(output_pairs_file, "w") as f:
        json.dump(preference_pairs, f, indent=2)

    # Print summary table
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY BY REASONING EFFORT:")
    print("="*60)
    for eff, st in effort_stats.items():
        pass_pct = (st["passed"] / st["total"] * 100) if st["total"] > 0 else 0
        redos_pct = (st["redos_safe"] / st["total"] * 100) if st["total"] > 0 else 0
        print(f"Effort [{eff.upper()}]:")
        print(f"  Accuracy (100% tests passed): {st['passed']}/{st['total']} ({pass_pct:.1f}%)")
        print(f"  ReDoS Safety Resilience:     {st['redos_safe']}/{st['total']} ({redos_pct:.1f}%)")
        print(f"  Average API Latency:         {st['avg_latency']}s")

    print(f"\nGenerated {len(all_traces)} traces -> {output_traces_file}")
    print(f"Generated {len(preference_pairs)} DPO preference pairs -> {output_pairs_file}")
    print("="*60)

    return {
        "traces": all_traces,
        "preference_pairs": preference_pairs,
        "stats": effort_stats
    }


if __name__ == "__main__":
    run_benchmark(efforts=["low", "medium"])
