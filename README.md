---
license: apache-2.0
task_categories:
  - reinforcement-learning
  - text-generation
language:
  - en
tags:
  - rlvr
  - grpo
  - regex
  - automata
  - redos
  - formal-verification
  - reasoning
  - beam
  - dpo
size_categories:
  - n<1K
pretty_name: "RegexLogic-RLVR: Formal Automata and ReDoS Verification for Beam"
configs:
  - config_name: full_traces
    data_files:
      - split: train
        path: "full_traces/train*"
  - config_name: rlvr_prompts
    data_files:
      - split: train
        path: "rlvr_prompts/train*"
  - config_name: preference_pairs
    data_files:
      - split: train
        path: "preference_pairs/train*"
---

# RegexLogic-RLVR: Formal Automata and ReDoS Verification for Beam

RegexLogic-RLVR is an execution-verified reasoning benchmark and synthetic dataset evaluating **`reflection/Beam-1.0-501B-A23B`** on formal regular expression synthesis, automata state constraints, and Catastrophic Backtracking (ReDoS) immunity.

Unlike subjective LLM-as-a-judge benchmarks, every model output in this dataset is evaluated by a **4-stage deterministic Python verifier**:
1. **Compilation Check**: Syntactic validity in Python's standard `re` engine.
2. **Positive Test Suite**: Full acceptance of boundary and complex valid instances.
3. **Negative Test Suite**: Strict rejection of edge-case and invalid instances.
4. **ReDoS Attack Simulation**: Live execution against exponential backtracking payloads (such as $O(2^n)$ nested quantifiers) under strict wall-clock process timers ($t \le 80\text{ms}$).

---

## Dataset Splits

1. **`full_traces`**: All attempts by `reflection/Beam-1.0-501B-A23B` across reasoning effort tiers (`low` vs. `medium`), containing:
   - Full unedited `reasoning_content` (internal chain of thought from the model)
   - Extracted candidate regex
   - Stage-by-stage verification metrics (positive pass rate, negative pass rate, ReDoS safety, latency)
   - Diagnostic failure reports
2. **`rlvr_prompts`**: RLVR-ready prompts with ground-truth test specifications, designed for training with Hugging Face TRL (`GRPOTrainer`).
3. **`preference_pairs`**: Curated DPO / Bradley-Terry preference pairs pairing high-reward, ReDoS-safe patterns against vulnerable or failing generations.

---

## Key Empirical Findings on Beam-1.0-501B

- **The `reasoning_effort` Parameter**: At default or unconstrained effort, Beam can generate over 16,000 characters of deep mathematical reasoning. Setting `reasoning_effort="low"` or `"medium"` keeps reasoning disciplined and produces high-accuracy solutions in 2 to 4 seconds without truncation.
- **ReDoS Awareness**: When explicitly prompted to avoid catastrophic backtracking, Beam successfully uses unrolled loops (e.g. `\w+(?:\s+\w+)*` instead of naive `(\w+\s*)+`) and atomic grouping logic, resisting evil payload attacks that would otherwise hang standard regex engines for >100 seconds.
- **Lookaround Limitations**: Beam occasionally assumes unlimited look-behind widths (common in PCRE or .NET), requiring RLVR rewards to guide it toward fixed-width look-behinds supported by Python's native `re` module.

---

## Benchmark Results

- **Low Effort (`low`)**:
  - Accuracy (100% tests passed): **81.2% (13/16)**
  - ReDoS Safety Resilience: **100.0% (16/16)**
  - Average Latency: **4.00s**
- **Medium Effort (`medium`)**:
  - Accuracy (100% tests passed): **62.5% (10/16)**
  - ReDoS Safety Resilience: **93.8% (15/16)**
  - Average Latency: **4.53s**

---

## Quickstart

### 1. Load the Dataset with `datasets`
```python
from datasets import load_dataset

# Load full verified traces
dataset = load_dataset("yemigraffix/beam-regexlogic-rlvr", "full_traces", split="train")
print(dataset[0]["reasoning_content"])
print(dataset[0]["extracted_regex"])
print("Verifier Reward:", dataset[0]["reward"])
```

### 2. Drop-in RLVR Training with TRL `GRPOTrainer`
This repository includes a standalone `reward_fn.py` compatible with Hugging Face TRL:

```python
from datasets import load_dataset
from trl import GRPOTrainer, GRPOConfig
from reward_fn import regex_reward_func

dataset = load_dataset("yemigraffix/beam-regexlogic-rlvr", "rlvr_prompts", split="train")

trainer = GRPOTrainer(
    model="your-base-model",
    reward_funcs=[regex_reward_func],
    args=GRPOConfig(
        output_dir="./output",
        learning_rate=1e-5,
        per_device_train_batch_size=4
    ),
    train_dataset=dataset
)

trainer.train()
```

---

## Benchmark Problem Categories

| Category | Description | Key Focus |
|---|---|---|
| **`redos_defense`** | Refactoring vulnerable expressions (emails, slugs, CSV) | $O(n)$ linear matching time; eliminating exponential backtracking |
| **`automata_theory`** | Binary divisibility (DFA modulo 3), even/odd parity | State-transition correctness and formal language equivalence |
| **`lookaround_logic`** | Complex negative assertions, multi-rule password constraints | Zero-width assertions without unintended prefix/suffix consumption |
| **`structured_data`** | SemVer 2.0.0, strict IPv4 (0-255 octets), ISO-8601, Cron | Multi-token numerical range and calendar constraints |
| **`syntax_parsing`** | Escaped JSON strings, balanced markdown links | Escape sequences and non-greedy delimiters |

---

## Ground-Truth Verifier Code

The complete deterministic verification harness is open source in [`verifier.py`](./verifier.py). Test it locally:

```bash
python verifier.py
```

Built for the **Build with Beam Hackathon** organized by Reflection AI and Hugging Face.
