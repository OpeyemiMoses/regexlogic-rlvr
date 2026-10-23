"""
RegexLogic-RLVR Arena and Beam Reasoning Explorer
Interactive Hugging Face Space for auditing Beam-1.0-501B-A23B regex reasoning,
running live deterministic verifications, and testing ReDoS attacks.
"""

import os
import json
import gradio as gr
from verifier import RegexVerifier, extract_regex_from_text
from problems import PROBLEMS, get_problem_by_id

# Load precomputed benchmark traces
TRACES_PATH = os.path.join(os.path.dirname(__file__), "beam_traces.json")
if os.path.exists(TRACES_PATH):
    with open(TRACES_PATH, "r") as f:
        TRACES = json.load(f)
else:
    TRACES = []

verifier = RegexVerifier()

# Build dropdown options
problem_choices = [f"{p['title']} [{p['id']}]" for p in PROBLEMS]


def load_problem_details(choice_str, effort_filter):
    if not choice_str:
        return "", "", "", "", "", "", ""
    pid = choice_str.split("[")[-1].rstrip("]")
    p = get_problem_by_id(pid)

    # Find matching trace
    trace = None
    for t in TRACES:
        if t.get("problem_id") == pid and t.get("effort") == effort_filter:
            trace = t
            break
    if not trace:
        for t in TRACES:
            if t.get("problem_id") == pid:
                trace = t
                break

    pos_str = "\n".join(p["positive"])
    neg_str = "\n".join(p["negative"])
    redos_str = "\n".join(p.get("redos_payloads", []))

    if trace:
        regex_val = trace.get("extracted_regex", "")
        reasoning_val = trace.get("reasoning_content", "(No reasoning recorded)")
        status_val = (
            f"### Status: {trace.get('status')} | Reward: {trace.get('reward')}\n"
            f"- **Effort:** {trace.get('effort', 'low').upper()}\n"
            f"- **Positive:** {trace.get('positive_passed')}/{trace.get('positive_total')} passed\n"
            f"- **Negative:** {trace.get('negative_passed')}/{trace.get('negative_total')} passed\n"
            f"- **ReDoS Resilience:** {'Safe' if trace.get('redos_safe') else 'VULNERABLE'}\n"
            f"- **ReDoS Latency:** {trace.get('redos_latency_ms')} ms\n"
            f"- **Diagnosis:** {trace.get('diagnosis')}"
        )
    else:
        regex_val = p["canonical_ref"]
        reasoning_val = "Canonical ground-truth reference solution."
        status_val = "### Canonical Reference Mode (Pass 100%)"

    return (
        p["prompt"],
        p["canonical_ref"],
        pos_str,
        neg_str,
        redos_str,
        regex_val,
        reasoning_val,
        status_val
    )


def run_live_verification(candidate_regex, pos_input, neg_input, redos_input):
    pos_list = [l.strip() for l in pos_input.split("\n") if l.strip()]
    neg_list = [l.strip() for l in neg_input.split("\n") if l.strip()]
    redos_list = [l.strip() for l in redos_input.split("\n") if l.strip()]

    clean_regex = extract_regex_from_text(candidate_regex) or candidate_regex.strip()

    result = verifier.verify(
        candidate_pattern=clean_regex,
        positive_cases=pos_list,
        negative_cases=neg_list,
        redos_payloads=redos_list
    )

    summary_md = (
        f"## Verification Audit Result: **{result['status']}**\n\n"
        f"| Metric | Value |\n"
        f"|---|---|\n"
        f"| **Verifiable Reward** | `{result['reward']}` / 1.0 |\n"
        f"| **Syntactically Valid** | `{'Yes' if result['compiled'] else 'NO'}` |\n"
        f"| **Positive Match Rate** | `{result['positive_passed']} / {result['positive_total']}` |\n"
        f"| **Negative Rejection Rate** | `{result['negative_passed']} / {result['negative_total']}` |\n"
        f"| **ReDoS Resilience** | `{'SAFE' if result['redos_safe'] else 'CRITICAL: VULNERABLE'}` |\n"
        f"| **ReDoS Execution Latency** | `{result['redos_max_latency_ms']} ms` |\n\n"
        f"**Audit Diagnosis:** {result['diagnosis']}"
    )

    failures_md = ""
    if result["positive_failures"]:
        failures_md += f"**Failed Positive Cases (Expected Match, Got None):**\n- " + "\n- ".join(result["positive_failures"]) + "\n\n"
    if result["negative_failures"]:
        failures_md += f"**Failed Negative Cases (Expected Rejection, Got Match):**\n- " + "\n- ".join(result["negative_failures"]) + "\n\n"
    if not result["redos_safe"]:
        failures_md += f"**ReDoS Attack Exploit Payload (Caused Timeout):**\n`{result['redos_failure_payload']}`"

    return summary_md, failures_md or "Zero failures detected. All ground-truth invariants satisfied."


theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="slate"
)

