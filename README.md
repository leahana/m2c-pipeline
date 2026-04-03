# m2c-pipeline

`m2c_pipeline` 是一个单线 Mermaid 转图片流水线：从 Markdown 中提取 Mermaid 代码块，用 Gemini 生成 Chiikawa 风格教育插画提示词，再通过 Vertex AI backend 生成 PNG，并写入可追踪的元数据。

当前对外公开接口以 CLI 为准：

```bash
python -m m2c_pipeline path/to/input.md
```

## 功能概览

流水线固定为四个阶段：

```text
Extract -> Translate -> Paint -> Store
```

- `Extract`: 从 Markdown 提取 ```` ```mermaid ```` 代码块
- `Translate`: 用 Gemini 文本模型把 Mermaid 结构翻译成图片提示词
- `Paint`: 用 `google-genai` + Vertex AI backend 生成图片
- `Store`: 保存 PNG，并写入 Mermaid 原文、提示词、时间戳等元数据

## 项目结构

```text
m2c-pipeline/
├── m2c_pipeline/
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

## 前置条件

运行前需要满足这些条件，agent 和人类都按同一套要求执行：

1. 安装 Python 3.11 或更高版本
2. 本地安装 `gcloud` CLI
3. 准备可用的 Google Cloud Application Default Credentials (ADC)
4. 选定一个可用的 GCP project
5. 启用 Vertex AI API
6. 设置 `M2C_PROJECT_ID`

推荐的最终方案：

1. 在 `.env` 中设置 `M2C_PROJECT_ID`
2. 优先在 `.env` 中设置 `GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/adc-or-service-account.json`
3. 如果未设置 `GOOGLE_APPLICATION_CREDENTIALS`，则自动回退到系统 ADC

本项目只允许使用 Vertex AI API，不允许使用 Google AI Studio / Gemini Developer API。
不要配置或依赖 `GOOGLE_API_KEY`、`GEMINI_API_KEY`、`genai.Client(api_key=...)`。

这里的“系统 ADC”包括：

1. 本机 `gcloud auth application-default login` 生成的 ADC 文件
2. 本机 `gcloud auth application-default login --impersonate-service-account=...` 生成的 ADC 文件
3. 云上运行环境附加的服务账号 ADC

推荐理解方式：

- `.env` 负责项目配置和显式指定凭据路径
- `GOOGLE_APPLICATION_CREDENTIALS` 负责告诉 Google SDK 去读哪个 ADC JSON
- 如果 `.env` 没有指定 `GOOGLE_APPLICATION_CREDENTIALS`，则回退到系统 ADC

## 安装

