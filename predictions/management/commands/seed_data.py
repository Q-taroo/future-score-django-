"""Development seed data — Django port of the Next.js version's
prisma/seed.ts. Creates 24 finance predictions across the 6 launch
categories, an admin + demo + 22 mock predictor accounts, AI predictions
and opinion signals for every question, mock votes, and pre-resolves 8
predictions so ranking/profile/dashboard pages have real data to show
immediately after seeding.

Idempotent-ish: re-running wipes and recreates seed-owned rows so local
dev/demo environments can be reset with one command.
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from predictions.models import (
    AIPrediction,
    Category,
    FINANCE_CATEGORIES,
    OpinionSignal,
    Prediction,
    PredictionStatus,
    UserPrediction,
    UserPredictionHistory,
)
from predictions.providers.ai.mock import MockAIProvider
from predictions.providers.ai.base import PredictionInputForAI
from predictions.providers.opinion import MockOpinionProvider, OpinionSignalInput
from scoring.models import Badge, BadgeCode, ScoreEvent, UserStats
from scoring.resolution import resolve_prediction
from scoring.services import refresh_ranking

User = get_user_model()

BADGE_DEFS = {
    BadgeCode.FIRST_PREDICTION: ("はじめての予測", "初めて予測に参加しました", "🎯"),
    BadgeCode.PREDICTIONS_10: ("予測10回達成", "予測に10回参加しました", "🔟"),
    BadgeCode.PREDICTIONS_50: ("予測50回達成", "予測に50回参加しました", "🏅"),
    BadgeCode.PREDICTIONS_100: ("予測100回達成", "予測に100回参加しました", "💯"),
    BadgeCode.STREAK_10: ("10連続的中", "10回連続で予測が的中しました", "🔥"),
    BadgeCode.AI_KILLER: ("AI KILLER", "AIの予測を上回りました", "🤖"),
    BadgeCode.TOP_100: ("TOP 100", "総合ランキングTOP 100入り", "🥉"),
    BadgeCode.TOP_10: ("TOP 10", "総合ランキングTOP 10入り", "🥈"),
    BadgeCode.TOP_1: ("TOP 1", "総合ランキング1位を獲得", "🥇"),
}

QUESTION_TEMPLATES = {
    Category.MONETARY_POLICY: [
        "日銀は次回会合で追加利上げを実施するか？",
        "FRBは年内にあと2回以上利下げを実施するか？",
        "ECBは政策金利を据え置くか？",
        "日銀はマイナス金利政策の再導入を検討すると示唆するか？",
    ],
    Category.FOREX: [
        "ドル円は年内に155円を突破するか？",
        "ユーロドルは1.10を上回って年を終えるか？",
        "人民元は対ドルで年初来安値を更新するか？",
        "英ポンドは対ドルで5%以上上昇するか？",
    ],
    Category.STOCK_MARKET: [
        "日経平均は年内に史上最高値を更新するか？",
        "S&P500は年内に5%以上の調整局面を迎えるか？",
        "半導体関連株は今四半期にセクター平均を上回るか？",
        "東証グロース市場指数は年内にプラス圏で終えるか？",
    ],
    Category.ECONOMIC_INDICATOR: [
        "米国の次回CPIは市場予想を上回るか？",
        "日本の実質GDP成長率は前期比プラスとなるか？",
        "米国失業率は4%を下回るか？",
        "日本の消費者物価上昇率は2%を上回り続けるか？",
    ],
    Category.COMMODITY: [
        "WTI原油価格は年内に90ドルを超えるか？",
        "金価格は年内に最高値を更新するか？",
        "銅価格は今四半期に5%以上上昇するか？",
        "天然ガス価格は冬場に急騰するか？",
    ],
    Category.MACROECONOMY: [
        "世界経済は年内にリセッション入りするか？",
        "中国の経済成長率は政府目標を達成するか？",
        "米国の長短金利は年内に逆転が解消するか？",
        "新興国からの資金流出は加速するか？",
    ],
}


def _rand_deadline(days_from_now: int) -> object:
    return timezone.now() + timedelta(days=days_from_now)


class Command(BaseCommand):
    help = "Seed the database with demo predictions, users, AI/opinion signals, votes, and resolved results."

    def handle(self, *args, **options):
        self._run()

    def _run(self):
        random.seed(42)
        with transaction.atomic():
            self._wipe()
            admin = self._create_admin()
            demo = self._create_demo()
            predictors = self._create_predictors()
            all_users = [demo] + predictors

            badges = self._create_badges()

            predictions = self._create_predictions(admin)
            self._create_votes(predictions, all_users)

        # Resolution runs its own transactions per-prediction (mirrors
        # scoring/resolution.py's real usage), so it happens outside the
        # bulk-seed transaction above.
        self._resolve_some(predictions, admin)
        refresh_ranking()

        print(f"Seeded {len(predictions)} predictions, {len(all_users) + 1} users.")
        print("Login credentials:")
        print("  admin@futurescore.local / Admin1234!")
        print("  demo@futurescore.local / Demo1234!")
        print("  predictor_01@futurescore.local .. predictor_22@futurescore.local / Password1!")

    def _wipe(self):
        UserPredictionHistory.objects.all().delete()
        UserPrediction.objects.all().delete()
        AIPrediction.objects.all().delete()
        OpinionSignal.objects.all().delete()
        ScoreEvent.objects.all().delete()
        Prediction.objects.all().delete()
        UserStats.objects.all().delete()
        User.objects.filter(username__startswith="predictor_").delete()
        User.objects.filter(username__in=["admin", "demo"]).delete()

    def _create_admin(self):
        admin = User.objects.create_user(
            username="admin", email="admin@futurescore.local", password="Admin1234!", role=User.Role.ADMIN
        )
        UserStats.objects.get_or_create(user=admin)
        return admin

    def _create_demo(self):
        demo = User.objects.create_user(username="demo", email="demo@futurescore.local", password="Demo1234!")
        UserStats.objects.get_or_create(user=demo)
        return demo

    def _create_predictors(self):
        users = []
        for i in range(1, 23):
            username = f"predictor_{i:02d}"
            user = User.objects.create_user(
                username=username, email=f"{username}@futurescore.local", password="Password1!"
            )
            UserStats.objects.get_or_create(user=user)
            users.append(user)
        return users

    def _create_badges(self):
        badges = {}
        for code, (name, description, icon) in BADGE_DEFS.items():
            badge, _ = Badge.objects.get_or_create(
                code=code, defaults={"name": name, "description": description, "icon": icon}
            )
            badges[code] = badge
        return badges

    def _create_predictions(self, admin):
        ai_provider = MockAIProvider()
        opinion_provider = MockOpinionProvider()
        predictions = []
        idx = 0
        for category in FINANCE_CATEGORIES:
            for q_idx, title in enumerate(QUESTION_TEMPLATES[category]):
                idx += 1
                # Roughly a third of predictions are already past their
                # deadline so /predictions can show CLOSED/RESOLVED states
                # too, not just OPEN ones.
                if idx % 3 == 0:
                    deadline = timezone.now() - timedelta(days=random.randint(1, 10))
                else:
                    deadline = _rand_deadline(random.randint(3, 60))

                slug_base = f"{category.value.lower()}-{q_idx + 1}"
                prediction = Prediction.objects.create(
                    slug=f"{slug_base}-{idx}",
                    title=title,
                    description=(
                        f"「{title}」について、AI予測・世論シグナル・ユーザーの皆さんの予測を比較します。"
                        "本予測は情報提供・エンターテインメント目的の分析であり、投資助言ではありません。"
                    ),
                    category=category,
                    deadline=deadline,
                    status=PredictionStatus.OPEN,
                    source_url="",
                    resolution_method="公表された公式統計・発表に基づき運営が判定します。",
                    min_predictions_for_ranking=10,
                    is_featured=(idx <= 6),
                    created_by=admin,
                )

                ai_output = ai_provider.generate_prediction(
                    PredictionInputForAI(
                        id=str(prediction.id),
                        title=prediction.title,
                        description=prediction.description,
                        category=prediction.category,
                        option_a=prediction.option_a,
                        option_b=prediction.option_b,
                        deadline=prediction.deadline,
                    )
                )
                AIPrediction.objects.create(
                    prediction=prediction,
                    provider=ai_provider.provider_name,
                    model=ai_output.model,
                    yes_probability=ai_output.probability,
                    no_probability=1 - ai_output.probability,
                    reasoning_summary=ai_output.reasoning_summary,
                )

                opinion_result = opinion_provider.fetch_signal(
                    OpinionSignalInput(id=str(prediction.id), title=prediction.title, category=prediction.category)
                )
                OpinionSignal.objects.create(
                    prediction=prediction,
                    source=opinion_result.source,
                    yes_probability=opinion_result.yes_probability,
                    no_probability=opinion_result.no_probability,
                    sample_size=opinion_result.sample_size,
                )

                predictions.append(prediction)

        return predictions

    def _create_votes(self, predictions, users):
        for prediction in predictions:
            voters = random.sample(users, k=random.randint(6, len(users)))
            for user in voters:
                selected = random.choices(["YES", "NO"], weights=[55, 45])[0]
                confidence = random.choice([None, None, random.randint(55, 95)])
                up = UserPrediction.objects.create(
                    user=user, prediction=prediction, selected_option=selected, confidence=confidence
                )
                UserPredictionHistory.objects.create(
                    user_prediction=up, selected_option=selected, confidence=confidence
                )
                stats, _ = UserStats.objects.get_or_create(user=user)
                stats.total_predictions += 1
                stats.save(update_fields=["total_predictions"])

    def _resolve_some(self, predictions, admin):
        # Resolve every prediction whose deadline has already passed
        # (matches real-world lifecycle) so ranking/profile/dashboard
        # pages have real accuracy/score data right after seeding.
        past_due = [p for p in predictions if p.deadline <= timezone.now()]
        for prediction in past_due:
            correct_option = random.choices(["YES", "NO"], weights=[55, 45])[0]
            resolve_prediction(prediction.id, correct_option, admin)
