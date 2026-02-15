---
name: ai-daily-digest
description: >
  从 90 个顶级技术博客抓取最新文章，通过 Kimi K2.5 AI 多维评分筛选，生成结构化的每日精选日报。
  替代原版 Gemini 版本，使用 Moonshot/Kimi API。
  Use when user asks for tech news digest, daily tech summary, Hacker News curation.
---

# AI Daily Digest - Kimi Edition 🤖

从 Andrej Karpathy 推荐的 90 个 Hacker News 顶级技术博客中抓取最新文章，通过 Kimi K2.5 AI 多维评分筛选，生成一份结构化的每日精选日报。

## What It Does

### 五步处理流水线

```
RSS 抓取 → 时间过滤 → AI 评分+分类 → AI 摘要+翻译 → 趋势总结
```

1. **RSS 抓取** — 并发抓取 90 个源（10 路并发，15s 超时），兼容 RSS 2.0 和 Atom 格式
2. **时间过滤** — 按指定时间窗口筛选近期文章
3. **AI 评分** — Kimi 从相关性、质量、时效性三个维度打分（1-10），同时完成分类和关键词提取
4. **AI 摘要** — 为 Top N 文章生成结构化摘要（4-6 句）、中文标题翻译、推荐理由
5. **趋势总结** — Kimi 归纳当日技术圈 2-3 个宏观趋势

### 六大分类体系

| 分类 | 覆盖范围 | Emoji |
|------|---------|-------|
| 🤖 AI / ML | AI、机器学习、LLM、深度学习 |
| 🔒 安全 | 安全、隐私、漏洞、加密 |
| ⚙️ 工程 | 软件工程、架构、编程语言、系统设计 |
| 🛠 工具 / 开源 | 开发工具、开源项目、新发布的库/框架 |
| 💡 观点 / 杂谈 | 行业观点、个人思考、职业发展 |
| 📝 其他 | 以上都不太适合的 |

## Usage

### CLI

```bash
# 基础使用（需要 Moonshot API Key）
export MOONSHOT_API_KEY="your-key"
python3 scripts/digest.py --hours 48 --top-n 15 --output ./digest.md

# 使用 OpenClaw Gateway（如果配置了）
python3 scripts/digest.py --hours 24 --top-n 10 \
  --gateway http://localhost:8080 \
  --api-key your-gateway-token \
  --output ~/Desktop/digest.md
```

### Parameters

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--hours` | 时间窗口（24h/48h/72h/7天） | 48 |
| `--top-n` | 精选文章数量 | 15 |
| `--output` | 输出文件路径 | ./digest.md |
| `--api-key` | Kimi/Moonshot API Key | 必填 |
| `--gateway` | OpenClaw Gateway URL | 可选 |

### From Agent Code

```python
from scripts.digest import (
    fetch_all_feeds, score_articles, summarize_articles,
    analyze_trends, generate_markdown, RSS_FEEDS
)

# 1. Fetch articles
articles = fetch_all_feeds(RSS_FEEDS)

# 2. Score with Kimi
scored = score_articles(articles, api_key="your-key")

# 3. Summarize top N
top_articles = sorted(scored, key=lambda x: x['score'], reverse=True)[:15]
summarized = summarize_articles(top_articles, api_key="your-key")

# 4. Analyze trends
trends = analyze_trends(summarized, api_key="your-key")

# 5. Generate markdown
markdown = generate_markdown(summarized, trends, hours=48, top_n=15)
```

## Output Format

生成的 Markdown 文件包含以下板块：

### 📝 今日看点
3-5 句话的宏观趋势总结

### 🏆 今日必读  
Top 3 深度展示：
- 中英双语标题
- 4-6 句结构化摘要
- 一句话推荐理由
- 关键词标签

### 📊 分类速览
按 6 大分类分组的文章列表

## Information Sources

90 个 RSS 源精选自 Hacker News 社区最受欢迎的独立技术博客，包括：

- **Simon Willison** (simonwillison.net) - AI/数据新闻
- **Paul Graham** (paulgraham.com) - 创业/技术随笔
- **Dan Abramov** (overreacted.io) - React/前端
- **Gwern** (gwern.net) - 深度研究/AI
- **Krebs on Security** - 网络安全
- **Mitchell Hashimoto** - 基础设施/DevOps
- **Troy Hunt** - 安全/数据泄露
- **Steve Blank** - 创业方法论
- **Eli Bendersky** - 编程语言
- **Fabien Sanglard** - 游戏/图形编程
- ... (共 90 个源)

完整列表见 `scripts/digest.py` 中的 `RSS_FEEDS`。

## Requirements

- Python 3.8+
- Kimi/Moonshot API Key（[免费获取](https://platform.moonshot.cn/)）
- 网络连接

## Differences from Original

| 特性 | 原版 (TypeScript/Bun/Gemini) | 本版 (Python/Kimi) |
|------|------------------------------|-------------------|
| 运行时 | Bun | Python 3.8+ |
| AI 模型 | Gemini 2.0 Flash | Kimi K2.5 |
| 依赖 | 零依赖 | 零第三方库 |
| 安装 | `npx -y bun` | `python3 digest.py` |
| 并发 | 10 路 RSS + 2 路 AI | 10 路 RSS + 顺序 AI |

## License

MIT (based on original by @vigorX777)
