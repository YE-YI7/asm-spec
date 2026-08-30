#!/usr/bin/env python3
"""Deterministic bandit smoke test with an external utility oracle.

This is a mechanism test, not product evidence. Ground truth is a hidden owner
utility vector and is not defined by TOPSIS. Candidate sets change every round,
so learned policies must generalize through manifest features rather than tool
IDs. A held-out tail is evaluated without model updates.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

from asm_protocol.preferences import BayesianLinearPreferenceModel
from scorer import Preferences, ServiceVector, score_topsis


FEATURES = ("cost_benefit", "quality", "speed", "reliability")


@dataclass(frozen=True)
class Candidate:
    service_id: str
    features: dict[str, float]


def utility(candidate: Candidate, owner_weights: dict[str, float]) -> float:
    return sum(candidate.features[name] * owner_weights[name] for name in FEATURES)


def candidates_for(rng: random.Random, round_index: int, count: int = 5) -> list[Candidate]:
    return [
        Candidate(
            service_id=f"round-{round_index}/tool-{index}",
            features={name: rng.uniform(-1, 1) for name in FEATURES},
        )
        for index in range(count)
    ]


def argmax(rows: list[Candidate], score) -> Candidate:
    return sorted(rows, key=lambda row: (-score(row), row.service_id))[0]


def choose_topsis(rows: list[Candidate]) -> Candidate:
    services = [
        ServiceVector(
            service_id=row.service_id,
            display_name=row.service_id,
            taxonomy="synthetic.tool",
            cost_per_unit=(1 - row.features["cost_benefit"]) / 2,
            quality_score=(row.features["quality"] + 1) / 2,
            latency_seconds=(1 - row.features["speed"]) / 2,
            uptime=(row.features["reliability"] + 1) / 2,
        )
        for row in rows
    ]
    winner = score_topsis(
        services,
        Preferences(cost=0.25, quality=0.25, speed=0.25, reliability=0.25),
    )[0].service.service_id
    return next(row for row in rows if row.service_id == winner)


def choose_adaptive(
    rows: list[Candidate],
    model: BayesianLinearPreferenceModel,
    *,
    policy: str,
    rng: random.Random,
) -> Candidate:
    if policy == "posterior_mean":
        return argmax(rows, lambda row: model.predict(row.features)[0])
    if policy == "linucb":
        return argmax(
            rows,
            lambda row: model.predict(row.features)[0]
            + math.sqrt(max(model.predict(row.features)[1], 0.0)),
        )
    if policy == "thompson":
        weights = model.sample_weights(rng=rng)
        return argmax(rows, lambda row: sum(row.features[name] * weights[name] for name in FEATURES))
    raise ValueError(policy)


def evaluate(
    *,
    seed: int = 20260831,
    rounds: int = 300,
    holdout: int = 100,
    preference_drift: bool = False,
    reward_noise: float = 0.0,
) -> dict:
    if rounds <= holdout or holdout < 1:
        raise ValueError("rounds must be greater than holdout")
    rng = random.Random(seed)
    initial_weights = {
        "cost_benefit": 0.10,
        "quality": 0.45,
        "speed": 0.15,
        "reliability": 0.30,
    }
    changed_weights = {
        "cost_benefit": 0.55,
        "quality": 0.10,
        "speed": 0.25,
        "reliability": 0.10,
    }
    models = {
        "posterior_mean": BayesianLinearPreferenceModel(FEATURES),
        "discounted_posterior": BayesianLinearPreferenceModel(FEATURES, forgetting_factor=0.97),
        "linucb": BayesianLinearPreferenceModel(FEATURES),
        "thompson": BayesianLinearPreferenceModel(FEATURES),
    }
    rows_by_round = [candidates_for(rng, index) for index in range(rounds)]
    metrics = {
        policy: {"regret": 0.0, "correct": 0}
        for policy in ("cheapest", "topsis", *models)
    }
    train_until = rounds - holdout
    drift_at = train_until // 2
    for index, rows in enumerate(rows_by_round):
        owner_weights = (
            changed_weights if preference_drift and index >= drift_at else initial_weights
        )
        oracle = argmax(rows, lambda row: utility(row, owner_weights))
        oracle_utility = utility(oracle, owner_weights)
        choices = {
            "cheapest": argmax(rows, lambda row: row.features["cost_benefit"]),
            "topsis": choose_topsis(rows),
        }
        for offset, (policy, model) in enumerate(models.items()):
            choices[policy] = choose_adaptive(
                rows,
                model,
                policy="posterior_mean" if policy == "discounted_posterior" else policy,
                rng=random.Random(seed + index * 10 + offset),
            )
        if index >= train_until:
            for policy, chosen in choices.items():
                metrics[policy]["regret"] += oracle_utility - utility(chosen, owner_weights)
                metrics[policy]["correct"] += int(chosen.service_id == oracle.service_id)
        else:
            for policy, model in models.items():
                chosen = choices[policy]
                # Bandit feedback: only the selected action's realized outcome.
                observed = utility(chosen, owner_weights) + rng.gauss(0.0, reward_noise)
                model.update(chosen.features, max(-1.0, min(observed, 1.0)))

    return {
        "status": "synthetic_mechanism_test_not_product_evidence",
        "seed": seed,
        "rounds": rounds,
        "train_rounds": train_until,
        "holdout_rounds": holdout,
        "preference_drift": preference_drift,
        "reward_noise": reward_noise,
        "initial_owner_weights": initial_weights,
        "changed_owner_weights": changed_weights if preference_drift else None,
        "results": {
            policy: {
                "mean_holdout_regret": round(value["regret"] / holdout, 6),
                "holdout_top1_accuracy": round(value["correct"] / holdout, 6),
            }
            for policy, value in sorted(metrics.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--holdout", type=int, default=100)
    parser.add_argument("--preference-drift", action="store_true")
    parser.add_argument("--reward-noise", type=float, default=0.0)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = evaluate(
        seed=args.seed,
        rounds=args.rounds,
        holdout=args.holdout,
        preference_drift=args.preference_drift,
        reward_noise=args.reward_noise,
    )
    text = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
