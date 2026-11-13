#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam 促销助手 - Skill 专用脚本
查询当前 Steam 打折游戏，按推荐分区输出结构化 JSON 到 stdout
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import json
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===== 配置 =====
STEAM_CC = "cn"
STEAM_LANG = "schinese"
REQUEST_TIMEOUT = 12
MAX_ENRICH = 30  # 最多补充详情的游戏数量（控制总耗时）

# 2026-2027 官方大促日历（来源：Steamworks 官方文档）
SEASONAL_SALES = [
    {"name": "春季特卖 2026", "start": "2026-03-12", "end": "2026-03-19"},
    {"name": "夏季特卖 2026", "start": "2026-06-25", "end": "2026-07-09"},
    {"name": "秋季特卖 2026", "start": "2026-10-01", "end": "2026-10-08"},
    {"name": "冬季特卖 2026", "start": "2026-12-17", "end": "2027-01-04"},
    {"name": "春季特卖 2027", "start": "2027-03-11", "end": "2027-03-18"},
]


# ===== 大促判断 =====

def get_current_sale():
    today = datetime.now().strftime("%Y-%m-%d")
    for sale in SEASONAL_SALES:
        if sale["start"] <= today <= sale["end"]:
            return sale
    return None


def get_next_sale():
    today = datetime.now().strftime("%Y-%m-%d")
    for sale in SEASONAL_SALES:
        if sale["start"] > today:
            return sale
    return None


# ===== Steam API =====

def get_featured_categories():
    """获取 Steam 特惠分类"""
    url = f"https://store.steampowered.com/api/featuredcategories?cc={STEAM_CC}&l={STEAM_LANG}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[WARN] featuredcategories 失败: {e}", file=sys.stderr)
        return None


def get_specials_extended():
    """从搜索接口获取更多打折游戏"""
    url = (
        f"https://store.steampowered.com/api/storesearch/"
        f"?term=&sort_by=_ASC&ignore_preferences=1&category1=998&specials=1"
        f"&cc={STEAM_CC}&l={STEAM_LANG}&count=50"
    )
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        games = []
        for item in items:
            if item.get("price"):
                game = {
                    "id": item["id"],
                    "name": item["name"],
                    "original_price": item["price"].get("initial", 0),
                    "final_price": item["price"].get("final", 0),
                    "discount_percent": 0,
                    "currency": item["price"].get("currency", "CNY"),
                }
                if game["original_price"] > 0:
                    game["discount_percent"] = round(
                        (1 - game["final_price"] / game["original_price"]) * 100
                    )
                if game["discount_percent"] > 0:
                    games.append(game)
        return games
    except Exception as e:
        print(f"[WARN] storesearch 失败: {e}", file=sys.stderr)
        return []


def get_app_details(appid):
    """获取游戏详情"""
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc={STEAM_CC}&l={STEAM_LANG}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data and str(appid) in data and data[str(appid)].get("success"):
            return data[str(appid)]["data"]
    except Exception as e:
        print(f"[WARN] appdetails {appid}: {e}", file=sys.stderr)
    return None


def get_app_reviews(appid):
    """获取游戏评价汇总"""
    url = f"https://store.steampowered.com/appreviews/{appid}?json=1&language=all&purchase_type=all&num_per_page=0"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") == 1:
            summary = data.get("query_summary", {})
            total_pos = summary.get("total_positive", 0)
            total_neg = summary.get("total_negative", 0)
            total = total_pos + total_neg
            rate = round(total_pos / total * 100, 1) if total > 0 else 0
            return {"total_reviews": total, "positive_rate": rate}
    except Exception as e:
        print(f"[WARN] appreviews {appid}: {e}", file=sys.stderr)
    return None


# ===== 数据处理 =====

def check_chinese_support(supported_languages_html):
    if not supported_languages_html:
        return "未知"
    text = supported_languages_html.lower()
    has_sc = "简体中文" in supported_languages_html or "schinese" in text or "simplified chinese" in text
    has_tc = "繁体中文" in supported_languages_html or "tchinese" in text or "traditional chinese" in text
    if has_sc and has_tc:
        return "简/繁中文"
    elif has_sc:
        return "简体中文"
    elif has_tc:
        return "繁体中文"
    return "无中文"


