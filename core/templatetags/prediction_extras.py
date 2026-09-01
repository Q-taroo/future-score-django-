from django import template

register = template.Library()

CATEGORY_LABELS = {
    "MONETARY_POLICY": "金融政策",
    "FOREX": "為替",
    "STOCK_MARKET": "株式市場",
    "ECONOMIC_INDICATOR": "経済指標",
    "COMMODITY": "コモディティ",
    "MACROECONOMY": "マクロ経済",
    "POLITICS": "政治",
    "SPORTS": "スポーツ",
    "TECHNOLOGY": "テクノロジー",
    "ENTERTAINMENT": "エンターテインメント",
    "SOCIETY": "社会",
    "WEATHER": "天候",
}

STATUS_LABELS = {
    "OPEN": "受付中",
    "CLOSED": "締切済み",
    "RESOLVED": "確定済み",
    "CANCELLED": "キャンセル",
}


@register.filter
def category_label(value: str) -> str:
    return CATEGORY_LABELS.get(value, value)


@register.filter
def status_label(value: str) -> str:
    return STATUS_LABELS.get(value, value)


@register.filter
def percent(value) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"{round(float(value) * 100)}%"
    except (TypeError, ValueError):
        return "—"


@register.filter
def mul100(value) -> float:
    if value is None:
        return 0
    return float(value) * 100


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def jpy_number(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)
