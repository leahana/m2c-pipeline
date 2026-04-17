# m2c-pipeline

> 把 Markdown 里的 Mermaid 图，变成 Chiikawa 风格的可爱教育插画

## 安装方式

这份 README 会同时作为 `skill` 分支和 GitHub Release 通用压缩包的入口文档；两种分发方式目录结构一致，根目录就是运行入口。

### 1. 通过 CC Switch 安装

1. 打开 CC Switch → Skills → Add Repository
2. Repository 填 `leahana/m2c-pipeline`，Branch 填 `skill`
3. 安装后即可在 Claude Code 中使用 `m2c-pipeline` skill

> 已知限制：基于 `2026-04-06` 对 `CC Switch 3.12.3` 的本地观察，首次安装通常可行，但“删除本地 skill 后重新安装”仍可能失败。
> 如果遇到这条重装路径的问题，优先回退到“GitHub Release 压缩包安装”或直接拉取 `skill` 分支；兼容契约见 [references/cc-switch-remote-contract.md](references/cc-switch-remote-contract.md)。

### 2. 通过 GitHub Release 压缩包安装

1. 从 GitHub Release 下载 `m2c-pipeline-generic-v<version>.zip`
2. 解压后进入根目录
3. 在根目录执行 `./scripts/bootstrap_env.sh`

```bash
cd m2c-pipeline-generic-v<version>
./scripts/bootstrap_env.sh
```

### 3. 直接拉取 `skill` 分支

全新拉取（skill 内容在克隆目录的 `m2c-pipeline/` 子目录下）：

```bash
git clone --branch skill --single-branch https://github.com/leahana/m2c-pipeline.git
cd m2c-pipeline/m2c-pipeline
./scripts/bootstrap_env.sh
```

已有本地仓库时：

```bash
git fetch origin skill
git switch skill
cd m2c-pipeline
```

## 快速开始

无论你当前目录来自源码仓库、Release 解压目录，还是直接 checkout 的 `skill` 分支，都可以在根目录执行同一套命令；skill 根目录本身就是工作目录，`./venv`、`./output`、`./.env` 都相对这里解析。

```bash
# 1. 在当前根目录准备环境
./scripts/bootstrap_env.sh

# 2. 配置凭据
cp .env.example .env
# 编辑 .env，填入 M2C_PROJECT_ID（必填）和 GOOGLE_APPLICATION_CREDENTIALS（推荐）

# 3. 离线验证（不调用云端，推荐先跑一次）
./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback

# 4. 正式生成图片
./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --translation-mode vertex --output-dir ./output
```

> 前提条件：POSIX 环境、Python 3.11+，`pip install` 可访问依赖源。

## Python 环境选择规则

这个 skill 最终一律运行在 repo-local `./venv` 上；外部 Python 只负责给 `./scripts/bootstrap_env.sh` 提供一个可用的启动解释器。

- 优先复用当前根目录下已经存在且健康的 `./venv/bin/python`。
- 如果本地 `./venv` 不可用，再选择一个 Python 3.11+ 作为 bootstrap 来源，优先级是用户直接提供的解释器路径、`pyenv`、`uv`、命名 Conda 环境，最后才是系统 Python。
- 不把运行时绑定到 `conda base`、`uv run` 或其他共享环境；所有正式命令最终都回到 repo-local `./venv`。
- 任何外部环境探测或 `gcloud` 检查，都应在用户明确授权后再执行。

## 使用自己的文件

你的 Markdown 文件只需要包含至少一个 ` ```mermaid ` 代码块，即可作为输入。

```bash
# 先用离线模式确认提示词生成正常
./venv/bin/python -m m2c_pipeline path/to/your-file.md --dry-run --translation-mode fallback

# 确认无误后，正式生成图片（默认输出 WebP）
./venv/bin/python -m m2c_pipeline path/to/your-file.md --translation-mode vertex --output-dir ./output

# 如需兼容旧 PNG 流程
./venv/bin/python -m m2c_pipeline path/to/your-file.md --translation-mode vertex --output-dir ./output --output-format png
```

文件中有多个 mermaid 块时，pipeline 会并发处理，每个块生成一张独立的图片。

## 输出示例

**离线 dry-run 输出**（终端日志）：

```
Extracting mermaid blocks from fixtures/minimal-input.md ...
Found 1 mermaid block(s).
Translating block 1/1 (fallback mode) ...
Dry run complete. No images were generated.
```

**正式生成输出**（生成文件示例）：

```
Extracting mermaid blocks from your-file.md ...
Found 2 mermaid block(s).
Translating and painting blocks ...  2/2
Generated images:
  ./output/diagram_20260416_120000_00.png
  ./output/diagram_20260416_120001_01.png
```

默认会生成 PNG 文件，并把 Mermaid、最终 prompt、模板、时间戳和关键参数直接写进 PNG metadata。

如果你改用 `--output-format webp`，则 metadata 会写到同名 `.metadata.json` sidecar。

每次正式运行还会在输出目录下保留 `_runs/<run_id>/` 形式的排障材料，包括：

- `run.json`：本次运行的 CLI 入参、最终配置和 block manifest
- `logs/run.log`：完整日志落盘
- `blocks/<block>/`：按 block 保存的翻译、生成、存储诊断信息

如果某个块生成失败，会在输出目录写入 `diagram_YYYYMMDD_HHMMSS_NN_FAILED.txt` 作为恢复参考。

## 常用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--template` | 风格模板 | `chiikawa` |
| `--translation-mode` | `vertex`（云端）或 `fallback`（离线）| `vertex` |
| `--aspect-ratio` | 图片宽高比 | `1:1` |
| `--output-dir` | 输出目录 | `./output` |
| `--output-format` | 保存格式（`png` / `webp`） | `png` |
| `--image-size` | 生成分辨率（`1K` / `2K` / `4K`） | `2K` |
| `--candidate-count` | 每个 block 的候选图数量（`1-4`），仅 `> 1` 时启用候选图选择 | `1` |
| `--webp-quality` | WebP 质量（`0-100`） | `95` |
| `--dry-run` | 跳过图片生成 | 关 |
| `--max-workers` | 并发数 | `2` |
| `--log-level` | 日志级别（`DEBUG`/`INFO`/`WARNING`/`ERROR`）| `INFO` |
| `--version` | 打印版本号并退出 | — |

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `M2C_PROJECT_ID` | 是 | GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | 否 | ADC JSON 路径；未设置时可回退到系统 ADC |

> 本 skill 只走 Vertex AI API，不支持 Google AI Studio、`GOOGLE_API_KEY`、`GEMINI_API_KEY` 或 `api_key=` 方式。

推荐把 `M2C_PROJECT_ID` 和 `GOOGLE_APPLICATION_CREDENTIALS` 都写进 `.env`。如果暂时不写凭据路径，也可以先完成 `gcloud auth application-default login`，再回退到系统 ADC。

## 维护者预览

仓库里提供了 `./scripts/dev/preview_install.sh` 供维护者本地安装带时间戳的 preview skill 做自测；普通用户仍应优先使用 `skill` 分支或 release 压缩包。

## License

[MIT](./LICENSE)
