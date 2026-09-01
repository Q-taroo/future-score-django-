"""Pure, framework/ORM-independent scoring logic.

Deliberately has ZERO Django/DB imports so it can be unit tested with
plain pytest (no database, no settings) and ported to another datastore
later without touching the rules themselves. This module is the single
source of truth for "how many points is a correct/incorrect pick worth",
"what's the current rating letter", and "how does the leaderboard sort" —
scoring.services (DB-touching) is a thin adapter on top of these.
"""

from dataclasses import dataclass

# --- Score Calculation Service (spec §12) ---------------------------------------
# MVP rule: correct -> +10, incorrect -> 0. Kept as named constants (not
# inlined) so a future Brier Score / Log Loss / calibration bonus can
# replace the body of calculate_score() without callers changing.
SCORE_CORRECT_POINTS = 10
SCORE_INCORRECT_POINTS = 0


@dataclass(frozen=True)
class ScoreResult:
    is_correct: bool
    points: int


def calculate_score(selected_option: str, correct_option: str, confidence: int | None = None) -> ScoreResult:
    """`confidence` is accepted now (even though unused by the MVP flat
    scoring rule) so a future Brier-score implementation is a body-only
    change, not a signature change that ripples through every caller."""
    is_correct = selected_option == correct_option
    return ScoreResult(is_correct=is_correct, points=SCORE_CORRECT_POINTS if is_correct else SCORE_INCORRECT_POINTS)


@dataclass(frozen=True)
class StreakResult:
    current_streak: int
    best_streak: int


def calculate_streak(previous_streak: int, previous_best_streak: int, is_correct: bool) -> StreakResult:
    current = previous_streak + 1 if is_correct else 0
    best = max(previous_best_streak, current)
    return StreakResult(current_streak=current, best_streak=best)


def calculate_accuracy(correct: int, resolved: int) -> float:
    if resolved <= 0:
        return 0.0
    return correct / resolved


def did_beat_ai(user_option: str, correct_option: str, ai_yes_probability: float) -> bool:
    """AI_KILLER tracking: was the user's pick correct while the AI's
    majority call (probability >= 50%) was wrong?"""
    ai_pick = "YES" if ai_yes_probability >= 0.5 else "NO"
    user_correct = user_option == correct_option
    ai_correct = ai_pick == correct_option
    return user_correct and not ai_correct


# --- Rating Service (spec §15) --------------------------------------------------
# Below this many *resolved* predictions, we don't have enough signal to
# award anything above C+ — prevents "3-for-3 lucky streak = A+".
MIN_RESOLVED_FOR_HIGH_RATING = 10


def calculate_rating(accuracy: float, resolved_predictions: int) -> str:
    if resolved_predictions == 0:
        return "C"

    has_volume = resolved_predictions >= MIN_RESOLVED_FOR_HIGH_RATING

    if accuracy >= 0.75 and has_volume:
        return "A+"
    if accuracy >= 0.68 and has_volume:
        return "A"
    if accuracy >= 0.60:
        return "B+" if has_volume else "B"
    if accuracy >= 0.52:
        return "B"
    if accuracy >= 0.45:
        return "C+"
    if accuracy >= 0.35:
        return "C"
    return "D"


# --- Ranking Service (spec §13) --------------------------------------------------
DEFAULT_MIN_PREDICTIONS_FOR_RANKING = 10


@dataclass(frozen=True)
class RankableUser:
    user_id: int
    prediction_score: int
    accuracy: float
    total_predictions: int
    current_streak: int = 0


@dataclass(frozen=True)
class RankedUser(RankableUser):
    rank: int = 0


def build_ranking(users: list[RankableUser], min_predictions: int = DEFAULT_MIN_PREDICTIONS_FOR_RANKING) -> list[RankedUser]:
    eligible = [u for u in users if u.total_predictions >= min_predictions]
    ordered = sorted(eligible, key=lambda u: (-u.prediction_score, -u.accuracy, -u.total_predictions))
    return [
        RankedUser(
            user_id=u.user_id,
            prediction_score=u.prediction_score,
            accuracy=u.accuracy,
            total_predictions=u.total_predictions,
            current_streak=u.current_streak,
            rank=idx + 1,
        )
        for idx, u in enumerate(ordered)
    ]


def find_user_rank(ranked: list[RankedUser], user_id: int) -> int | None:
    for u in ranked:
        if u.user_id == user_id:
            return u.rank
    return None


# --- Badge Service (spec §21) ----------------------------------------------------
@dataclass(frozen=True)
class StatsSnapshot:
    total_predictions: int = 0
    resolved_predictions: int = 0
    correct_predictions: int = 0
    current_streak: int = 0
    best_streak: int = 0
    prediction_score: int = 0
    ai_beat_count: int = 0


def determine_volume_badges(stats: StatsSnapshot) -> list[str]:
    codes: list[str] = []
    if stats.total_predictions >= 1:
        codes.append("FIRST_PREDICTION")
    if stats.total_predictions >= 10:
        codes.append("PREDICTIONS_10")
    if stats.total_predictions >= 50:
        codes.append("PREDICTIONS_50")
    if stats.total_predictions >= 100:
        codes.append("PREDICTIONS_100")
    if stats.current_streak >= 10:
        codes.append("STREAK_10")
    if stats.ai_beat_count >= 1:
        codes.append("AI_KILLER")
    return codes


def determine_rank_badges(rank: int | None) -> list[str]:
    if rank is None:
        return []
    codes: list[str] = []
    if rank <= 100:
        codes.append("TOP_100")
    if rank <= 10:
        codes.append("TOP_10")
    if rank == 1:
        codes.append("TOP_1")
    return codes