def get_genres_text(genres_list):
    if not genres_list:
        return ""
    return "/".join([g.get("description", "") for g in genres_list[:3]])


def enrich_one_game(game_basic):
    """补充一款游戏的详情（并发调用用）"""
    appid = game_basic["id"]
    result = {
        "appid": appid,
        "name": game_basic.get("name", ""),
        "discount_percent": game_basic.get("discount_percent", 0),
        "original_price": game_basic.get("original_price", 0),
        "final_price": game_basic.get("final_price", 0),
    }

    # 并行获取评价和详情
    reviews = get_app_reviews(appid)
    details = get_app_details(appid)

    if reviews:
        result["positive_rate"] = reviews["positive_rate"]
        result["total_reviews"] = reviews["total_reviews"]
    else:
        result["positive_rate"] = 0
        result["total_reviews"] = 0

    if details:
        result["chinese_support"] = check_chinese_support(details.get("supported_languages", ""))
        result["genres"] = get_genres_text(details.get("genres", []))
        result["release_date"] = details.get("release_date", {}).get("date", "")
        result["short_description"] = details.get("short_description", "")
    else:
        result["chinese_support"] = "未知"
        result["genres"] = ""
        result["release_date"] = ""
        result["short_description"] = ""

    return result


def get_review_description(positive_rate, total_reviews):
    """根据好评率和评论数返回 Steam 风格的评价描述"""
    if total_reviews < 10:
        return ""
    if positive_rate >= 95 and total_reviews >= 500:
        return "好评如潮"
    elif positive_rate >= 80 and total_reviews >= 50:
        return "特别好评"
    elif positive_rate >= 70:
        return "多半好评"
    elif positive_rate >= 40:
        return "褒贬不一"
    elif positive_rate >= 20:
        return "多半差评"
    elif total_reviews >= 500:
        return "差评如潮"
    else:
        return "差评"


def format_reviews_count(count):
    if count >= 10000:
        value = count / 10000
        if value >= 10:
            return f"{value:.0f}万"
        else:
            return f"{value:.1f}万"
    return f"{count:,}"


def format_price(price_cents):
    if price_cents is None or price_cents == 0:
        return "免费"
    return f"¥{price_cents / 100:.0f}"


def classify_games(games):
    """按推荐分区归类"""
    big_hits = []
    quality_picks = []
    new_deals = []
    one_year_ago = datetime.now() - timedelta(days=365)

    for g in games:
        reviews = g.get("total_reviews", 0)
        rate = g.get("positive_rate", 0)
        discount = g.get("discount_percent", 0)
        release = g.get("release_date", "")

        is_new = False
        if release:
            for fmt in ["%Y 年 %m 月 %d 日", "%Y年%m月%d日", "%b %d, %Y", "%d %b, %Y"]:
                try:
                    rd = datetime.strptime(release, fmt)
                    is_new = rd > one_year_ago
                    break
                except ValueError:
                    continue

        if is_new and discount >= 20:
            new_deals.append(g)
        elif reviews >= 50000 and discount >= 50:
            big_hits.append(g)
        elif rate >= 90 and reviews >= 3000 and discount >= 30:
            quality_picks.append(g)
        elif reviews >= 50000 and discount >= 40:
            big_hits.append(g)
        elif rate >= 85 and reviews >= 10000 and discount >= 40:
            quality_picks.append(g)

    big_hits.sort(key=lambda x: (-x["discount_percent"], -x["total_reviews"]))
    quality_picks.sort(key=lambda x: (-x["positive_rate"], -x["total_reviews"]))
    new_deals.sort(key=lambda x: (-x["discount_percent"], -x["total_reviews"]))

    return {
        "big_hits": big_hits[:8],
        "quality_picks": quality_picks[:8],
        "new_deals": new_deals[:5],
    }


# ===== 输出 =====