with gr.Blocks(title="RegexLogic-RLVR: Formal Automata and ReDoS Verification", theme=theme) as demo:
    gr.Markdown(
        """
        # RegexLogic-RLVR Arena: Formal Verification for Beam-1.0-501B
        ### Build with Beam Hackathon · Execution-Verified Automata and ReDoS Safety
        
        This benchmark evaluates **`reflection/Beam-1.0-501B-A23B`** on formal regular expression logic, 
        automata state transitions, and Catastrophic Backtracking (ReDoS) immunity using a **4-stage deterministic verifier**.
        
        Dataset: [`yemigraffix/beam-regexlogic-rlvr`](https://huggingface.co/datasets/yemigraffix/beam-regexlogic-rlvr)  
        Model Evaluated: [`reflection/Beam-1.0-501B-A23B`](https://huggingface.co/reflection/Beam-1.0-501B-A23B)
        """
    )

    with gr.Tab("Benchmark Problem and Trace Explorer"):
        with gr.Row():
            problem_dropdown = gr.Dropdown(
                label="Select Benchmark Problem",
                choices=problem_choices,
                value=problem_choices[0] if problem_choices else None
            )
            effort_radio = gr.Radio(
                label="Reasoning Effort Tier",
                choices=["low", "medium"],
                value="low"
            )

        prompt_box = gr.Textbox(label="Problem Specification & Constraints", lines=3, interactive=False)
        canonical_box = gr.Textbox(label="Canonical Ground-Truth Reference Pattern", lines=1, interactive=False)

        with gr.Row():
            with gr.Column():
                beam_regex_box = gr.Textbox(label="Beam Generated Regex Pattern", lines=2)
                audit_status_box = gr.Markdown(label="Audit Verdict")
            with gr.Column():
                pos_box = gr.Textbox(label="Positive Test Suite (Must Match)", lines=4)
                neg_box = gr.Textbox(label="Negative Test Suite (Must Reject)", lines=4)
                redos_box = gr.Textbox(label="ReDoS Attack Payloads (Tests Backtracking)", lines=3)

        with gr.Accordion("Beam-1.0-501B Internal Chain-of-Thought (reasoning_content)", open=False):
            reasoning_box = gr.Textbox(label="Unedited Reasoning Trace from Beam", lines=12, interactive=False)

        verify_btn = gr.Button("Re-Verify Candidate Pattern with Deterministic Engine", variant="primary")
        with gr.Row():
            live_result_md = gr.Markdown()
            failures_box = gr.Markdown()

        problem_dropdown.change(
            fn=load_problem_details,
            inputs=[problem_dropdown, effort_radio],
            outputs=[prompt_box, canonical_box, pos_box, neg_box, redos_box, beam_regex_box, reasoning_box, audit_status_box]
        )
        effort_radio.change(
            fn=load_problem_details,
            inputs=[problem_dropdown, effort_radio],
            outputs=[prompt_box, canonical_box, pos_box, neg_box, redos_box, beam_regex_box, reasoning_box, audit_status_box]
        )
        verify_btn.click(
            fn=run_live_verification,
            inputs=[beam_regex_box, pos_box, neg_box, redos_box],
            outputs=[live_result_md, failures_box]
        )

    with gr.Tab("ReDoS Vulnerability Attack Sandbox"):
        gr.Markdown(
            """
            ### Catastrophic Backtracking Attack Simulator
            Test any regular expression against pathological input strings to determine if it scales linearly 
            $O(n)$ or explodes exponentially $O(2^n)$. The sandbox enforces a strict 80ms timeout to prevent system freezing.
            """
        )
        with gr.Row():
            with gr.Column():
                custom_pattern = gr.Textbox(
                    label="Target Regular Expression",
                    value=r"^(a+)+$",
                    lines=1
                )
                custom_evil = gr.Textbox(
                    label="Evil Payload",
                    value="a" * 28 + "!",
                    lines=1
                )
                test_redos_btn = gr.Button("Launch ReDoS Attack Test", variant="stop")
            with gr.Column():
                redos_out_md = gr.Markdown()

        def test_custom_redos(pattern, payload):
            res = verifier.verify(
                candidate_pattern=pattern.strip(),
                positive_cases=[],
                negative_cases=[],
                redos_payloads=[payload]
            )
            if res["redos_safe"]:
                return (
                    f"### Pattern Resisted Attack\n"
                    f"- **Status:** Safe\n"
                    f"- **Latency:** `{res['redos_max_latency_ms']} ms`\n"
                    f"The engine rejected or matched the payload without entering exponential backtracking."
                )
            else:
                return (
                    f"### VULNERABILITY DETECTED: Catastrophic Backtracking\n"
                    f"- **Status:** TIMEOUT / ReDoS Vulnerable\n"
                    f"- **Halt Limit:** `{res['redos_max_latency_ms']} ms` (Process Interrupted)\n"
                    f"The pattern entered an exponential state explosion on: `{payload[:40]}...`"
                )

        test_redos_btn.click(
            fn=test_custom_redos,
            inputs=[custom_pattern, custom_evil],
            outputs=[redos_out_md]
        )

    with gr.Tab("TRL GRPOTrainer and RLVR Cheatsheet"):
        gr.Markdown(
            """
            ### Train Any Model with Verifiable Regex Rewards
            Use the `yemigraffix/beam-regexlogic-rlvr` dataset and the drop-in `reward_fn.py` to train models with 
            Reinforcement Learning with Verifiable Rewards (RLVR):
            
            ```python
            from datasets import load_dataset
            from trl import GRPOTrainer, GRPOConfig
            from reward_fn import regex_reward_func

            # Load the RLVR prompts split
            dataset = load_dataset("yemigraffix/beam-regexlogic-rlvr", "rlvr_prompts", split="train")

            trainer = GRPOTrainer(
                model="your-base-model",
                reward_funcs=[regex_reward_func],
                args=GRPOConfig(
                    output_dir="./rlvr_output",
                    learning_rate=2e-5,
                    per_device_train_batch_size=4,
                    num_generations=4
                ),
                train_dataset=dataset
            )
            trainer.train()
            ```
            """
        )

if __name__ == "__main__":
    demo.launch()
