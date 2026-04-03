# 🌸 m2c-pipeline

> 把 Markdown 里的 Mermaid 图，变成 Chiikawa 风格的可爱教育插画 🐭✨

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-pink?logo=opensourceinitiative&logoColor=white)
![Vertex AI](https://img.shields.io/badge/Powered%20by-Vertex%20AI-4285F4?logo=googlecloud&logoColor=white)

---

## 💡 它做什么

`m2c_pipeline` 是一条单线流水线：自动读取 Markdown 文件 → 提取所有 Mermaid 代码块 → 用 Gemini 翻译成图片提示词 → 调用 Vertex AI 生成 PNG → 写入元数据存档。

```bash
python -m m2c_pipeline path/to/input.md
```

---

## 🎀 特性亮点

- 🔍 **自动提取** — 正则解析 Markdown，支持多个 Mermaid block 批量处理
- 🌸 **Chiikawa 风格** — Gemini 文本模型理解图结构，生成可爱教育插画提示词
- 🖼️ **Vertex AI 生图** — 通过 `google-genai` SDK 调用 Gemini 图片模型
- ⚡ **并发生成** — `ThreadPoolExecutor` 并发，`tqdm` 进度条实时反馈
- 🔁 **自动重试** — `tenacity` 指数退避，Translate 和 Paint 阶段均有 fallback
- 💾 **元数据内嵌** — PNG 文件内嵌 `mermaid_source` / `image_prompt` / `generated_at` 等字段
- 🛡️ **纯 Vertex AI** — 只走 ADC 认证，不依赖 Google AI Studio API key

---

## ⚡ 快速开始

```bash
# 1. 克隆 & 安装
git clone https://github.com/leahana/m2c-pipeline.git
cd m2c-pipeline
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
# 编辑 .env，填入 M2C_PROJECT_ID 和 GOOGLE_APPLICATION_CREDENTIALS

# 3. 试跑（不调用图片模型）
python -m m2c_pipeline tests/fixtures/test_input.md --dry-run

# 4. 正式生成
python -m m2c_pipeline tests/fixtures/test_input.md --output-dir ./output
```

---

## ✨ 流水线说明

四个固定阶段，依次执行：

```text
🔍 Extract  ──→  🌸 Translate  ──→  🖼️ Paint  ──→  💾 Store
```

| 阶段 | 文件 | 说明 |
|------|------|------|
| 🔍 Extract | `extractor.py` | 正则提取 ```` ```mermaid ```` 块，返回 `MermaidBlock` |
| 🌸 Translate | `translator.py` | Gemini 文本模型生成 `ImagePrompt`，失败时用本地 fallback |
| 🖼️ Paint | `painter.py` | Gemini 图片模型生成 PNG 字节 |
| 💾 Store | `storage.py` | 保存 PNG，写入元数据，失败时存 `*_FAILED.txt` |

---

## 🗂️ 项目结构

```text
m2c-pipeline/
├── m2c_pipeline/
│   ├── __main__.py       # CLI 入口
│   ├── pipeline.py       # 流水线编排
│   ├── config.py         # 配置 & .env 加载
│   ├── extractor.py      # Mermaid 提取
│   ├── translator.py     # Gemini 文本翻译
│   ├── painter.py        # Gemini 图片生成
│   ├── storage.py        # PNG 保存
│   └── templates/        # 风格模板（当前：chiikawa）
├── tests/
│   ├── fixtures/
│   ├── test_m2c_config.py
│   ├── test_m2c_extractor.py
│   ├── test_m2c_storage.py
│   └── smoke_test.py
├── .env.example
├── LICENSE
└── requirements.txt
```

---

## ✅ 前置条件

运行前确认以下条件，agent 和人类都按同一套要求执行：

- 🐍 Python 3.11+
- ☁️ 本地安装 `gcloud` CLI
- 🔑 可用的 Google Cloud Application Default Credentials (ADC)
- 📦 已启用 Vertex AI API（`aiplatform.googleapis.com`）
- 🆔 一个可用的 GCP project，并设置 `M2C_PROJECT_ID`

> 本项目只走 **Vertex AI API**，不支持也不需要 Google AI Studio / Gemini Developer API key。

---

## 🛠️ 安装与认证

### 安装依赖

```bash
cd m2c-pipeline
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 配置 `.env`

```bash
cp .env.example .env
```

推荐的 `.env`：

```dotenv
M2C_PROJECT_ID=YOUR_PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/adc-or-service-account.json
```

如果没有 `GOOGLE_APPLICATION_CREDENTIALS`，会自动回退到系统 ADC：

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

> 💡 `.env` 只用于本地开发，不要提交到版本控制。

<details>
<summary>📖 ADC 认证方式详解（点击展开）</summary>

两种 JSON 凭据文件的区别：

| 类型 | 来源 | 适合场景 |
|------|------|----------|
| 用户 ADC JSON | `gcloud auth application-default login` | 本地开发 |
| 服务账号 JSON key | Cloud Console / `gcloud iam service-accounts keys create` | CI/CD、生产环境 |

优先级：设置了 `GOOGLE_APPLICATION_CREDENTIALS` → 读取指定 JSON；未设置 → 回退系统 ADC。

⚠️ 两种文件都不应该提交到仓库，服务账号 JSON key 尤其敏感，只在明确需要时使用。

</details>

---

## 🚀 使用方式

**只生成提示词，不调用图片模型（推荐先跑一次）：**

```bash
python -m m2c_pipeline tests/fixtures/test_input.md --dry-run
```

**生成图片：**

```bash
python -m m2c_pipeline tests/fixtures/test_input.md --output-dir ./output
```

**常用参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--template` | 风格模板 | `chiikawa` |
| `--aspect-ratio` | 图片宽高比 | `1:1` |
| `--output-dir` | 输出目录 | `./output` |
| `--max-workers` | 并发数 | `2` |
| `--log-level` | 日志级别 | `INFO` |

---

## ⚙️ 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `M2C_PROJECT_ID` | ✅ | — | GCP project ID |
| `M2C_LOCATION` | | `us-central1` | Gemini 文本调用区域 |
| `M2C_GEMINI_MODEL` | | `gemini-2.0-flash` | 文本模型 |
| `M2C_IMAGE_MODEL` | | `gemini-3.1-flash-image-preview` | 图片模型 |
| `M2C_ASPECT_RATIO` | | `1:1` | 图片宽高比 |
| `M2C_OUTPUT_DIR` | | `./output` | 输出目录 |
| `M2C_TEMPLATE` | | `chiikawa` | 风格模板 |
| `M2C_MAX_WORKERS` | | `2` | 并发数 |
| `M2C_REQUEST_TIMEOUT` | | `600` | 请求超时（秒） |
| `M2C_LOG_LEVEL` | | `INFO` | 日志级别 |

---

## 📂 输出说明

成功生成时，每个 Mermaid block 输出一个 PNG 🖼️，并内嵌以下元数据：

```text
mermaid_source   原始 Mermaid 代码
image_prompt     发送给图片模型的提示词
generated_at     生成时间戳
block_index      在文档中的位置
diagram_type     图类型（graph / sequenceDiagram / ...）
```

生成失败时，保存 `*_FAILED.txt` 📄，包含原始 Mermaid 和最终提示词，便于手工复查。

### 🔧 常见问题排查

1. ❓ `M2C_PROJECT_ID` 是否设置正确？
2. ❓ `GOOGLE_APPLICATION_CREDENTIALS` 路径是否存在且 JSON 有效？
3. ❓ 系统 ADC 是否可用（`gcloud auth application-default print-access-token`）？
4. ❓ 服务账号冒充场景：当前用户是否有 `roles/iam.serviceAccountTokenCreator`？
5. ❓ `aiplatform.googleapis.com` 是否已启用？
6. ❓ 当前模型和区域是否仍可用？

---

## 🧪 测试

基础单测（无需 GCP 凭据）：

```bash
python -m unittest \
  tests.test_m2c_config \
  tests.test_m2c_extractor \
  tests.test_m2c_storage
```

手工集成 smoke test（需要真实 Vertex AI 凭据）：

```bash
python tests/smoke_test.py --input tests/fixtures/test_input.md
python tests/smoke_test.py --input tests/fixtures/test_input.md --with-image
```

---

## 🔒 安全说明

- 🚫 不在仓库中存储 API key、token、服务账号 JSON
- 📁 `.env` 仅本地使用，不提交
- 🖼️ 生成图片、失败日志、测试输出均属本地产物，不提交
- 📋 共享配置只共享 `.env.example`
- ⛔ 明确禁止 `GOOGLE_API_KEY`、`GEMINI_API_KEY` 或 `genai.Client(api_key=...)`

---

## 📄 License

[MIT](./LICENSE) © 2026 leahana
