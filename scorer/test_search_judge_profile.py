from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_judge_prompt_commitment_and_unfrozen_boundaries() -> None:
    directory = ROOT / "experiments" / "search_evaluation"
    profile = json.loads((directory / "judge-profile.v0.1.json").read_text(encoding="utf-8"))
    model_step = next(step for step in profile["steps"] if step["method"] == "blinded_model_assisted")
    prompt_bytes = (directory / model_step["prompt_file"]).read_bytes()

    assert model_step["prompt_digest"] == "sha256:" + hashlib.sha256(prompt_bytes).hexdigest()
    assert profile["status"] == "draft_unfrozen"
    assert model_step["model"] is None
    assert model_step["model_version"] is None
    assert profile["gold_input"] == ["benchmark_answer"]
    assert profile["provider_identity_visible"] is False
