"""Unit tests for scoring/pure.py — zero Django/DB imports, so these run
with plain pytest and no database (mirrors the Next.js version's Vitest
suite for score-service/rating-service/ranking-service/badge-service)."""

from scoring.pure import (
    MIN_RESOLVED_FOR_HIGH_RATING,
    RankableUser,
    StatsSnapshot,
    build_ranking,
    calculate_accuracy,
    calculate_rating,
    calculate_score,
    calculate_streak,
    determine_rank_badges,
    determine_volume_badges,
    did_beat_ai,
    find_user_rank,
)


class TestCalculateScore:
    def test_correct_pick_awards_10_points(self):
        result = calculate_score("YES", "YES")
        assert result.is_correct is True
        assert result.points == 10

    def test_incorrect_pick_awards_0_points(self):
        result = calculate_score("YES", "NO")
        assert result.is_correct is False
        assert result.points == 0

    def test_confidence_does_not_affect_mvp_scoring(self):
        assert calculate_score("YES", "YES", confidence=55).points == 10
        assert calculate_score("YES", "YES", confidence=99).points == 10


class TestCalculateStreak:
    def test_correct_increments_streak(self):
        result = calculate_streak(previous_streak=3, previous_best_streak=5, is_correct=True)
        assert result.current_streak == 4
        assert result.best_streak == 5

    def test_incorrect_resets_streak_to_zero(self):
        result = calculate_streak(previous_streak=7, previous_best_streak=7, is_correct=False)
        assert result.current_streak == 0
        assert result.best_streak == 7

    def test_new_streak_beats_previous_best(self):
        result = calculate_streak(previous_streak=4, previous_best_streak=4, is_correct=True)
        assert result.current_streak == 5
        assert result.best_streak == 5


class TestCalculateAccuracy:
    def test_zero_resolved_is_zero_not_divide_by_zero(self):
        assert calculate_accuracy(0, 0) == 0.0

    def test_half_correct(self):
        assert calculate_accuracy(5, 10) == 0.5

    def test_all_correct(self):
        assert calculate_accuracy(10, 10) == 1.0


class TestDidBeatAi:
    def test_user_correct_ai_wrong_is_beat(self):
        assert did_beat_ai("NO", "NO", ai_yes_probability=0.8) is True

    def test_user_correct_ai_also_correct_is_not_beat(self):
        assert did_beat_ai("YES", "YES", ai_yes_probability=0.8) is False

    def test_user_wrong_is_never_a_beat(self):
        assert did_beat_ai("YES", "NO", ai_yes_probability=0.2) is False

    def test_ai_pick_boundary_at_exactly_half(self):
        # ai_yes_probability == 0.5 counts as an AI "YES" pick.
        assert did_beat_ai("NO", "NO", ai_yes_probability=0.5) is True


class TestCalculateRating:
    def test_zero_resolved_defaults_to_c(self):
        assert calculate_rating(accuracy=0.9, resolved_predictions=0) == "C"

    def test_high_accuracy_without_volume_is_capped_below_a(self):
        assert calculate_rating(accuracy=0.9, resolved_predictions=MIN_RESOLVED_FOR_HIGH_RATING - 1) == "B"

    def test_a_plus_requires_volume_and_accuracy(self):
        assert calculate_rating(accuracy=0.8, resolved_predictions=MIN_RESOLVED_FOR_HIGH_RATING) == "A+"

    def test_a_requires_volume(self):
        assert calculate_rating(accuracy=0.70, resolved_predictions=MIN_RESOLVED_FOR_HIGH_RATING) == "A"

    def test_low_accuracy_is_d(self):
        assert calculate_rating(accuracy=0.1, resolved_predictions=20) == "D"


class TestBuildRanking:
    def _user(self, uid, score, accuracy=0.5, total=10, streak=0):
        return RankableUser(user_id=uid, prediction_score=score, accuracy=accuracy, total_predictions=total, current_streak=streak)

    def test_excludes_users_below_minimum_predictions(self):
        users = [self._user(1, 100, total=3), self._user(2, 50, total=10)]
        ranked = build_ranking(users, min_predictions=10)
        assert [u.user_id for u in ranked] == [2]

    def test_sorts_by_score_desc_then_accuracy_then_volume(self):
        users = [
            self._user(1, 100, accuracy=0.6, total=10),
            self._user(2, 100, accuracy=0.8, total=10),
            self._user(3, 90, accuracy=0.9, total=10),
        ]
        ranked = build_ranking(users, min_predictions=10)
        assert [u.user_id for u in ranked] == [2, 1, 3]
        assert [u.rank for u in ranked] == [1, 2, 3]

    def test_find_user_rank(self):
        users = [self._user(1, 100, total=10), self._user(2, 50, total=10)]
        ranked = build_ranking(users, min_predictions=10)
        assert find_user_rank(ranked, 2) == 2
        assert find_user_rank(ranked, 999) is None


class TestBadges:
    def test_first_prediction_badge_at_one(self):
        codes = determine_volume_badges(StatsSnapshot(total_predictions=1))
        assert "FIRST_PREDICTION" in codes
        assert "PREDICTIONS_10" not in codes

    def test_multiple_volume_thresholds_can_fire_together(self):
        codes = determine_volume_badges(StatsSnapshot(total_predictions=100))
        assert {"FIRST_PREDICTION", "PREDICTIONS_10", "PREDICTIONS_50", "PREDICTIONS_100"} <= set(codes)

    def test_streak_and_ai_killer_badges(self):
        codes = determine_volume_badges(StatsSnapshot(total_predictions=1, current_streak=10, ai_beat_count=1))
        assert "STREAK_10" in codes
        assert "AI_KILLER" in codes

    def test_no_badges_for_zero_activity(self):
        assert determine_volume_badges(StatsSnapshot()) == []

    def test_rank_badges_none_for_unranked(self):
        assert determine_rank_badges(None) == []

    def test_rank_badges_top_1_implies_top_10_and_top_100(self):
        codes = determine_rank_badges(1)
        assert set(codes) == {"TOP_100", "TOP_10", "TOP_1"}

    def test_rank_badges_top_50_only_top_100(self):
        assert determine_rank_badges(50) == ["TOP_100"]

    def test_rank_badges_below_top_100_is_empty(self):
        assert determine_rank_badges(500) == []
