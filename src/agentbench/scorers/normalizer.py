"""Score normalization utilities."""

from __future__ import annotations


class ScoreNormalizer:
    """Normalizes raw scores to a standard 0-100 scale.

    Different categories may have different scoring scales or distributions.
    The normalizer applies category-specific transformations to produce
    comparable scores across categories.
    """

    def __init__(self) -> None:
        self._category_params: dict[str, dict[str, float]] = {
            "prompt_injection": {"scale": 1.0, "offset": 0.0},
            "tool_poisoning": {"scale": 1.0, "offset": 0.0},
            "ssrf": {"scale": 1.0, "offset": 0.0},
            "data_exfiltration": {"scale": 1.0, "offset": 0.0},
            "jailbreak": {"scale": 1.0, "offset": 0.0},
            "memory_attacks": {"scale": 1.0, "offset": 0.0},
            "multi_agent": {"scale": 1.0, "offset": 0.0},
        }

    def normalize(self, raw_score: float, category: str = "") -> float:
        """Normalize a raw score to the 0-100 scale.

        Args:
            raw_score: Raw score value (expected 0-100 range).
            category: Optional category name for category-specific normalization.

        Returns:
            Normalized score between 0 and 100.
        """
        params = self._category_params.get(category, {"scale": 1.0, "offset": 0.0})
        normalized = raw_score * params["scale"] + params["offset"]
        return max(0.0, min(100.0, normalized))

    def register_category(self, category: str, scale: float = 1.0, offset: float = 0.0) -> None:
        """Register or update normalization parameters for a category.

        Args:
            category: Category name.
            scale: Multiplicative scale factor.
            offset: Additive offset.
        """
        self._category_params[category] = {"scale": scale, "offset": offset}

    def denormalize(self, normalized_score: float, category: str = "") -> float:
        """Reverse normalization to recover raw score.

        Args:
            normalized_score: Normalized score (0-100).
            category: Category name for reverse transformation.

        Returns:
            Raw score estimate.
        """
        params = self._category_params.get(category, {"scale": 1.0, "offset": 0.0})
        if params["scale"] == 0:
            return 0.0
        raw = (normalized_score - params["offset"]) / params["scale"]
        return max(0.0, min(100.0, raw))
