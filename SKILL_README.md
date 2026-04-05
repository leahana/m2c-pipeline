# m2c-pipeline

> 把 Markdown 里的 Mermaid 图，变成 Chiikawa 风格的可爱教育插画

## 安装方式

这份 README 会同时作为 `skill` 分支和 GitHub Release 通用压缩包的入口文档；两种分发方式目录结构一致，根目录就是运行入口。

### 1. 通过 CC Switch 安装

1. 打开 CC Switch → Skills → Add Repository
2. Repository 填 `leahana/m2c-pipeline`，Branch 填 `skill`
3. 安装后即可在 Claude Code 中使用 `m2c-pipeline` skill

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

> 前提条件：POSIX 环境、Python 3.11+，并且 `pip install` 可访问依赖源。
> agent 首跑顺序固定为：先检查 `./venv/bin/python`，再检查系统 `python3/python`，仍缺失时按 `references/install-python.md` 选择单一路径安装并确认权限；安装后回到 repo-local bootstrap。Windows 上则由 agent 安装 Python 后执行 `python -m venv venv` 和 `.\venv\Scripts\python.exe -m pip install -r requirements.txt`。

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
