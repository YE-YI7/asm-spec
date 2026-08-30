"""Local owner-preference evidence and Bayesian linear utility learning.

The ledger stores normalized decision evidence, not raw user prompts. The
Gaussian observation model is a small online-learning baseline; it exposes its
uncertainty instead of pretending that early owner evidence is ground truth.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


DEFAULT_FEATURES = (
    "cost_benefit",
    "quality",
    "speed",
    "reliability",
    "privacy",
    "familiarity",
    "low_human_effort",
    "observed_success",
)
_CONTEXT_TAG_RE = re.compile(r"^[a-z][a-z0-9_.:-]{0,63}$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _finite_unit(value: float, *, field: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not -1.0 <= number <= 1.0:
        raise ValueError(f"{field} must be finite and in [-1, 1]")
    return number


def _vector(features: Mapping[str, float], names: Sequence[str]) -> list[float]:
    unknown = set(features) - set(names)
    if unknown:
        raise ValueError(f"unknown preference features: {sorted(unknown)}")
    return [_finite_unit(features.get(name, 0.0), field=name) for name in names]


def _context_tags(values: Iterable[str]) -> tuple[str, ...]:
    tags = tuple(sorted(set(str(value) for value in values)))
    if len(tags) > 16:
        raise ValueError("context_tags must contain at most 16 identifiers")
    invalid = [tag for tag in tags if not _CONTEXT_TAG_RE.fullmatch(tag)]
    if invalid:
        raise ValueError(
            "context_tags must be short machine identifiers, not raw prompt text: "
            f"{invalid}"
        )
    return tags


@dataclass(frozen=True)
class PreferenceEvent:
    """Privacy-bounded evidence used to update one owner model."""

    event_id: str
    occurred_at: str
    kind: str
    chosen_service_id: str
    feature_delta: dict[str, float]
    reward: float
    alternative_service_id: str | None = None
    context_tags: tuple[str, ...] = ()
    reversible: bool = True
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if self.kind not in {"pairwise_choice", "outcome"}:
            raise ValueError("preference event kind must be pairwise_choice or outcome")
        if not self.chosen_service_id:
            raise ValueError("chosen_service_id is required")
        _finite_unit(self.reward, field="reward")
        for name, value in self.feature_delta.items():
            _finite_unit(value, field=f"feature_delta.{name}")
        _context_tags(self.context_tags)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["context_tags"] = list(self.context_tags)
        return value

    @classmethod
    def from_dict(cls, value: Mapping) -> "PreferenceEvent":
        return cls(
            event_id=str(value["event_id"]),
            occurred_at=str(value["occurred_at"]),
            kind=str(value["kind"]),
            chosen_service_id=str(value["chosen_service_id"]),
            alternative_service_id=value.get("alternative_service_id"),
            feature_delta={str(k): float(v) for k, v in dict(value["feature_delta"]).items()},
            reward=float(value["reward"]),
            context_tags=tuple(str(tag) for tag in value.get("context_tags") or ()),
            reversible=bool(value.get("reversible", True)),
            schema_version=str(value.get("schema_version", "0.1")),
        )


class PreferenceLedger:
    """Append-only JSONL evidence stored in an owner-controlled local path."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()

    def append(self, event: PreferenceEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(
            self.path,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            0o600,
        )
        try:
            os.chmod(self.path, 0o600)
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                descriptor = -1
                handle.write(json.dumps(event.to_dict(), sort_keys=True, ensure_ascii=False) + "\n")
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def events(self) -> list[PreferenceEvent]:
        if not self.path.exists():
            return []
        result = []
        event_ids: set[str] = set()
        with self.path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    event = PreferenceEvent.from_dict(json.loads(line))
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid preference ledger line {line_number}: {exc}") from exc
                if event.event_id in event_ids:
                    raise ValueError(f"duplicate preference event_id at line {line_number}")
                event_ids.add(event.event_id)
                result.append(event)
        return result

    def record_pairwise(
        self,
        *,
        chosen_service_id: str,
        chosen_features: Mapping[str, float],
        rejected_service_id: str,
        rejected_features: Mapping[str, float],
        context_tags: Iterable[str] = (),
        reversible: bool = True,
    ) -> PreferenceEvent:
        names = set(chosen_features) | set(rejected_features)
        delta = {
            name: _finite_unit(
                (
                    float(chosen_features.get(name, 0.0))
                    - float(rejected_features.get(name, 0.0))
                )
                / 2.0,
                field=name,
            )
            for name in sorted(names)
        }
        event = PreferenceEvent(
            event_id=str(uuid.uuid4()),
            occurred_at=_now(),
            kind="pairwise_choice",
            chosen_service_id=chosen_service_id,
            alternative_service_id=rejected_service_id,
            feature_delta=delta,
            reward=1.0,
            context_tags=_context_tags(context_tags),
            reversible=reversible,
        )
        self.append(event)
        return event

    def record_outcome(
        self,
        *,
        service_id: str,
        features: Mapping[str, float],
        reward: float,
        context_tags: Iterable[str] = (),
        reversible: bool = True,
    ) -> PreferenceEvent:
        event = PreferenceEvent(
            event_id=str(uuid.uuid4()),
            occurred_at=_now(),
            kind="outcome",
            chosen_service_id=service_id,
            feature_delta={name: _finite_unit(value, field=name) for name, value in features.items()},
            reward=_finite_unit(reward, field="reward"),
            context_tags=_context_tags(context_tags),
            reversible=reversible,
        )
        self.append(event)
        return event


def _identity(size: int, scale: float) -> list[list[float]]:
    return [[scale if i == j else 0.0 for j in range(size)] for i in range(size)]


def _invert(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    size = len(matrix)
    augmented = [list(row) + identity for row, identity in zip(matrix, _identity(size, 1.0))]
    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            raise ValueError("preference posterior matrix is singular")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        divisor = augmented[col][col]
        augmented[col] = [value / divisor for value in augmented[col]]
        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[col])
            ]
    return [row[size:] for row in augmented]


