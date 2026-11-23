"""Versioned title/description food-relevance rules."""
import re
FOOD_TERMS = (
    "美食", "吃", "餐", "饭", "菜", "面", "饼", "肉", "鱼", "虾", "蛋", "甜品", "奶茶",
    "咖啡", "火锅", "烧烤", "小吃", "早餐", "夜市", "厨房", "烘焙", "点心", "饮料",
    "豆皮", "米粉", "牛排", "寿司", "料理", "卤味", "煎", "炒", "炖", "拌", "食谱",
    "海鲜", "便当", "寿喜烧", "厨艺", "调料", "年糕", "外卖", "三明治", "一人食",
    "曲奇", "布朗尼", "冰激凌", "冰淇淋", "泰奶", "巴斯克", "可露丽", "食物", "苍蝇馆子",
)
META_TERMS = ("博主真实行情", "体验官招募", "博主吗", "拍照分享")
NON_FOOD_PATTERNS = (
    r'blender.{0,20}(烘焙|贴图)',
    r'烘焙.{0,8}(贴图|材质)|(贴图|材质).{0,8}烘焙',
    r'(游戏|模拟人生|星露谷).{0,20}(模组|\bmod\b)|(模组|\bmod\b).{0,20}(游戏|模拟人生|星露谷)',
)

def food_relevance(row: dict) -> str:
    text = (row.get("title") or "") + " " + (row.get("description") or "")
    if any(re.search(pattern,text,re.I) for pattern in NON_FOOD_PATTERNS):
        return "no"
    if any(term in text for term in META_TERMS):
        return "uncertain"
    return "yes" if any(term in text for term in FOOD_TERMS) else "uncertain"