def format_output(classified, current_sale, next_sale):
    """输出结构化 JSON"""
    result = {"sale_status": {}, "sections": [], "next_sale": None}

    if current_sale:
        result["sale_status"] = {
            "in_sale": True,
            "name": current_sale["name"],
            "start": current_sale["start"],
            "end": current_sale["end"],
        }
    else:
        result["sale_status"] = {
            "in_sale": False,
            "note": "当前无大型季节性促销，以下为日常/周末特惠精选",
        }

    section_map = [
        ("🔥 大作好价", "big_hits"),
        ("💎 口碑精品", "quality_picks"),
        ("🆕 新品首折", "new_deals"),
    ]

    for title, key in section_map:
        games = classified.get(key, [])
        if not games:
            continue
        section = {"title": title, "games": []}
        for g in games:
            rate = g.get("positive_rate", 0)
            total = g.get("total_reviews", 0)
            section["games"].append({
                "name": g["name"],
                "appid": g["appid"],
                "genres": g.get("genres", ""),
                "original_price": format_price(g["original_price"]),
                "final_price": format_price(g["final_price"]),
                "discount_percent": g["discount_percent"],
                "chinese_support": g.get("chinese_support", "未知"),
                "positive_rate": rate,
                "total_reviews_display": format_reviews_count(total),
                "review_description": get_review_description(rate, total),
                "short_description": g.get("short_description", ""),
                "release_date": g.get("release_date", ""),
            })
        result["sections"].append(section)

    if next_sale:
        result["next_sale"] = {
            "name": next_sale["name"],
            "start": next_sale["start"],
            "end": next_sale["end"],
        }

    return result


# ===== 主入口 =====

def main():
    print("开始获取 Steam 促销数据...", file=sys.stderr)
    start_time = time.time()

    # 1. 大促判断
    current_sale = get_current_sale()
    next_sale = get_next_sale()
    if current_sale:
        print(f"  当前大促: {current_sale['name']}", file=sys.stderr)
    else:
        print("  当前无大促，获取日常特惠", file=sys.stderr)

    # 2. 获取特惠列表
    print("  获取 featuredcategories...", file=sys.stderr)
    featured = get_featured_categories()

    games_basic = []
    if featured:
        specials = featured.get("specials", {}).get("items", [])
        for item in specials:
            if item.get("discounted") and item.get("type") == 0:
                games_basic.append(item)
        print(f"  specials: {len(games_basic)} 款", file=sys.stderr)

    # 3. 补充搜索接口
    print("  获取 storesearch...", file=sys.stderr)
    extended = get_specials_extended()
    print(f"  storesearch: {len(extended)} 款", file=sys.stderr)

    # 合并去重
    seen_ids = set(g["id"] for g in games_basic)
    for g in extended:
        if g["id"] not in seen_ids:
            games_basic.append(g)
            seen_ids.add(g["id"])

    total_basic = len(games_basic)
    print(f"  合计去重: {total_basic} 款", file=sys.stderr)

    # 4. 并发补充详情（限制数量控制耗时）
    to_enrich = games_basic[:MAX_ENRICH]
    print(f"  补充详情（并发，最多 {len(to_enrich)} 款）...", file=sys.stderr)

    enriched_games = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(enrich_one_game, g): g for g in to_enrich}
        for future in as_completed(futures):
            try:
                result = future.result()
                enriched_games.append(result)
            except Exception as e:
                game = futures[future]
                print(f"  [SKIP] {game.get('name', '?')}: {e}", file=sys.stderr)

    print(f"  详情获取完成: {len(enriched_games)} 款", file=sys.stderr)

    # 5. 分类
    classified = classify_games(enriched_games)
    print(f"  分类结果: 大作{len(classified['big_hits'])} 精品{len(classified['quality_picks'])} 新品{len(classified['new_deals'])}", file=sys.stderr)

    # 6. 输出 JSON 到 stdout
    output = format_output(classified, current_sale, next_sale)
    elapsed = round(time.time() - start_time, 1)
    output["_meta"] = {"elapsed_seconds": elapsed, "games_evaluated": len(enriched_games)}
    print(f"  总耗时: {elapsed}s", file=sys.stderr)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
