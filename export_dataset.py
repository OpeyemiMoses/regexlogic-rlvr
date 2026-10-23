"""
Hugging Face Dataset Publisher for RegexLogic-RLVR
Packages benchmark prompts, verified Beam reasoning traces, and DPO preference pairs
into a structured multi-subset Hugging Face Dataset and publishes to Hub:
Repo: yemigraffix/beam-regexlogic-rlvr
"""

import os
import json
from datasets import Dataset
from huggingface_hub import HfApi

DATASET_REPO = "yemigraffix/beam-regexlogic-rlvr"


def export_and_upload():
    print(f"Loading generated traces and preference pairs...")
    with open("beam_traces.json") as f:
        traces_data = json.load(f)

    with open("preference_pairs.json") as f:
        pairs_data = json.load(f)

    # Subset 1: Full Traces (All reasoning traces + verifier audit labels)
    df_traces = []
    for t in traces_data:
        df_traces.append({
            "problem_id": t.get("problem_id"),
            "title": t.get("title"),
            "category": t.get("category"),
            "effort": t.get("effort", "low"),
            "prompt": t.get("prompt"),
            "positive_tests": json.dumps(t.get("positive_tests", [])),
            "negative_tests": json.dumps(t.get("negative_tests", [])),
            "canonical_ref": t.get("canonical_ref", ""),
            "extracted_regex": t.get("extracted_regex", ""),
            "reasoning_content": t.get("reasoning_content", ""),
            "response_content": t.get("response_content", ""),
            "status": t.get("status", "FAIL"),
            "reward": float(t.get("reward", 0.0)),
            "positive_passed": int(t.get("positive_passed", 0)),
            "positive_total": int(t.get("positive_total", 0)),
            "negative_passed": int(t.get("negative_passed", 0)),
            "negative_total": int(t.get("negative_total", 0)),
            "redos_safe": bool(t.get("redos_safe", False)),
            "redos_latency_ms": float(t.get("redos_latency_ms", 0.0)),
            "diagnosis": t.get("diagnosis", ""),
            "latency_sec": float(t.get("latency_sec", 0.0)),
            "model": "reflection/Beam-1.0-501B-A23B"
        })
    ds_traces = Dataset.from_list(df_traces)

    # Subset 2: RLVR Prompts with Verifiable Test Specifications
    df_rlvr = []
    seen_problems = set()
    for t in traces_data:
        pid = t.get("problem_id")
        if pid not in seen_problems:
            seen_problems.add(pid)
            df_rlvr.append({
                "problem_id": pid,
                "title": t.get("title"),
                "category": t.get("category"),
                "prompt": t.get("prompt"),
                "positive_tests": json.dumps(t.get("positive_tests", [])),
                "negative_tests": json.dumps(t.get("negative_tests", [])),
                "redos_payloads": json.dumps(t.get("redos_payloads", [])),
                "canonical_ref": t.get("canonical_ref", "")
            })
    ds_rlvr = Dataset.from_list(df_rlvr)

    # Subset 3: DPO / Bradley-Terry Preference Pairs
    df_pairs = []
    for p in pairs_data:
        df_pairs.append({
            "problem_id": p.get("problem_id"),
            "title": p.get("title"),
            "category": p.get("category"),
            "prompt": p.get("prompt"),
            "chosen_response": p["chosen"].get("response", ""),
            "chosen_reasoning": p["chosen"].get("reasoning", ""),
            "chosen_regex": p["chosen"].get("regex", ""),
            "chosen_reward": float(p["chosen"].get("reward", 1.0)),
            "rejected_response": p["rejected"].get("response", ""),
            "rejected_reasoning": p["rejected"].get("reasoning", ""),
            "rejected_reward": float(p["rejected"].get("reward", 0.0))
        })
    ds_pairs = Dataset.from_list(df_pairs)

    print(f"Pushing subsets to Hugging Face Hub ({DATASET_REPO})...")

    # 1. Push full_traces
    print("Pushing 'full_traces' config...")
    ds_traces.push_to_hub(
        DATASET_REPO,
        config_name="full_traces",
        split="train",
        private=False
    )

    # 2. Push rlvr_prompts
    print("Pushing 'rlvr_prompts' config...")
    ds_rlvr.push_to_hub(
        DATASET_REPO,
        config_name="rlvr_prompts",
        split="train",
        private=False
    )

    # 3. Push preference_pairs
    print("Pushing 'preference_pairs' config...")
    ds_pairs.push_to_hub(
        DATASET_REPO,
        config_name="preference_pairs",
        split="train",
        private=False
    )

    print("All 3 dataset subsets pushed successfully!")

    # Upload auxiliary files (README.md, reward_fn.py, verifier.py, problems.py)
    api = HfApi()
    for filename in ["README.md", "reward_fn.py", "verifier.py", "problems.py"]:
        if os.path.exists(filename):
            api.upload_file(
                path_or_fileobj=filename,
                path_in_repo=filename,
                repo_id=DATASET_REPO,
                repo_type="dataset"
            )
            print(f"Uploaded {filename} to {DATASET_REPO}")


if __name__ == "__main__":
    export_and_upload()