def _mat_vec(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> list[float]:
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _cholesky(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    size = len(matrix)
    lower = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(i + 1):
            subtotal = sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                diagonal = matrix[i][i] - subtotal
                if diagonal < -1e-10:
                    raise ValueError("preference posterior covariance is not positive semidefinite")
                lower[i][j] = math.sqrt(max(diagonal, 0.0))
            elif lower[j][j] > 1e-12:
                lower[i][j] = (matrix[i][j] - subtotal) / lower[j][j]
    return lower


class BayesianLinearPreferenceModel:
    """Bayesian ridge sufficient statistics for mean/UCB/Thompson policies."""

    def __init__(
        self,
        feature_names: Sequence[str] = DEFAULT_FEATURES,
        *,
        prior_precision: float = 1.0,
        observation_precision: float = 1.0,
        forgetting_factor: float = 1.0,
    ) -> None:
        if not feature_names or len(set(feature_names)) != len(feature_names):
            raise ValueError("feature_names must be unique and non-empty")
        if prior_precision <= 0 or observation_precision <= 0:
            raise ValueError("model precisions must be positive")
        if not 0 < forgetting_factor <= 1:
            raise ValueError("forgetting_factor must be in (0, 1]")
        self.feature_names = tuple(feature_names)
        self.prior_precision = float(prior_precision)
        self.observation_precision = float(observation_precision)
        self.forgetting_factor = float(forgetting_factor)
        self.precision = _identity(len(self.feature_names), self.prior_precision)
        self.evidence = [0.0] * len(self.feature_names)
        self.observations = 0

    def update(self, features: Mapping[str, float], reward: float) -> None:
        x = _vector(features, self.feature_names)
        y = _finite_unit(reward, field="reward")
        beta = self.observation_precision
        if self.observations and self.forgetting_factor < 1.0:
            gamma = self.forgetting_factor
            for i in range(len(x)):
                self.evidence[i] *= gamma
                for j in range(len(x)):
                    prior = self.prior_precision if i == j else 0.0
                    self.precision[i][j] = prior + gamma * (self.precision[i][j] - prior)
        for i in range(len(x)):
            self.evidence[i] += beta * x[i] * y
            for j in range(len(x)):
                self.precision[i][j] += beta * x[i] * x[j]
        self.observations += 1

    def fit(self, events: Iterable[PreferenceEvent]) -> "BayesianLinearPreferenceModel":
        for event in events:
            self.update(event.feature_delta, event.reward)
        return self

    @property
    def covariance(self) -> list[list[float]]:
        return _invert(self.precision)

    @property
    def mean(self) -> dict[str, float]:
        vector = _mat_vec(self.covariance, self.evidence)
        return dict(zip(self.feature_names, vector))

    def predict(self, features: Mapping[str, float]) -> tuple[float, float]:
        x = _vector(features, self.feature_names)
        covariance = self.covariance
        mean_vector = _mat_vec(covariance, self.evidence)
        mean = _dot(x, mean_vector)
        variance = max(_dot(x, _mat_vec(covariance, x)), 0.0)
        return mean, variance

    def sample_weights(self, *, rng: random.Random) -> dict[str, float]:
        covariance = self.covariance
        mean = _mat_vec(covariance, self.evidence)
        lower = _cholesky(covariance)
        normal = [rng.gauss(0.0, 1.0) for _ in self.feature_names]
        draw = [mean[i] + sum(lower[i][j] * normal[j] for j in range(i + 1)) for i in range(len(mean))]
        return dict(zip(self.feature_names, draw))

    def digest(self) -> str:
        payload = json.dumps(
            {
                "feature_names": self.feature_names,
                "prior_precision": self.prior_precision,
                "observation_precision": self.observation_precision,
                "forgetting_factor": self.forgetting_factor,
                "precision": self.precision,
                "evidence": self.evidence,
                "observations": self.observations,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def model_from_ledger(
    ledger: PreferenceLedger,
    *,
    feature_names: Sequence[str] = DEFAULT_FEATURES,
) -> BayesianLinearPreferenceModel:
    return BayesianLinearPreferenceModel(feature_names).fit(ledger.events())


__all__ = [
    "BayesianLinearPreferenceModel",
    "DEFAULT_FEATURES",
    "PreferenceEvent",
    "PreferenceLedger",
    "model_from_ledger",
]
