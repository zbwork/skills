#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam 跨区比价脚本（Skill 专用）
输入游戏名，输出各区定价对比 + 实际成本估算，纯文本结果到 stdout
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import argparse
import requests
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# 区域配置
# ============================================================

REGIONS = [
    {"cc": "cn", "name": "中国", "flag": "🇨🇳", "currency": "CNY", "premium_low": 1.00, "premium_high": 1.00, "card_supply": "direct", "note": "支付宝/微信直付，无需充值卡"},
    {"cc": "ar", "name": "阿根廷", "flag": "🇦🇷", "currency": "USD", "premium_low": 0.94, "premium_high": 1.00, "card_supply": "good", "note": "电商平台搜\"Steam 美元充值卡\"查看最新汇率"},
    {"cc": "tr", "name": "土耳其", "flag": "🇹🇷", "currency": "USD", "premium_low": 0.94, "premium_high": 1.00, "card_supply": "good", "note": "电商平台搜\"Steam 美元充值卡\"查看最新汇率"},
    {"cc": "br", "name": "巴西", "flag": "🇧🇷", "currency": "BRL", "premium_low": 1.04, "premium_high": 1.10, "card_supply": "good", "note": "电商平台搜\"Steam 巴西充值卡\"查看最新汇率"},
    {"cc": "in", "name": "印度", "flag": "🇮🇳", "currency": "INR", "premium_low": 0.85, "premium_high": 0.92, "card_supply": "good", "note": "电商平台搜\"Steam 印度充值卡\"查看最新汇率"},
    {"cc": "kz", "name": "哈萨克斯坦", "flag": "🇰🇿", "currency": "KZT", "premium_low": 0.99, "premium_high": 1.05, "card_supply": "good", "note": "电商平台搜\"Steam 哈萨克充值卡\"查看最新汇率"},
    {"cc": "ua", "name": "乌克兰", "flag": "🇺🇦", "currency": "UAH", "premium_low": 0.90, "premium_high": 0.97, "card_supply": "good", "note": "电商平台搜\"Steam 乌克兰充值卡\"查看最新汇率"},
    {"cc": "za", "name": "南非", "flag": "🇿🇦", "currency": "ZAR", "premium_low": 1.05, "premium_high": 1.12, "card_supply": "good", "note": "电商平台搜\"Steam 南非充值卡\"查看最新汇率"},
    {"cc": "co", "name": "哥伦比亚", "flag": "🇨🇴", "currency": "COP", "premium_low": 1.14, "premium_high": 1.22, "card_supply": "poor", "note": "⚠️ 充值卡几乎无人售卖，不建议选择"},
    {"cc": "us", "name": "美国", "flag": "🇺🇸", "currency": "USD", "premium_low": 0.94, "premium_high": 1.00, "card_supply": "good", "note": "电商平台搜\"Steam 美元充值卡\"查看最新汇率"},
    {"cc": "hk", "name": "香港", "flag": "🇭🇰", "currency": "HKD", "premium_low": 1.00, "premium_high": 1.00, "card_supply": "credit_card", "note": "⚠️ 无充值卡，需Visa/Master国际信用卡下单"},
    {"cc": "jp", "name": "日本", "flag": "🇯🇵", "currency": "JPY", "premium_low": 0.91, "premium_high": 0.98, "card_supply": "good", "note": "电商平台搜\"Steam 日本充值卡\"查看最新汇率"},
]


# ============================================================
# 汇率获取
# ============================================================

def get_exchange_rates():
    """获取各币种对人民币汇率"""
    currencies = list(set(r["currency"] for r in REGIONS if r["currency"] != "CNY"))
    rates = {"CNY": 1.0}

    # 尝试方案1：exchangerate-api（免费，无需key）
    try:
        url = "https://open.er-api.com/v6/latest/CNY"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("result") == "success":
            cny_rates = data.get("rates", {})
            for cur in currencies:
                if cur in cny_rates and cny_rates[cur] > 0:
                    rates[cur] = 1.0 / cny_rates[cur]  # 转为 1外币=X人民币
            print(f"  汇率获取成功（exchangerate-api）", file=sys.stderr)
            return rates
    except Exception as e:
        print(f"  exchangerate-api 失败: {e}", file=sys.stderr)

    # 兜底：硬编码近似汇率（2026.04 参考值）
    print(f"  使用兜底汇率", file=sys.stderr)
    fallback = {
        "USD": 7.20, "BRL": 1.30, "INR": 0.085,
        "KZT": 0.015, "UAH": 0.17, "ZAR": 0.39,
        "COP": 0.0017, "HKD": 0.92, "JPY": 0.047,
    }
    rates.update(fallback)
    return rates


