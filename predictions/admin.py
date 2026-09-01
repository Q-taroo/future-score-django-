from django.contrib import admin

from predictions.models import (
    AIPrediction,
    OpinionSignal,
    Prediction,
    UserPrediction,
    UserPredictionHistory,
)


class AIPredictionInline(admin.TabularInline):
    model = AIPrediction
    extra = 0
    readonly_fields = ("provider", "model", "yes_probability", "no_probability", "created_at")


class OpinionSignalInline(admin.TabularInline):
    model = OpinionSignal
    extra = 0
    readonly_fields = ("source", "yes_probability", "sample_size", "captured_at")


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "deadline", "correct_option", "is_featured")
    list_filter = ("category", "status", "is_featured")
    search_fields = ("title", "description", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [AIPredictionInline, OpinionSignalInline]


@admin.register(UserPrediction)
class UserPredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "prediction", "selected_option", "confidence", "is_correct", "created_at")
    list_filter = ("selected_option", "is_correct")
    search_fields = ("user__username", "prediction__title")


@admin.register(UserPredictionHistory)
class UserPredictionHistoryAdmin(admin.ModelAdmin):
    list_display = ("user_prediction", "selected_option", "confidence", "changed_at")
    readonly_fields = ("user_prediction", "selected_option", "confidence", "changed_at")


@admin.register(AIPrediction)
class AIPredictionAdmin(admin.ModelAdmin):
    list_display = ("prediction", "provider", "model", "yes_probability", "created_at")
    list_filter = ("provider",)


@admin.register(OpinionSignal)
class OpinionSignalAdmin(admin.ModelAdmin):
    list_display = ("prediction", "source", "yes_probability", "sample_size", "captured_at")
    list_filter = ("source",)
