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

全新拉取：

```bash
git clone --branch skill --single-branch https://github.com/leahana/m2c-pipeline.git
cd m2c-pipeline
./scripts/bootstrap_env.sh
```

已有本地仓库时：

```bash
git fetch origin skill
git switch skill
```

## 快速开始

无论你当前目录来自源码仓库、Release 解压目录，还是直接 checkout 的 `skill` 分支，都可以在根目录执行同一套命令；已有 `./venv` 时可以直接复用。

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

- `pyenv`：优先复用，适合作为用户态、干净的 bootstrap 来源。
- `uv`：可以提供 Python 或临时 `.venv`，但本项目不切到 `uv run`；仍然会回到 repo-local `./venv`。
- Conda：命名环境可以临时借来 bootstrap；不建议把本项目绑定到共享 `conda base`。
- Homebrew / Python.org / 系统 Python：只要版本兼容，也可以作为 bootstrap 来源。
- 完全没有兼容 Python 时：优先看是否已有 `pyenv` 或 `uv`，再退到 Homebrew / `apt` / `winget` 这类平台安装路径。

## 使用自己的文件

你的 Markdown 文件只需要包含至少一个 ` ```mermaid ` 代码块，即可作为输入。

```bash
# 先用离线模式确认提示词生成正常
./venv/bin/python -m m2c_pipeline path/to/your-file.md --dry-run --translation-mode fallback

# 确认无误后，正式生成图片
./venv/bin/python -m m2c_pipeline path/to/your-file.md --translation-mode vertex --output-dir ./output
```

文件中有多个 mermaid 块时，pipeline 会并发处理，每个块生成一张独立的 PNG。

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
  ./output/diagram_20260406_120000_00.png
  ./output/diagram_20260406_120001_01.png
```

生成的 PNG 文件内嵌有元数据（原始 Mermaid 代码、最终提示词、生成时间、块索引、图表类型）。

如果某个块生成失败，会在输出目录写入 `diagram_YYYYMMDD_HHMMSS_NN_FAILED.txt` 作为恢复参考。

## 常用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--template` | 风格模板 | `chiikawa` |
| `--translation-mode` | `vertex`（云端）或 `fallback`（离线）| `vertex` |
| `--aspect-ratio` | 图片宽高比 | `1:1` |
| `--output-dir` | 输出目录 | `./output` |
| `--dry-run` | 跳过图片生成 | 关 |
| `--max-workers` | 并发数 | `2` |
| `--log-level` | 日志级别（`DEBUG`/`INFO`/`WARNING`/`ERROR`）| `INFO` |
| `--version` | 打印版本号并退出 | — |

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `M2C_PROJECT_ID` | 是 | GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | 否 | ADC JSON 路径；未设置时回退到系统 ADC |

> 本 skill 只走 Vertex AI API，不支持 Google AI Studio 或 API key。

## License

[MIT](./LICENSE)