# ============================================================
# Steam API 调用
# ============================================================

def search_game(game_name):
    """搜索游戏，返回 appid 和官方名称"""
    try:
        url = "https://store.steampowered.com/api/storesearch"
        params = {"term": game_name, "cc": "cn", "l": "schinese"}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return None, None

        # 优先精确匹配
        target = game_name.lower()
        for item in items:
            if item.get("name", "").lower() == target:
                return item["id"], item["name"]

        # 退回第一个
        return items[0]["id"], items[0]["name"]
    except Exception as e:
        print(f"  搜索游戏失败: {e}", file=sys.stderr)
        return None, None


def get_region_price(appid, cc):
    """获取指定区域的价格信息"""
    try:
        url = "https://store.steampowered.com/api/appdetails"
        params = {"appids": str(appid), "cc": cc, "l": "english"}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        app_data = data.get(str(appid), {})
        if not app_data.get("success"):
            return None

        game_data = app_data.get("data", {})
        price_overview = game_data.get("price_overview")

        if game_data.get("is_free"):
            return {
                "available": True,
                "is_free": True,
                "price_raw": 0,
                "price_formatted": "免费",
                "currency": game_data.get("price_overview", {}).get("currency", ""),
                "discount_percent": 0,
            }

        if not price_overview:
            # 该区可能无法购买
            return {"available": False}

        return {
            "available": True,
            "is_free": False,
            "price_raw": price_overview.get("initial", 0),  # 单位：分
            "price_final": price_overview.get("final", 0),
            "price_formatted": price_overview.get("initial_formatted") or price_overview.get("final_formatted", ""),
            "currency": price_overview.get("currency", ""),
            "discount_percent": price_overview.get("discount_percent", 0),
        }
    except Exception as e:
        print(f"  获取 {cc} 区价格失败: {e}", file=sys.stderr)
        return None


def get_game_details(appid):
    """获取游戏基本信息（名称、类型、中文支持等）"""
    try:
        url = "https://store.steampowered.com/api/appdetails"
        params = {"appids": str(appid), "cc": "cn", "l": "schinese"}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        app_data = data.get(str(appid), {})
        if not app_data.get("success"):
            return None

        game_data = app_data.get("data", {})
        languages = game_data.get("supported_languages", "")

        return {
            "name": game_data.get("name", ""),
            "type": game_data.get("type", ""),
            "has_chinese": "简体中文" in languages or "Simplified Chinese" in languages,
            "header_image": game_data.get("header_image", ""),
        }
    except Exception as e:
        print(f"  获取游戏详情失败: {e}", file=sys.stderr)
        return None


# ============================================================
# 核心比价逻辑
# ============================================================

