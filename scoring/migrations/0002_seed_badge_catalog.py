"""Seeds the Badge catalog (spec §21) as part of `migrate`, not only the
optional `seed_data` dev-data command. scoring.services.grant_badges()
looks badges up by code and silently no-ops if the row doesn't exist yet
— so any deployment that runs migrations without also running the dev
seed script would otherwise never award a single badge. This migration
is the fix: the catalog now always exists after `migrate`, and
`seed_data`'s own get_or_create() call for the same rows stays a safe
no-op on top of it.
"""

from django.db import migrations

BADGES = [
    ("FIRST_PREDICTION", "はじめての予測", "初めて予測に参加しました", "🎯"),
    ("PREDICTIONS_10", "予測10回達成", "予測に10回参加しました", "🔟"),
    ("PREDICTIONS_50", "予測50回達成", "予測に50回参加しました", "🏅"),
    ("PREDICTIONS_100", "予測100回達成", "予測に100回参加しました", "💯"),
    ("STREAK_10", "10連続的中", "10回連続で予測が的中しました", "🔥"),
    ("AI_KILLER", "AI KILLER", "AIの予測を上回りました", "🤖"),
    ("TOP_100", "TOP 100", "総合ランキングTOP 100入り", "🥉"),
    ("TOP_10", "TOP 10", "総合ランキングTOP 10入り", "🥈"),
    ("TOP_1", "TOP 1", "総合ランキング1位を獲得", "🥇"),
]


def seed_badges(apps, schema_editor):
    Badge = apps.get_model("scoring", "Badge")
    for code, name, description, icon in BADGES:
        Badge.objects.get_or_create(code=code, defaults={"name": name, "description": description, "icon": icon})


def noop_reverse(apps, schema_editor):
    # Deliberately not deleting rows on reverse — a badge catalog entry
    # being removed could cascade-delete users' already-earned
    # UserBadge rows, which is destructive and not what "unmigrate" for
    # this one step should imply.
    pass


class Migration(migrations.Migration):
    dependencies = [("scoring", "0001_initial")]
    operations = [migrations.RunPython(seed_badges, noop_reverse)]
