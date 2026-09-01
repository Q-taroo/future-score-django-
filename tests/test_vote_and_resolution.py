"""Integration tests (real Postgres via pytest-django) for the vote +
resolution flow — mirrors the Next.js version's
tests/integration/vote-and-resolution.test.ts. Exercises submit_vote(),
resolve_prediction()'s idempotency guarantees, and the resulting
UserStats/ScoreEvent/badge side effects."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from predictions.models import AIPrediction, Prediction
from predictions.services import VoteError, submit_vote
from scoring.models import ScoreEvent, UserBadge, UserStats
from scoring.resolution import ResolutionConflictError, resolve_prediction

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_prediction(**overrides):
    defaults = dict(
        slug="test-prediction",
        title="テスト予測",
        description="テスト用の説明文です。",
        category="MONETARY_POLICY",
        deadline=timezone.now() + timedelta(days=1),
    )
    defaults.update(overrides)
    return Prediction.objects.create(**defaults)


def _make_user(username="voter"):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="Password1!")
    UserStats.objects.get_or_create(user=user)
    return user


class TestSubmitVote:
    def test_creates_a_new_vote(self):
        prediction = _make_prediction()
        user = _make_user()

        up = submit_vote(user, prediction, "YES", confidence=70)

        assert up.selected_option == "YES"
        assert up.confidence == 70
        assert up.history.count() == 1

    def test_editing_before_deadline_updates_in_place_and_appends_history(self):
        prediction = _make_prediction()
        user = _make_user()

        submit_vote(user, prediction, "YES", confidence=70)
        up = submit_vote(user, prediction, "NO", confidence=90)

        assert up.selected_option == "NO"
        assert up.confidence == 90
        # One official row per (user, prediction)...
        assert prediction.user_predictions.count() == 1
        # ...but every change is preserved in the audit trail.
        assert up.history.count() == 2

    def test_total_predictions_only_increments_on_genuinely_new_vote(self):
        prediction = _make_prediction()
        user = _make_user()

        submit_vote(user, prediction, "YES", confidence=None)
        submit_vote(user, prediction, "NO", confidence=None)  # edit, not a new vote

        stats = UserStats.objects.get(user=user)
        assert stats.total_predictions == 1

    def test_refuses_vote_after_deadline(self):
        prediction = _make_prediction(deadline=timezone.now() - timedelta(hours=1))
        user = _make_user()

        with pytest.raises(VoteError):
            submit_vote(user, prediction, "YES", confidence=None)

    def test_refuses_vote_on_closed_prediction(self):
        prediction = _make_prediction(status="CLOSED")
        user = _make_user()

        with pytest.raises(VoteError):
            submit_vote(user, prediction, "YES", confidence=None)

    def test_first_vote_awards_first_prediction_badge(self):
        prediction = _make_prediction()
        user = _make_user()

        submit_vote(user, prediction, "YES", confidence=None)

        assert UserBadge.objects.filter(user=user, badge__code="FIRST_PREDICTION").exists()


class TestResolvePrediction:
    def _resolve_with_one_correct_one_incorrect(self):
        prediction = _make_prediction(deadline=timezone.now() + timedelta(hours=1))
        winner = _make_user("winner")
        loser = _make_user("loser")
        admin = User.objects.create_user(username="admin", email="admin@example.com", password="Admin1234!", role="ADMIN")

        submit_vote(winner, prediction, "YES", confidence=None)
        submit_vote(loser, prediction, "NO", confidence=None)

        result = resolve_prediction(prediction.id, "YES", admin)
        return prediction, winner, loser, admin, result

    def test_scores_every_voter_and_marks_correctness(self):
        prediction, winner, loser, admin, result = self._resolve_with_one_correct_one_incorrect()

        prediction.refresh_from_db()
        assert prediction.status == "RESOLVED"
        assert prediction.correct_option == "YES"
        assert result == {"already_resolved": False, "scored_users": 2}

        winner_stats = UserStats.objects.get(user=winner)
        loser_stats = UserStats.objects.get(user=loser)
        assert winner_stats.prediction_score == 10
        assert winner_stats.correct_predictions == 1
        assert loser_stats.prediction_score == 0
        assert loser_stats.correct_predictions == 0

    def test_creates_exactly_one_score_event_per_voter(self):
        prediction, winner, loser, admin, _ = self._resolve_with_one_correct_one_incorrect()
        assert ScoreEvent.objects.filter(prediction=prediction).count() == 2

    def test_rerunning_with_same_outcome_is_a_no_op(self):
        prediction, winner, loser, admin, _ = self._resolve_with_one_correct_one_incorrect()

        result = resolve_prediction(prediction.id, "YES", admin)

        assert result == {"already_resolved": True}
        # Score events must NOT be duplicated by the re-run.
        assert ScoreEvent.objects.filter(prediction=prediction).count() == 2
        winner_stats = UserStats.objects.get(user=winner)
        assert winner_stats.prediction_score == 10  # unchanged, not doubled

    def test_rerunning_with_a_different_outcome_is_refused(self):
        prediction, winner, loser, admin, _ = self._resolve_with_one_correct_one_incorrect()

        with pytest.raises(ResolutionConflictError):
            resolve_prediction(prediction.id, "NO", admin)

        # The original resolution must remain untouched.
        prediction.refresh_from_db()
        assert prediction.correct_option == "YES"

    def test_cancelled_prediction_cannot_be_resolved(self):
        prediction = _make_prediction(status="CANCELLED")
        admin = User.objects.create_user(username="admin2", email="admin2@example.com", password="Admin1234!")

        with pytest.raises(ResolutionConflictError):
            resolve_prediction(prediction.id, "YES", admin)

    def test_ai_killer_badge_awarded_when_user_beats_a_wrong_ai_call(self):
        prediction = _make_prediction(deadline=timezone.now() + timedelta(hours=1))
        user = _make_user("underdog")
        admin = User.objects.create_user(username="admin3", email="admin3@example.com", password="Admin1234!")

        AIPrediction.objects.create(
            prediction=prediction, provider="MOCK", model="mock-analyst-v1",
            yes_probability=0.9, no_probability=0.1, reasoning_summary="AI said YES confidently.",
        )
        submit_vote(user, prediction, "NO", confidence=None)

        resolve_prediction(prediction.id, "NO", admin)

        assert UserBadge.objects.filter(user=user, badge__code="AI_KILLER").exists()
        stats = UserStats.objects.get(user=user)
        assert stats.ai_beat_count == 1
