# m2c-pipeline

> 把 Markdown 里的 Mermaid 图，变成 Chiikawa 风格的可爱教育插画

## 通过 CC Switch 安装

1. 打开 CC Switch → Skills → Add Repository
2. 填入 `leahana/m2c-pipeline`，Branch 填 `skill`
3. 安装后即可在 Claude Code 中使用 `m2c-pipeline` skill

## 快速开始

```bash
# 1. 安装依赖
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. 配置凭据
cp .env.example .env
# 编辑 .env，填入 M2C_PROJECT_ID（必填）和 GOOGLE_APPLICATION_CREDENTIALS（推荐）

# 3. 离线验证（不调用云端，推荐先跑一次）
python -m m2c_pipeline <input.md> --dry-run --translation-mode fallback

# 4. 正式生成图片
python -m m2c_pipeline <input.md> --translation-mode vertex --output-dir ./output
```

## 常用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--template` | 风格模板 | `chiikawa` |
| `--translation-mode` | `vertex`（云端）或 `fallback`（离线）| `vertex` |
| `--aspect-ratio` | 图片宽高比 | `1:1` |
| `--output-dir` | 输出目录 | `./output` |
| `--dry-run` | 跳过图片生成 | 关 |
| `--max-workers` | 并发数 | `2` |

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `M2C_PROJECT_ID` | 是 | GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | 否 | ADC JSON 路径；未设置时回退到系统 ADC |

> 本 skill 只走 Vertex AI API，不支持 Google AI Studio 或 API key。

## License

[MIT](./LICENSE)
