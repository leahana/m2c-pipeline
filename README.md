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
- 🌸 **Chiikawa 风格** — Gemini 文本模型理解图结构，生成可爱教育插画提示词；自动按节点类型分配吉伊 / 八千代 / 乌萨奇角色，保证视觉多样性
- 🖼️ **Vertex AI 生图** — 通过 `google-genai` SDK 调用 Gemini 图片模型
- ⚡ **并发生成** — `ThreadPoolExecutor` 并发，`tqdm` 进度条实时反馈
- 🔁 **自动重试** — `tenacity` 指数退避，Vertex 调用失败时 Translate 和 Paint 阶段都有保护
- 🧪 **离线 dry-run** — `fallback + --dry-run` 可在无云凭据、无项目 ID 的环境里验证提词流程
- 💾 **元数据内嵌** — PNG 文件内嵌 `mermaid_source` / `image_prompt` / `generated_at` 等字段
- 🛡️ **纯 Vertex AI** — 只走 ADC 认证，不依赖 Google AI Studio API key

---

## 📦 Skill 安装（CC Switch）

通过 CC Switch 将此仓库安装为 Claude Code skill：

1. 打开 CC Switch → Skills → Add Repository
2. 填入 `leahana/m2c-pipeline`，Branch 填 `skill`
3. 安装后即可在 Claude Code 中使用 `m2c-pipeline` skill

`skill` 分支在每次 Release 时由 CI 自动发布，仅包含 skill 运行所需文件。

---

## ⚡ 快速开始

```bash
# 1. 克隆 & 安装
git clone https://github.com/leahana/m2c-pipeline.git
cd m2c-pipeline
./scripts/bootstrap_env.sh

# 2. 配置
cp .env.example .env
# 编辑 .env，填入 M2C_PROJECT_ID 和 GOOGLE_APPLICATION_CREDENTIALS

# 3. 离线试跑（不调用云端翻译或图片模型）
./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback

# 4. 正式生成
./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --translation-mode vertex --output-dir ./output
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
├── fixtures/
│   └── minimal-input.md   # skill 发布态 dry-run 输入
├── m2c_pipeline/
│   ├── __main__.py       # CLI 入口
│   ├── pipeline.py       # 流水线编排
│   ├── config.py         # 配置 & .env 加载
│   ├── extractor.py      # Mermaid 提取
│   ├── translator.py     # Gemini 文本翻译
│   ├── painter.py        # Gemini 图片生成
│   ├── storage.py        # PNG 保存
│   ├── version.py        # 版本号
│   └── templates/        # 风格模板（当前：chiikawa）
├── tests/
│   ├── fixtures/
│   ├── test_m2c_config.py
│   ├── test_m2c_cli.py
│   ├── test_m2c_extractor.py
│   ├── test_m2c_pipeline.py
│   ├── test_m2c_storage.py
│   ├── test_m2c_translator.py
│   ├── test_ci_package.py
│   ├── test_skill_spec.py
│   ├── test_governance_audit.py
│   ├── test_check_pr_head.py
│   ├── test_repo_policy.py
│   ├── test_release_tag.py
│   └── smoke_test.py
├── .github/
│   └── workflows/
│       ├── ci.yml                # 单元测试 & 策略校验
│       ├── claude-review.yml     # PR 评论触发 Claude 代码审查
│       ├── governance-audit.yml  # 治理审计
│       └── release-please.yml    # 标准化 release PR + 发布流程
├── CHANGELOG.md                  # release-please 维护的版本日志
├── .release-please-manifest.json # release-please 当前版本基线
├── release-please-config.json    # release-please 仓库配置
├── policy/
│   ├── governance.json           # 治理规则
│   ├── package-allowlist.txt     # 依赖白名单
│   └── skill-contract.json       # skill 合约
├── references/                   # skill 参考文档（按需加载）
├── evals/                        # skill 评估场景
├── scripts/
│   ├── bootstrap_env.sh          # skill 发布态 POSIX 自举入口
│   └── ci/                       # CI 校验脚本
├── .env.example
├── AGENTS.md                     # agent 开发指南
├── SKILL.md                      # Claude Code skill 规范
├── SKILL_README.md               # skill 分支专用 README（发布时替换 README.md）
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
> 如果你通过 skill 让 agent 负责安装，请让它先按 `references/install-python.md` 选择平台安装路径；系统级 Python 安装完成后，再执行 repo-local bootstrap。

---

## 🛠️ 安装与认证

### 安装依赖

```bash
cd m2c-pipeline
./scripts/bootstrap_env.sh
```

Windows（已有兼容 Python 时）的 repo-local bootstrap：

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
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

**离线 dry-run（不调用云端翻译或图片模型，推荐先跑一次）：**

```bash
./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback
```

**生成图片：**

```bash
./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --translation-mode vertex --output-dir ./output
```

**常用参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--template` | 风格模板 | `chiikawa` |
| `--translation-mode` | 翻译模式 | `vertex` |
| `--aspect-ratio` | 图片宽高比（`1:1`/`4:3`/`3:4`/`16:9`/`9:16` 等） | `1:1` |
| `--output-dir` | 输出目录 | `./output` |
| `--max-workers` | 并发数 | `2` |
| `--log-level` | 日志级别 | `INFO` |
| `--version` | 打印版本号并退出 | — |

