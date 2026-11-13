#!/usr/bin/env python3
"""
Steam DLC 雷达 — 定时检查脚本
用途：检查指定游戏是否有新 DLC 上线
特性：3次重试 + 5秒超时 + 指数退避 + 本地缓存
网络说明：store.steampowered.com 国内可达但不稳定，需重试机制兜底

用法：
  python check_dlc.py --app_id 1245620 --game_name "艾尔登法环"
  python check_dlc.py --app_id 1245620 --game_name "艾尔登法环" --full   # 输出完整 DLC 列表
  python check_dlc.py --check_all                                        # 检查所有缓存过的游戏
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote

# ============================================================
# 配置
# ============================================================
STEAM_STORE_API = "https://store.steampowered.com/api"
STEAM_REVIEW_API = "https://store.steampowered.com/appreviews"

MAX_RETRIES = 3          # 最大重试次数
TIMEOUT_SECONDS = 8      # 单次请求超时（秒）
RETRY_BASE_DELAY = 2     # 重试基础延迟（秒），指数退避：2s → 4s → 8s
REQUEST_INTERVAL = 0.5   # 请求间隔（秒），避免触发频率限制

# 缓存目录（脚本同目录下的 data/）
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
CACHE_FILE = DATA_DIR / "dlc_cache.json"

# ============================================================
# 网络请求（带重试 + 超时 + 指数退避）
# ============================================================

def fetch_json(url: str) -> dict | None:
    """
    发起 GET 请求，返回 JSON 解析结果。
    失败时自动重试，全部失败返回 None。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except (URLError, HTTPError, TimeoutError, OSError, json.JSONDecodeError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                print(f"  [重试 {attempt}/{MAX_RETRIES}] 请求失败: {e}，{delay}秒后重试...")
                time.sleep(delay)
            else:
                print(f"  [失败] 经过 {MAX_RETRIES} 次尝试，请求仍失败: {e}")
    
    return None


# ============================================================
# Steam API 封装
# ============================================================

def search_game(game_name: str) -> int | None:
    """通过游戏名搜索 Steam AppID"""
    url = f"{STEAM_STORE_API}/storesearch/?term={quote(game_name)}&cc=cn&l=schinese"
    data = fetch_json(url)
    if data and data.get("total", 0) > 0:
        items = data.get("items", [])
        if items:
            return items[0].get("id")
    return None


def get_app_details(app_id: int) -> dict | None:
    """获取游戏/DLC 详情"""
    url = f"{STEAM_STORE_API}/appdetails?appids={app_id}&cc=cn&l=schinese"
    data = fetch_json(url)
    if data:
        app_data = data.get(str(app_id), {})
        if app_data.get("success"):
            return app_data.get("data", {})
    return None


def get_reviews_summary(app_id: int) -> dict | None:
    """获取评测汇总"""
    url = f"{STEAM_REVIEW_API}/{app_id}?json=1&language=all&num_per_page=0"
    data = fetch_json(url)
    if data and data.get("success") == 1:
        return data.get("query_summary", {})
    return None


# ============================================================
# 缓存管理
# ============================================================

def load_cache() -> dict:
    """加载本地 DLC 缓存"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(cache: dict):
    """保存 DLC 缓存"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ============================================================
# 核心逻辑
# ============================================================

def check_game_dlc(app_id: int, game_name: str, full_mode: bool = False) -> dict:
    """
    检查指定游戏的 DLC 情况。
    
    返回结构：
    {
        "success": bool,           # 是否成功获取数据
        "error": str | None,       # 失败原因
        "game_name": str,          # 游戏名
        "app_id": int,             # AppID
        "total_dlc": int,          # DLC 总数
        "new_dlc": [...],          # 新增 DLC 列表
        "all_dlc": [...],          # 全部 DLC 列表（full_mode=True 时）
        "cached_dlc_ids": [...],   # 上次缓存的 DLC ID 列表
        "checked_at": str,         # 检查时间
    }
    """
    result = {
        "success": False,
        "error": None,
        "game_name": game_name,
        "app_id": app_id,
        "total_dlc": 0,
        "new_dlc": [],
        "all_dlc": [],
        "cached_dlc_ids": [],
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    # 1. 获取游戏详情
    print(f"\n🔍 正在查询 {game_name} (AppID: {app_id}) 的 DLC 信息...")
    game_data = get_app_details(app_id)
    
    if game_data is None:
        result["error"] = (
            "Steam 商店 API 当前无法访问。\n"
            "可能原因：Steam 在国内访问不稳定（store.steampowered.com）。\n"
            "建议：开启加速器后重试，或稍后再试。"
        )
        return result
    
    # 2. 提取 DLC 列表
    dlc_ids = game_data.get("dlc", [])
    result["total_dlc"] = len(dlc_ids)
    
    if not dlc_ids:
        result["success"] = True
        print(f"  📭 {game_name} 没有 DLC。")
        # 更新缓存（记录该游戏没有 DLC）
        cache = load_cache()
        cache[str(app_id)] = {
            "game_name": game_name,
            "dlc_ids": [],
            "last_checked": result["checked_at"],
        }
        save_cache(cache)
        return result
    
    print(f"  📦 发现 {len(dlc_ids)} 个 DLC")
    
    # 3. 加载缓存，对比新增
    cache = load_cache()
    cache_key = str(app_id)
    cached_entry = cache.get(cache_key, {})
    cached_dlc_ids = set(cached_entry.get("dlc_ids", []))
    result["cached_dlc_ids"] = list(cached_dlc_ids)
    
    new_dlc_ids = [did for did in dlc_ids if did not in cached_dlc_ids]
    
    # 4. 获取 DLC 详情
    dlc_to_fetch = new_dlc_ids if (not full_mode and cached_dlc_ids) else dlc_ids
    
    fetched_dlc = []
    failed_count = 0
    
    for i, dlc_id in enumerate(dlc_to_fetch):
        if i > 0:
            time.sleep(REQUEST_INTERVAL)
        
        print(f"  [{i+1}/{len(dlc_to_fetch)}] 查询 DLC {dlc_id}...")
        dlc_data = get_app_details(dlc_id)
        
        if dlc_data is None:
            failed_count += 1
            print(f"    ⚠️ DLC {dlc_id} 查询失败")
            continue
        
        # 获取评测信息
        time.sleep(REQUEST_INTERVAL)
        reviews = get_reviews_summary(dlc_id)
        
        dlc_info = {
            "dlc_id": dlc_id,
            "name": dlc_data.get("name", f"Unknown DLC ({dlc_id})"),
            "is_free": dlc_data.get("is_free", False),
            "price": None,
            "discount_percent": 0,
            "release_date": dlc_data.get("release_date", {}).get("date", "未知"),
            "coming_soon": dlc_data.get("release_date", {}).get("coming_soon", False),
            "short_description": dlc_data.get("short_description", ""),
            "reviews": None,
            "is_new": dlc_id in new_dlc_ids,
        }
        
        # 价格
        price_info = dlc_data.get("price_overview")
        if price_info:
            dlc_info["price"] = price_info.get("final_formatted", "")
            dlc_info["discount_percent"] = price_info.get("discount_percent", 0)
        elif dlc_info["is_free"]:
            dlc_info["price"] = "免费"
        
        # 评测
        if reviews:
            total = reviews.get("total_reviews", 0)
            positive = reviews.get("total_positive", 0)
            dlc_info["reviews"] = {
                "total": total,
                "positive": positive,
                "negative": reviews.get("total_negative", 0),
                "score_desc": reviews.get("review_score_desc", ""),
                "positive_rate": round(positive / total * 100, 1) if total > 0 else 0,
            }
        
        fetched_dlc.append(dlc_info)
    
    # 5. 判断成功状态
    if failed_count == len(dlc_to_fetch):
        result["error"] = (
            "所有 DLC 详情查询均失败。\n"
            "可能原因：Steam 在国内访问不稳定（store.steampowered.com）。\n"
            "建议：开启加速器后重试，或稍后再试。"
        )
        return result
    
    result["success"] = True
    
    if full_mode or not cached_dlc_ids:
        result["all_dlc"] = fetched_dlc
    
    result["new_dlc"] = [d for d in fetched_dlc if d.get("is_new")]
    
    # 6. 更新缓存
    cache[cache_key] = {
        "game_name": game_name,
        "dlc_ids": dlc_ids,
        "last_checked": result["checked_at"],
    }
    save_cache(cache)
    
    # 7. 输出统计
    if new_dlc_ids:
        print(f"\n  🆕 发现 {len(new_dlc_ids)} 个新 DLC！")
    else:
        print(f"\n  ✅ 暂无新 DLC（缓存 {len(cached_dlc_ids)} 个，当前 {len(dlc_ids)} 个）")
    
    if failed_count > 0:
        print(f"  ⚠️ {failed_count} 个 DLC 查询失败（部分 Steam API 请求超时）")
    
    return result


def check_all_cached() -> list[dict]:
    """检查所有缓存过的游戏"""
    cache = load_cache()
    results = []
    
    if not cache:
        print("📭 暂无缓存数据，请先查询至少一个游戏。")
        return results
    
    print(f"🔍 准备检查 {len(cache)} 个已缓存游戏...\n")
    
    for app_id_str, entry in cache.items():
        app_id = int(app_id_str)
        game_name = entry.get("game_name", f"AppID:{app_id}")
        result = check_game_dlc(app_id, game_name)
        results.append(result)
        time.sleep(REQUEST_INTERVAL)
    
    return results


# ============================================================
# 输出格式化（供 AI 解析）
# ============================================================

def format_output(result: dict) -> str:
    """格式化输出结果为文本（AI 可直接解析并转为用户友好格式）"""
    lines = []
    
    if not result["success"]:
        lines.append(f"❌ 检查失败 — {result['game_name']} (AppID: {result['app_id']})")
        lines.append(f"原因：{result['error']}")
        return "\n".join(lines)
    
    lines.append(f"✅ {result['game_name']} (AppID: {result['app_id']}) — DLC 检查完成")
    lines.append(f"检查时间：{result['checked_at']}")
    lines.append(f"DLC 总数：{result['total_dlc']}")
    
    # 新增 DLC
    if result["new_dlc"]:
        lines.append(f"\n🆕 新增 DLC ({len(result['new_dlc'])} 个)：")
        for dlc in result["new_dlc"]:
            lines.append(format_dlc_item(dlc))
    else:
        lines.append("\n暂无新 DLC。")
    
    # 完整列表（full mode）
    if result["all_dlc"]:
        lines.append(f"\n📦 全部 DLC ({len(result['all_dlc'])} 个)：")
        for dlc in result["all_dlc"]:
            lines.append(format_dlc_item(dlc))
    
    return "\n".join(lines)


def format_dlc_item(dlc: dict) -> str:
    """格式化单个 DLC 信息"""
    parts = [f"  📦 {dlc['name']}"]
    
    price_str = dlc["price"] or "价格未知"
    if dlc["discount_percent"] > 0:
        price_str += f" (-{dlc['discount_percent']}%)"
    parts.append(f"     💰 {price_str} | 📅 {dlc['release_date']}")
    
    if dlc.get("coming_soon"):
        parts.append("     🔮 即将推出（未上线）")
    
    if dlc.get("reviews"):
        r = dlc["reviews"]
        parts.append(f"     ⭐ {r['positive_rate']}% 好评（{r['total']}条评论）")
    
    return "\n".join(parts)


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Steam DLC 雷达 — 定时检查脚本")
    parser.add_argument("--app_id", type=int, help="Steam AppID")
    parser.add_argument("--game_name", type=str, help="游戏中文名", default="")
    parser.add_argument("--full", action="store_true", help="输出完整 DLC 列表")
    parser.add_argument("--check_all", action="store_true", help="检查所有缓存过的游戏")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    
    args = parser.parse_args()
    
    if args.check_all:
        results = check_all_cached()
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(format_output(r))
                print("---")
    elif args.app_id:
        game_name = args.game_name or f"AppID:{args.app_id}"
        result = check_game_dlc(args.app_id, game_name, full_mode=args.full)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_output(result))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
