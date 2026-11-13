# Steam Store API 参考

DLC雷达Skill用到的Steam API汇总。所有接口免费、无需登录、无需API Key。

> ⚠️ **国内网络可达性**：`store.steampowered.com` 域名未被墙，但国内访问**不稳定**（丢包、超时、速度慢）。建议用户开启加速器以获得稳定体验。所有 API 调用统一通过预置脚本 `scripts/check_dlc.py` 执行（内置3次重试 + 8秒超时 + 指数退避），**禁止 AI 临时生成脚本调用**。

---

## 1. 游戏搜索（游戏名 → AppID）

**用途**：将用户输入的游戏名匹配到Steam AppID

**接口**：
```
GET https://store.steampowered.com/api/storesearch/?term={游戏名}&cc=cn&l=schinese
```

**参数**：
| 参数 | 说明 |
|------|------|
| term | 搜索关键词（游戏名） |
| cc | 地区代码，cn=中国 |
| l | 语言，schinese=简体中文 |

**返回示例**：
```json
{
  "total": 1,
  "items": [
    {
      "type": "app",
      "name": "ELDEN RING",
      "id": 1245620,
      "tiny_image": "https://...",
      "price": { "final": 29800, "currency": "CNY" }
    }
  ]
}
```

**注意**：
- 中文名搜索效果一般，英文名更准确
- 返回结果按相关性排序，取第一个通常最准
- 有些游戏中英文名差异大（如"艾尔登法环" vs "ELDEN RING"），可能需要两次搜索

---

## 2. 游戏详情（获取DLC列表）

**用途**：获取某游戏的DLC AppID列表及基本信息

**接口**：
```
GET https://store.steampowered.com/api/appdetails?appids={appid}&cc=cn&l=schinese
```

**参数**：
| 参数 | 说明 |
|------|------|
| appids | Steam AppID，多个用逗号分隔（建议单个查询） |
| cc | 地区代码 |
| l | 语言 |

**返回关键字段**：
```json
{
  "1245620": {
    "success": true,
    "data": {
      "type": "game",
      "name": "ELDEN RING",
      "steam_appid": 1245620,
      "dlc": [2778580],
      "price_overview": {
        "currency": "CNY",
        "initial": 29800,
        "final": 29800,
        "discount_percent": 0,
        "initial_formatted": "¥298.00",
        "final_formatted": "¥298.00"
      },
      "release_date": {
        "coming_soon": false,
        "date": "2022 年 2 月 25 日"
      }
    }
  }
}
```

**DLC相关字段说明**：
| 字段路径 | 说明 |
|---------|------|
| data.dlc | DLC的AppID数组 |
| data.type | 类型（"game"=本体, "dlc"=DLC） |
| data.name | 游戏/DLC名称 |
| data.price_overview | 价格信息（含折扣） |
| data.release_date | 发行日期 |
| data.short_description | 简短描述 |
| data.metacritic | Metacritic评分（如有） |

---

## 3. DLC详情（逐个查询每个DLC）

**用途**：获取单个DLC的详细信息

**接口**：与游戏详情相同
```
GET https://store.steampowered.com/api/appdetails?appids={dlc_appid}&cc=cn&l=schinese
```

**补充说明**：
- DLC的返回结构与游戏相同
- 关注 `price_overview`（价格+折扣）和 `release_date`
- DLC的 `type` 字段为 `"dlc"`
- DLC的 `fullgame` 字段包含所属本体游戏信息

---

## 4. Steam评测（获取好评率和评价摘要）

**用途**：获取DLC的玩家评测数据

**接口**：
```
GET https://store.steampowered.com/appreviews/{appid}?json=1&language=schinese&num_per_page=10&filter=recent
```

**参数**：
| 参数 | 说明 |
|------|------|
| appid | 路径参数，游戏/DLC的AppID |
| json | 返回JSON格式 |
| language | 评测语言筛选 |
| num_per_page | 每页评测数（最多100） |
| filter | 排序方式：recent/updated/all |

**返回关键字段**：
```json
{
  "success": 1,
  "query_summary": {
    "num_reviews": 10,
    "review_score": 7,
    "review_score_desc": "多半好评",
    "total_positive": 85000,
    "total_negative": 15000,
    "total_reviews": 100000
  },
  "reviews": [
    {
      "recommendationid": "...",
      "author": { "steamid": "..." },
      "review": "评测正文内容...",
      "voted_up": true,
      "votes_up": 100,
      "timestamp_created": 1700000000
    }
  ]
}
```

**好评率计算**：
```
好评率 = total_positive / total_reviews * 100
```

**review_score_desc 对照表**：
| 值 | 中文 | 好评率范围 |
|----|------|-----------|
| Overwhelmingly Positive | 好评如潮 | ≥95% & ≥500条 |
| Very Positive | 特别好评 | ≥80% & ≥50条 |
| Positive | 好评 | ≥80% & <50条 |
| Mostly Positive | 多半好评 | 70%-79% |
| Mixed | 褒贬不一 | 40%-69% |
| Mostly Negative | 多半差评 | 20%-39% |
| Negative / Very Negative / Overwhelmingly Negative | 差评系列 | <20% |

---

## 5. 频率限制与注意事项

- Steam Store API **没有官方文档的频率限制说明**，但建议：
  - 单次批量查询不超过 5-10 个DLC
  - 每次请求间隔 200-500ms
  - 定时任务一天一次完全够用，不需要更频繁
- `cc=cn` 获取国区价格，`l=schinese` 获取中文信息
- 部分游戏/DLC在国区不可用，`appdetails` 返回 `success: false`
- 免费DLC的 `is_free` 为 true，不会有 `price_overview` 字段
