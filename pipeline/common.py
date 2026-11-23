"""Shared deterministic screening helpers."""
from urllib.parse import urlsplit, urlunsplit

FOOD_TERMS = (
    "美食", "吃", "餐", "饭", "菜", "面", "饼", "肉", "鱼", "虾", "蛋", "甜品", "奶茶",
    "咖啡", "火锅", "烧烤", "小吃", "早餐", "夜市", "厨房", "烘焙", "点心", "饮料",
    "豆皮", "米粉", "牛排", "寿司", "料理", "卤味", "煎", "炒", "炖", "拌", "食谱",
)
META_TERMS = ("博主真实行情", "体验官招募", "博主吗", "拍照分享")

def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def food_relevance(row: dict) -> str:
    text = (row.get("title") or "") + " " + (row.get("description") or "")
    if any(term in text for term in META_TERMS):
        return "uncertain"
    return "yes" if any(term in text for term in FOOD_TERMS) else "uncertain"