```bash
cd m2c-pipeline

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

复制环境变量模板：

```bash
cp .env.example .env
```

说明：

- 仓库会在运行时自动加载当前目录或仓库根目录下的 `.env`
- `.env` 只用于本地开发，不应该提交到版本控制
- 本项目不使用 Google AI Studio / Gemini Developer API 的 API key
- 本项目只调用 Vertex AI API
- 推荐在 `.env` 中显式设置 `GOOGLE_APPLICATION_CREDENTIALS`
- 如果 `.env` 未设置 `GOOGLE_APPLICATION_CREDENTIALS`，则回退到系统 ADC

推荐的 `.env` 示例：

```dotenv
M2C_PROJECT_ID=YOUR_PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/adc-or-service-account.json
```

关于 JSON 凭据文件，需要区分两类：

1. 用户 ADC JSON
   - 通常由 `gcloud auth application-default login` 生成
   - 默认保存在本机的 Google Cloud ADC 标准位置
   - 适合本地开发，但仍然依赖 `gcloud` 来初始化这份凭据
2. 服务账号 JSON key
   - 不通过 `gcloud auth application-default login` 生成
   - 通常来自 Google Cloud Console 或 `gcloud iam service-accounts keys create`
   - 可以直接配合 `GOOGLE_APPLICATION_CREDENTIALS` 使用，运行时不依赖当前 `gcloud` CLI 登录账号

这两种方式可以共存，优先级如下：

1. 如果设置了 `GOOGLE_APPLICATION_CREDENTIALS`，SDK 优先读取它指向的 JSON 文件
2. 如果没有设置，再回退到本机默认 ADC 文件

对本项目来说，推荐的理解方式是：

- `.env` 负责项目配置，例如 `M2C_PROJECT_ID`
- `.env` 也可以显式指定 `GOOGLE_APPLICATION_CREDENTIALS`
- ADC JSON 负责 Google Cloud 身份认证
- 如果你希望运行时尽量脱离 `gcloud` CLI 当前登录状态，优先在 `.env` 中指定 `GOOGLE_APPLICATION_CREDENTIALS`
- 如果不想在项目里绑定凭据路径，就依赖系统 ADC 作为回退

安全提醒：

- 不要提交用户 ADC JSON
- 不要提交服务账号 JSON key
- 服务账号 JSON key 比用户 ADC 文件更敏感，只在明确需要时使用

如果你需要初始化系统 ADC，常用命令如下：

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

## 使用方式

只提取 Mermaid 并生成提示词，不调用图片模型：

```bash
python -m m2c_pipeline tests/fixtures/test_input.md --dry-run
```

真正生成图片：

```bash
python -m m2c_pipeline tests/fixtures/test_input.md --output-dir ./output
```

常见参数：

- `--template`: 当前默认也是唯一模板 `chiikawa`
- `--aspect-ratio`: 覆盖所有图片宽高比
- `--output-dir`: 指定输出目录
- `--max-workers`: 控制并发块数
- `--log-level`: `DEBUG | INFO | WARNING | ERROR`

## 关键配置

主要环境变量：

- `M2C_PROJECT_ID`: 必填，GCP project id
- `M2C_LOCATION`: Gemini 文本调用区域，默认 `us-central1`
- `M2C_GEMINI_MODEL`: 默认 `gemini-2.0-flash`
- `M2C_IMAGE_MODEL`: 默认 `gemini-3.1-flash-image-preview`
- `M2C_ASPECT_RATIO`: 默认 `1:1`
- `M2C_OUTPUT_DIR`: 默认 `./output`
- `M2C_TEMPLATE`: 默认 `chiikawa`
- `M2C_MAX_WORKERS`: 默认 `2`
- `M2C_REQUEST_TIMEOUT`: 默认 `600`
- `M2C_LOG_LEVEL`: 默认 `INFO`

## 输出与排错

默认输出目录是 `./output/`。

成功生成时：

- 每个 Mermaid block 生成一个 PNG
- PNG 内嵌元数据：
  - `mermaid_source`
  - `image_prompt`
  - `generated_at`
  - `block_index`
  - `diagram_type`

生成失败时：

- 会保存 `*_FAILED.txt`
- 里面包含原始 Mermaid 和最终提示词，便于手工复查

优先排查这些问题：

1. `M2C_PROJECT_ID` 是否设置正确
2. 如果 `.env` 设置了 `GOOGLE_APPLICATION_CREDENTIALS`，该路径是否存在且 JSON 有效
3. 如果 `.env` 未设置 `GOOGLE_APPLICATION_CREDENTIALS`，系统 ADC 是否可用
4. 如果使用服务账号冒充生成的系统 ADC，当前用户是否具备该服务账号的 `roles/iam.serviceAccountTokenCreator`
5. `aiplatform.googleapis.com` 是否已启用
6. 当前模型和区域配置是否仍可用

## 测试

基础单测：

```bash
python -m unittest \
  tests.test_m2c_config \
  tests.test_m2c_extractor \
  tests.test_m2c_storage
```

手工集成验证脚本：

```bash
python tests/smoke_test.py --input tests/fixtures/test_input.md
python tests/smoke_test.py --input tests/fixtures/test_input.md --with-image
```

`smoke_test.py` 是手工 smoke/integration 脚本，不是常规单测入口。

## 安全说明

- 不在仓库中存储 API key、token、cookie、session、服务账号 JSON
- `.env` 仅本地使用，不提交
- 生成图片、失败日志、测试输出都属于本地产物，不提交
- 如果需要共享配置，只共享 `.env.example`
- 明确禁止接入 Google AI Studio / Gemini Developer API
- 明确禁止添加 `GOOGLE_API_KEY`、`GEMINI_API_KEY` 或 `genai.Client(api_key=...)`
- 如果需要本地服务账号 ADC，优先使用服务账号冒充，不优先发放 JSON key

## Skill 使用

后续作为 skill 使用时，复用同一套前置条件和安全约束。具体协作方式见 [SKILL.md](./SKILL.md)。