---

## ⚙️ 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `M2C_PROJECT_ID` | ✅ | — | GCP project ID |
| `M2C_LOCATION` | | `us-central1` | Gemini 文本调用区域 |
| `M2C_GEMINI_MODEL` | | `gemini-2.0-flash` | 文本模型 |
| `M2C_IMAGE_MODEL` | | `gemini-3.1-flash-image-preview` | 图片模型 |
| `M2C_ASPECT_RATIO` | | `1:1` | 图片宽高比，支持 `1:1`/`4:3`/`3:4`/`16:9`/`9:16`/`2:3`/`3:2`/`4:5`/`5:4` |
| `M2C_OUTPUT_DIR` | | `./output` | 输出目录 |
| `M2C_TEMPLATE` | | `chiikawa` | 风格模板 |
| `M2C_TRANSLATION_MODE` | | `vertex` | 翻译模式，`fallback` 仅用于 `--dry-run` |
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
  tests.test_ci_package \
  tests.test_check_pr_head \
  tests.test_repo_policy \
  tests.test_release_tag \
  tests.test_skill_spec \
  tests.test_governance_audit \
  tests.test_m2c_config \
  tests.test_m2c_cli \
  tests.test_m2c_extractor \
  tests.test_m2c_pipeline \
  tests.test_m2c_storage \
  tests.test_m2c_translator
```

离线 smoke test（无需 GCP 凭据）：

```bash
./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback
```

手工集成 smoke test（需要真实 Vertex AI 凭据）：

```bash
python tests/smoke_test.py --input tests/fixtures/test_input.md
python tests/smoke_test.py --input tests/fixtures/test_input.md --with-image
```

---

## 📦 发布工作流

本仓库现在使用 `release-please` 作为标准发版入口，默认流程如下：

1. 开发分支先合到本地 `dev`
2. 从 `dev` 发 PR 到 `main`
3. `dev -> main` 推荐使用 **merge commit**
4. `release-please` 在 `main` 上自动创建 release PR
5. merge release PR 后，自动创建 tag、GitHub Release，并上传通用 zip/sha256 资产

### 约定

- 功能 PR 和 `dev -> main` PR **不再手工修改** `m2c_pipeline/version.py`
- 版本号、`CHANGELOG.md`、tag、GitHub Release 统一由 release PR 管理
- Conventional Commits 作为发版语义来源：
  - `feat:` => minor
  - `fix:` / `perf:` => patch
  - 带 `!` 的 breaking change => major
  - `docs:` / `ci:` / `chore:` 默认不会单独触发新版本

### release PR 说明

- release PR 是自动生成的正常 PR，不是异常分支
- 自动分支名通常为 `release-please--branches--main`
- 首次启用前，需要在仓库 Secrets 中配置 `RELEASE_PLEASE_TOKEN`
- 还需要在仓库 Actions 设置里允许 GitHub Actions 创建和更新 PR

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
