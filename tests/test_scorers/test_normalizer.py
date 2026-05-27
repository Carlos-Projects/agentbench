"""Tests for ScoreNormalizer."""


from agentbench.scorers.normalizer import ScoreNormalizer


class TestScoreNormalizer:
    def setup_method(self) -> None:
        self.normalizer = ScoreNormalizer()

    def test_normalize_default(self) -> None:
        assert self.normalizer.normalize(85.0) == 85.0

    def test_normalize_clamps_low(self) -> None:
        assert self.normalizer.normalize(-10.0) == 0.0

    def test_normalize_clamps_high(self) -> None:
        assert self.normalizer.normalize(150.0) == 100.0

    def test_normalize_boundary_low(self) -> None:
        assert self.normalizer.normalize(0.0) == 0.0

    def test_normalize_boundary_high(self) -> None:
        assert self.normalizer.normalize(100.0) == 100.0

    def test_register_category(self) -> None:
        self.normalizer.register_category("custom", scale=0.5, offset=10.0)
        assert self.normalizer.normalize(80.0, "custom") == 50.0

    def test_denormalize(self) -> None:
        raw = self.normalizer.denormalize(75.0)
        assert raw == 75.0

    def test_denormalize_with_params(self) -> None:
        self.normalizer.register_category("custom", scale=0.5, offset=10.0)
        raw = self.normalizer.denormalize(50.0, "custom")
        assert raw == 80.0

    def test_denormalize_zero_scale(self) -> None:
        self.normalizer.register_category("custom", scale=0.0)
        assert self.normalizer.denormalize(50.0, "custom") == 0.0

    def test_unknown_category(self) -> None:
        assert self.normalizer.normalize(75.0, "unknown") == 75.0
