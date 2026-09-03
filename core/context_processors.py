def app_context(request):
    """Small set of globals every template can rely on without each view
    passing them explicitly."""
    from django.conf import settings

    return {
        "APP_NAME": "FUTURE SCORE",
        "CURRENT_YEAR": __import__("datetime").datetime.now().year,
        "NOTE_TUTORIAL_URL": settings.NOTE_TUTORIAL_URL,
    }