def compare_prices(appid, game_name):
    """并发查询各区价格，计算实际成本"""
    print(f"  获取汇率...", file=sys.stderr)
    rates = get_exchange_rates()

    print(f"  并发查询 {len(REGIONS)} 个区域价格...", file=sys.stderr)
    results = []

    # 并发请求各区价格
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {}
        for region in REGIONS:
            future = executor.submit(get_region_price, appid, region["cc"])
            futures[future] = region

        for future in as_completed(futures):
            region = futures[future]
            price_data = future.result()

            if price_data is None or not price_data.get("available"):
                results.append({
                    "region": region,
                    "available": False,
                    "reason": "该区未上架或无法购买",
                })
                print(f"    {region['flag']} {region['name']}: 不可购买", file=sys.stderr)
                continue

            if price_data.get("is_free"):
                results.append({
                    "region": region,
                    "available": True,
                    "is_free": True,
                    "price_cny": 0,
                    "cost_low": 0,
                    "cost_high": 0,
                })
                print(f"    {region['flag']} {region['name']}: 免费", file=sys.stderr)
                continue

            # 计算人民币价格
            currency = price_data["currency"]
            price_raw = price_data["price_raw"] / 100.0  # 分转元

            rate = rates.get(currency)
            if rate is None:
                print(f"    {region['flag']} {region['name']}: 未知货币 {currency}", file=sys.stderr)
                results.append({
                    "region": region,
                    "available": False,
                    "reason": f"未知货币 {currency}",
                })
                continue

            price_cny = price_raw * rate  # 本币价格 × 汇率 = 人民币价格

            # 实际成本 = 人民币定价 × 充值卡汇率
            if region["cc"] == "cn":
                cost_low = price_cny
                cost_high = price_cny
            else:
                cost_low = price_cny * region["premium_low"]
                cost_high = price_cny * region["premium_high"]

            discount = price_data.get("discount_percent", 0)
            final_price_raw = price_data.get("price_final", price_data["price_raw"]) / 100.0

            results.append({
                "region": region,
                "available": True,
                "is_free": False,
                "currency": currency,
                "price_raw": price_raw,
                "price_formatted": price_data["price_formatted"],
                "price_cny": price_cny,
                "cost_low": cost_low,
                "cost_high": cost_high,
                "discount_percent": discount,
                "final_price_raw": final_price_raw,
                "final_price_cny": final_price_raw * rate,
            })

            print(f"    {region['flag']} {region['name']}: {currency} {price_raw:.2f} → ¥{price_cny:.0f} (实际 ¥{cost_low:.0f}-{cost_high:.0f})", file=sys.stderr)

    # 按实际成本低值排序（可购买的排前面）
    available = [r for r in results if r.get("available") and not r.get("is_free")]
    unavailable = [r for r in results if not r.get("available")]
    free_list = [r for r in results if r.get("available") and r.get("is_free")]

    available.sort(key=lambda x: x["cost_low"])

    return available, unavailable, free_list


# ============================================================
# 格式化输出
# ============================================================

