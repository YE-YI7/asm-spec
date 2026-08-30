from experiments.adaptive_selection_replay import evaluate


def test_adaptive_replay_is_external_to_topsis_and_learns_on_unseen_tools():
    result = evaluate(seed=20260831, rounds=180, holdout=60)
    assert result["status"] == "synthetic_mechanism_test_not_product_evidence"
    rows = result["results"]
    assert rows["posterior_mean"]["mean_holdout_regret"] < rows["topsis"]["mean_holdout_regret"]
    assert rows["posterior_mean"]["holdout_top1_accuracy"] > rows["cheapest"]["holdout_top1_accuracy"]


def test_discounted_model_handles_preference_drift_better_than_static_history():
    result = evaluate(
        seed=20260831,
        rounds=240,
        holdout=60,
        preference_drift=True,
        reward_noise=0.05,
    )
    rows = result["results"]
    assert rows["discounted_posterior"]["mean_holdout_regret"] < rows["posterior_mean"]["mean_holdout_regret"]
