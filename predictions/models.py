from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.TextChoices):
    """MVP ships the finance verticals only; the rest are reserved so a
    new genre can be turned on without a migration (spec §2/§3)."""

    MONETARY_POLICY = "MONETARY_POLICY", "金融政策"
    FOREX = "FOREX", "為替"
    STOCK_MARKET = "STOCK_MARKET", "株式市場"
    ECONOMIC_INDICATOR = "ECONOMIC_INDICATOR", "経済指標"
    COMMODITY = "COMMODITY", "コモディティ"
    MACROECONOMY = "MACROECONOMY", "マクロ経済"
    POLITICS = "POLITICS", "政治"
    SPORTS = "SPORTS", "スポーツ"
    TECHNOLOGY = "TECHNOLOGY", "テクノロジー"
    ENTERTAINMENT = "ENTERTAINMENT", "エンターテインメント"
    SOCIETY = "SOCIETY", "社会"
    WEATHER = "WEATHER", "天候"


FINANCE_CATEGORIES = [
    Category.MONETARY_POLICY,
    Category.FOREX,
    Category.STOCK_MARKET,
    Category.ECONOMIC_INDICATOR,
    Category.COMMODITY,
    Category.MACROECONOMY,
]


class PredictionStatus(models.TextChoices):
    OPEN = "OPEN", "受付中"
    CLOSED = "CLOSED", "締切済み"
    RESOLVED = "RESOLVED", "確定済み"
    CANCELLED = "CANCELLED", "キャンセル"


class QuestionType(models.TextChoices):
    BINARY = "BINARY", "二択"


class PredictionOption(models.TextChoices):
    YES = "YES", "YES"
    NO = "NO", "NO"


class Prediction(models.Model):
    slug = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=300)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=Category.choices)
    question_type = models.CharField(max_length=10, choices=QuestionType.choices, default=QuestionType.BINARY)
    option_a = models.CharField(max_length=50, default="YES")
    option_b = models.CharField(max_length=50, default="NO")
    deadline = models.DateTimeField()
    resolution_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=PredictionStatus.choices, default=PredictionStatus.OPEN)
    correct_option = models.CharField(max_length=3, choices=PredictionOption.choices, null=True, blank=True)
    source_url = models.URLField(blank=True, default="")
    resolution_method = models.TextField(blank=True, default="")
    min_predictions_for_ranking = models.PositiveIntegerField(default=10)
    is_featured = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_predictions"
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="resolved_predictions"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["status"]),
            models.Index(fields=["deadline"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_deadline_passed(self) -> bool:
        return self.deadline <= timezone.now()


class UserPrediction(models.Model):
    """The "official", latest vote per (user, prediction). Every
    submit/change is additionally appended to UserPredictionHistory,
    which is append-only and never mutated — the audit trail (spec §7)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="predictions_voted")
    prediction = models.ForeignKey(Prediction, on_delete=models.CASCADE, related_name="user_predictions")
    selected_option = models.CharField(max_length=3, choices=PredictionOption.choices)
    confidence = models.PositiveSmallIntegerField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    scored_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "prediction"], name="uniq_user_prediction")]
        indexes = [models.Index(fields=["prediction"]), models.Index(fields=["user"])]


class UserPredictionHistory(models.Model):
    user_prediction = models.ForeignKey(UserPrediction, on_delete=models.CASCADE, related_name="history")
    selected_option = models.CharField(max_length=3, choices=PredictionOption.choices)
    confidence = models.PositiveSmallIntegerField(null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user_prediction"])]


class AIProviderName(models.TextChoices):
    MOCK = "MOCK", "MOCK"
    OPENAI = "OPENAI", "OPENAI"
    ANTHROPIC = "ANTHROPIC", "ANTHROPIC"
    GOOGLE = "GOOGLE", "GOOGLE"


class AIPrediction(models.Model):
    prediction = models.ForeignKey(Prediction, on_delete=models.CASCADE, related_name="ai_predictions")
    provider = models.CharField(max_length=10, choices=AIProviderName.choices)
    model = models.CharField(max_length=100)
    yes_probability = models.FloatField()
    no_probability = models.FloatField()
    reasoning_summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["prediction"])]
        ordering = ["-created_at"]


class OpinionSource(models.TextChoices):
    MOCK_SURVEY = "MOCK_SURVEY", "Mock調査"
    NEWS_SENTIMENT = "NEWS_SENTIMENT", "ニュース"
    SEARCH_TREND = "SEARCH_TREND", "検索トレンド"
    SOCIAL_MEDIA = "SOCIAL_MEDIA", "SNS"
    PREDICTION_MARKET = "PREDICTION_MARKET", "予測市場"
    PUBLIC_STATISTICS = "PUBLIC_STATISTICS", "公開統計"


class OpinionSignal(models.Model):
    prediction = models.ForeignKey(Prediction, on_delete=models.CASCADE, related_name="opinion_signals")
    source = models.CharField(max_length=20, choices=OpinionSource.choices)
    yes_probability = models.FloatField()
    no_probability = models.FloatField()
    sample_size = models.PositiveIntegerField()
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["prediction"])]
        ordering = ["-captured_at"]
