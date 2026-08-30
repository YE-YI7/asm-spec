from __future__ import annotations

import math
import random
import stat

import pytest

from asm_protocol.preferences import (
    BayesianLinearPreferenceModel,
    PreferenceLedger,
    model_from_ledger,
)


def test_unseen_owner_has_zero_mean_and_explicit_uncertainty():
    model = BayesianLinearPreferenceModel(("cost_benefit", "privacy"))
    mean, variance = model.predict({"cost_benefit": 1.0})
    assert mean == 0.0
    assert variance == pytest.approx(1.0)
    assert model.observations == 0


def test_pairwise_choices_update_owner_posterior_without_raw_prompt(tmp_path):
    ledger = PreferenceLedger(tmp_path / "owner.jsonl")
    ledger.record_pairwise(
        chosen_service_id="local/private",
        chosen_features={"cost_benefit": 0.2, "privacy": 1.0},
        rejected_service_id="cloud/cheap",
        rejected_features={"cost_benefit": 1.0, "privacy": 0.0},
        context_tags=("research",),
    )
    model = model_from_ledger(ledger, feature_names=("cost_benefit", "privacy"))
    private_mean, _ = model.predict({"cost_benefit": 0.2, "privacy": 1.0})
    cheap_mean, _ = model.predict({"cost_benefit": 1.0, "privacy": 0.0})
    assert private_mean > cheap_mean
    raw = ledger.path.read_text()
    assert "raw_prompt" not in raw
    assert model.digest().startswith("sha256:")
    assert stat.S_IMODE(ledger.path.stat().st_mode) == 0o600


def test_pairwise_extremes_are_scaled_into_the_model_feature_range(tmp_path):
    ledger = PreferenceLedger(tmp_path / "owner.jsonl")
    event = ledger.record_pairwise(
        chosen_service_id="private",
        chosen_features={"privacy": 1.0},
        rejected_service_id="tracking",
        rejected_features={"privacy": -1.0},
    )
    assert event.feature_delta == {"privacy": 1.0}


def test_context_tags_reject_raw_prompt_text(tmp_path):
    ledger = PreferenceLedger(tmp_path / "owner.jsonl")
    with pytest.raises(ValueError, match="not raw prompt text"):
        ledger.record_outcome(
            service_id="example/tool",
            features={"privacy": 1.0},
            reward=1.0,
            context_tags=("please use my private medical history",),
        )


def test_corrupt_or_duplicate_ledger_fails_closed(tmp_path):
    ledger = PreferenceLedger(tmp_path / "owner.jsonl")
    event = ledger.record_outcome(
        service_id="example/tool",
        features={"privacy": 1.0},
        reward=1.0,
    )
    with ledger.path.open("a", encoding="utf-8") as handle:
        handle.write(ledger.path.read_text(encoding="utf-8").splitlines()[0] + "\n")
    with pytest.raises(ValueError, match="duplicate preference event_id"):
        ledger.events()


def test_outcomes_can_reverse_an_early_preference(tmp_path):
    ledger = PreferenceLedger(tmp_path / "owner.jsonl")
    features = {"cost_benefit": 1.0, "quality": 0.0}
    ledger.record_outcome(service_id="cheap", features=features, reward=-1.0)
    ledger.record_outcome(service_id="cheap", features=features, reward=-1.0)
    model = model_from_ledger(ledger, feature_names=("cost_benefit", "quality"))
    mean, variance = model.predict(features)
    assert mean < 0
    assert variance < 1


def test_sampling_uses_the_posterior_and_is_reproducible():
    model = BayesianLinearPreferenceModel(("cost_benefit",))
    model.update({"cost_benefit": 1.0}, 1.0)
    left = model.sample_weights(rng=random.Random(7))
    right = model.sample_weights(rng=random.Random(7))
    assert left == right
    assert math.isfinite(left["cost_benefit"])


def test_discounted_model_can_forget_old_owner_evidence():
    static = BayesianLinearPreferenceModel(("privacy",), forgetting_factor=1.0)
    adaptive = BayesianLinearPreferenceModel(("privacy",), forgetting_factor=0.5)
    for model in (static, adaptive):
        for _ in range(8):
            model.update({"privacy": 1.0}, 1.0)
        for _ in range(4):
            model.update({"privacy": 1.0}, -1.0)
    static_mean, _ = static.predict({"privacy": 1.0})
    adaptive_mean, _ = adaptive.predict({"privacy": 1.0})
    assert static_mean > 0
    assert adaptive_mean < 0


def test_unknown_feature_and_out_of_range_reward_fail_closed(tmp_path):
    model = BayesianLinearPreferenceModel(("cost_benefit",))
    with pytest.raises(ValueError, match="unknown preference features"):
        model.predict({"privacy": 1.0})
    ledger = PreferenceLedger(tmp_path / "owner.jsonl")
    with pytest.raises(ValueError, match="reward"):
        ledger.record_outcome(
            service_id="bad",
            features={"cost_benefit": 1.0},
            reward=2.0,
        )
