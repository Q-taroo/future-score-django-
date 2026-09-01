from django.contrib import admin

from scoring.models import Badge, ScoreEvent, UserBadge, UserStats


@admin.register(ScoreEvent)
class ScoreEventAdmin(admin.ModelAdmin):
    list_display = ("user", "prediction", "type", "points", "created_at")
    list_filter = ("type",)
    search_fields = ("user__username",)


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "prediction_score",
        "accuracy",
        "rating",
        "overall_rank",
        "current_streak",
        "ai_beat_count",
    )
    list_filter = ("rating",)
    search_fields = ("user__username",)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "icon")


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "earned_at")
    search_fields = ("user__username",)
