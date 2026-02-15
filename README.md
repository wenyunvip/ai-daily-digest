# AI Daily Digest - Kimi Edition 🤖

从 90 个顶级技术博客抓取最新文章，通过 Kimi K2.5 AI 多维评分筛选，生成结构化的每日精选日报。

**原版**: [vigorX777/ai-daily-digest](https://github.com/vigorX777/ai-daily-digest) (TypeScript + Gemini)  
**本版**: Python + Kimi K2.5，零依赖，更轻量

## 快速开始

### 方式 1: 交互式配置（推荐首次使用）

```bash
# 1. 首次运行配置向导
python3 scripts/digest.py --setup

# 2. 之后直接运行（使用配置好的参数）
python3 scripts/digest.py
```

### 方式 2: 环境变量

```bash
# 设置环境变量
export MOONSHOT_API_KEY="your-api-key"

# 运行
python3 scripts/digest.py --hours 48 --top-n 15
```

### 方式 3: 命令行参数

```bash
python3 scripts/digest.py \
  --api-key "your-api-key" \
  --hours 48 \
  --top-n 15 \
  --output ./digest.md
```

## 功能特性

- 🤖 **AI 评分** - Kimi 从相关性、质量、时效性三维度评分
- 📝 **结构化摘要** - 4-6 句覆盖核心问题→关键论点→结论
- 🌐 **双语标题** - 中文翻译 + 原文保留
- 🏷️ **智能分类** - 6 大类别自动归类
- 📈 **趋势洞察** - 每日宏观技术趋势总结
- 🔥 **90 个顶级源** - Karpathy 精选 HN 技术博客

## 输出示例

```markdown
# 🚀 技术日报 | 2026年2月15日

## 📝 今日看点
今日技术圈聚焦 AI 安全与开发者工具...

## 🏆 今日必读

### 1. OpenAI 发布新模型
🤖 AI / ML | 评分: 9/10

**摘要**: OpenAI 今日发布...（4-6句详细摘要）

**推荐**: 所有 AI 从业者必读的突破性进展

🏷️ **标签**: LLM, OpenAI, GPT-4
```

## 信息源

90 个 RSS 源精选自 Hacker News 最受欢迎的独立技术博客：

- Simon Willison (AI/数据)
- Paul Graham (创业/随笔)  
- Dan Abramov (React/前端)
- Gwern (深度研究)
- Krebs on Security (网络安全)
- Mitchell Hashimoto (DevOps)
- Troy Hunt (安全)
- ... (共 90 个)

## 参数说明

| 参数 | 说明 | 默认 |
|------|------|------|
| `--hours` | 时间窗口 | 48 |
| `--top-n` | 精选数量 | 15 |
| `--output` | 输出文件 | ./digest.md |
| `--api-key` | API Key | 必填 |
| `--gateway` | 网关 URL | 可选 |

## 技术栈

- **Python 3.8+** - 纯标准库，零依赖
- **Kimi K2.5** - Moonshot AI API
- **并发抓取** - 10 路 RSS 并发
- **智能解析** - RSS 2.0 + Atom 双兼容

## 与原版对比

| 特性 | 原版 | 本版 |
|------|------|------|
| 语言 | TypeScript | Python |
| 运行时 | Bun | Python 3.8+ |
| AI | Gemini | Kimi K2.5 |
| 依赖 | 零 | 零 |
| 安装 | npx -y bun | python3 digest.py |

## License

MIT (based on original by @vigorX777)