def format_output(game_name, game_details, available, unavailable, free_list):
    """格式化比价结果为纯文本"""
    lines = []
    lines.append(f"🎮 Steam 跨区比价 —— {game_name}")
    lines.append(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if game_details:
        chinese = "✅ 支持中文" if game_details.get("has_chinese") else "❌ 不支持中文"
        lines.append(f"中文支持: {chinese}")
    lines.append("")

    if free_list:
        lines.append("🆓 该游戏在以下区域免费：")
        for item in free_list:
            r = item["region"]
            lines.append(f"  {r['flag']} {r['name']}")
        lines.append("")

    if not available:
        lines.append("⚠️ 该游戏在所有比价区域均无定价或不可购买。")
        return "\n".join(lines)

    # 找到国区价格作为基准
    cn_item = next((r for r in available if r["region"]["cc"] == "cn"), None)
    cn_price = cn_item["price_cny"] if cn_item else None
    cn_rank = next((idx + 1 for idx, item in enumerate(available) if item["region"]["cc"] == "cn"), None)

    # 国区基准摘要
    if cn_item:
        if cn_rank == 1:
            lines.append(f"📍 国区基准：¥{cn_item['cost_low']:.0f}（排第 {cn_rank}/{len(available) + len(unavailable)}）✅ 国区已是最低价，无需跨区购买")
        else:
            lines.append(f"📍 国区基准：¥{cn_item['cost_low']:.0f}（排第 {cn_rank}/{len(available) + len(unavailable)}）")
    elif unavailable and any(item["region"]["cc"] == "cn" for item in unavailable):
        lines.append("📍 国区：❌ 不可购买（可能涉及内容审核或发行商未上架）")
    lines.append("")

    # Markdown 网格表格输出
    lines.append("💰 全区比价排行")
    lines.append("")
    # 表头
    lines.append("| 排名 | 区域 | 预估成本(¥) | vs国区 | 地区定价 | 充值卡汇率参考值 | 备注 |")
    lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---|")

    for idx, item in enumerate(available):
        r = item["region"]
        rank = idx + 1
        is_cn = r["cc"] == "cn"

        # 排名列
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
        if is_cn:
            medal = f"#{rank}"

        # 区域列
        region_str = f"{r['flag']} {r['name']}"
        if is_cn:
            region_str += " ◀"

        # 定价列
        price_str = f"{item['currency']} {item['price_raw']:.2f}"

        # 溢价列
        if is_cn or r.get("card_supply") == "credit_card":
            premium_str = "—"
        else:
            premium_str = f"×{r['premium_low']:.2f}-{r['premium_high']:.2f}"

        # 预估成本列
        if is_cn:
            cost_str = f"¥{item['cost_low']:.0f}"
        elif item['cost_low'] == item['cost_high']:
            cost_str = f"¥{item['cost_low']:.0f}"
        else:
            cost_str = f"¥{item['cost_low']:.0f}-{item['cost_high']:.0f}"

        # vs国区列
        if is_cn:
            vs_cn_str = "**基准**"
        elif cn_price and cn_price > 0:
            save_high = cn_price - item["cost_low"]
            save_low = cn_price - item["cost_high"]
            if save_low > 0:
                vs_cn_str = f"省¥{save_low:.0f}-{save_high:.0f}"
            elif save_high > 0:
                vs_cn_str = f"省≈¥{save_high:.0f}"
            else:
                vs_cn_str = f"贵¥{abs(save_high):.0f}"
        else:
            vs_cn_str = "—"

        # 备注列
        note_str = r.get("note", "")

        # 折扣信息追加到备注
        if item.get("discount_percent", 0) > 0:
            discount_note = f"🏷️ -{item['discount_percent']}%"
            note_str = f"{discount_note} {note_str}" if note_str else discount_note

        lines.append(f"| {medal} | {region_str} | {cost_str} | {vs_cn_str} | {price_str} | {premium_str} | {note_str} |")

    # 不可购买的区域（如果有）
    if unavailable:
        for item in unavailable:
            r = item["region"]
            region_str = f"{r['flag']} {r['name']}"
            lines.append(f"| — | {region_str} | — | — | ❌ 不可购买 | — | 该区未上架 |")

    lines.append("")

    # 说明
    lines.append("📌 **说明**")
    lines.append("- 💰 由于充值卡汇率实时波动，预估成本仅供参考，下单前请到电商平台确认最新卡价")
    lines.append("- 💱 充值卡汇率参考值 = 买卡实付 ÷ 卡面金额")
    lines.append("- 🔗 阿根廷/土耳其/美国三区虽然国家不同，但 Steam 统一以美元结算，所以都搜同一种美元充值卡即可")
    lines.append("- ⚠️ 跨区风险：频繁切换商店区域可能被 V 社强制转回国区（遣返），届时 **3个月内无法再换区**，钱包余额按汇率折损；多次触发还可能收到红信（账号交易受限）。社区经验来看，低频切区（一年几次）风险较低，但请自行权衡收益与风险")

    return "\n".join(lines)


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Steam 跨区比价工具")
    parser.add_argument("game", nargs="+", help="游戏名称（支持中英文）")
    args = parser.parse_args()

    game_name = " ".join(args.game)
    print(f"【Steam 跨区比价】搜索: {game_name}", file=sys.stderr)

    # 1. 搜索游戏
    print(f"  搜索游戏...", file=sys.stderr)
    appid, official_name = search_game(game_name)
    if not appid:
        print(f"❌ 未找到游戏「{game_name}」，请检查游戏名称是否正确。")
        print(f"💡 建议：尝试使用英文名或 Steam 商店中的完整名称。")
        return

    display_name = official_name or game_name
    print(f"  找到: {display_name} (appid: {appid})", file=sys.stderr)

    # 2. 获取游戏详情
    game_details = get_game_details(appid)

    # 3. 并发比价
    available, unavailable, free_list = compare_prices(appid, display_name)

    # 4. 格式化输出
    output = format_output(display_name, game_details, available, unavailable, free_list)
    print(output)


if __name__ == "__main__":
    main()
