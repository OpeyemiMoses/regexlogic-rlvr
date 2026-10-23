"""
RegexLogic Verifiable Reward Function for Hugging Face TRL (GRPOTrainer / RLVR)
Drop-in reward function for training models with Reinforcement Learning with Verifiable Rewards.

Usage with TRL:
```python
from trl import GRPOTrainer, GRPOConfig
from reward_fn import regex_reward_func

trainer = GRPOTrainer(
    model="your-model",
    reward_funcs=[regex_reward_func],
    ...
)
```
"""

from typing import List, Dict, Any, Union
from verifier import RegexVerifier, extract_regex_from_text


class RegexRewardEngine:
    def __init__(self, timeout_sec: float = 0.08):
        self.verifier = RegexVerifier(timeout_per_match=timeout_sec)

    def compute_reward(self, completion: str, ground_truth: Dict[str, Any]) -> float:
        """Computes verifiable reward (0.0 to 1.0) for a single model completion."""
        extracted_pattern = extract_regex_from_text(completion)
        if not extracted_pattern:
            return 0.0

        verification = self.verifier.verify(
            candidate_pattern=extracted_pattern,
            positive_cases=ground_truth.get("positive", []),
            negative_cases=ground_truth.get("negative", []),
            redos_payloads=ground_truth.get("redos_payloads", [])
        )
        return float(verification["reward"])


# Global engine instance
_engine = RegexRewardEngine()


def regex_reward_func(
    prompts: List[Union[str, List[Dict[str, str]]]],
    completions: List[Union[str, List[Dict[str, str]]]],
    **kwargs
) -> List[float]:
    """
    TRL-compatible reward function.
    Matches each completion against problem specifications in kwargs or prompt metadata.
    """
    rewards = []
    # If problem metadata is passed in kwargs (e.g. from dataset columns)
    problem_specs = kwargs.get("problem_spec", [])

    for idx, comp in enumerate(completions):
        # Extract text from completion (either raw str or list of message dicts)
        if isinstance(comp, list) and len(comp) > 0 and isinstance(comp[-1], dict):
            comp_text = comp[-1].get("content", "")
        else:
            comp_text = str(comp)

        spec = problem_specs[idx] if idx < len(problem_specs) else {}
        reward = _engine.compute_reward(comp_text, spec)
        rewards.append(reward)

    return rewards


if __name__ == "__main__":
    # Test reward function
    sample_spec = {
        "positive": ["hello world!", "test!"],
        "negative": ["hello", "bad!"],
        "redos_payloads": ["a " * 30 + "!"]
    }
    sample_comp = "Here is the pattern: `^\\w+(?:\\s+\\w+)*!$`"
    r = _engine.compute_reward(sample_comp, sample_spec)
    print("Sample TRL reward score:", r)
