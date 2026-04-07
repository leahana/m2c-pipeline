# CC Switch Remote Skill Contract

> 状态：仓库侧稳定兼容说明
>
> 观察基线：`CC Switch 3.12.3`，`2026-04-06`

这份文档定义 `m2c-pipeline` 当前对外承诺的远程 Skill 分发契约，以及推荐给 CC Switch 安装器维护者的修复方向。

## 当前仓库契约

- 远程安装入口固定为 `owner/repo + branch=skill`
- 当前只支持单 Skill 发布分支，不支持 `subpath`
- `skill` 分支根目录就是 Skill 根目录，直接包含 `SKILL.md` 和 `README.md`
- GitHub Release 通用压缩包与 `skill` 分支 payload 保持同构
- 仓库不会尝试通过伪造 GitHub branch zip 顶层目录名来规避安装器缺陷

## 已知限制

- 基于 `2026-04-06` 对 `CC Switch 3.12.3` 的本地观察，首次远程安装通常可行
- 同一版本在“删除本地 Skill 后重新安装”路径上可能失败
- 因此当前推荐顺序是：
  - 优先使用 `leahana/m2c-pipeline + branch=skill`
  - 如果删除后重装失败，回退到 GitHub Release 压缩包
  - 或直接拉取 `skill` 分支并在根目录执行 `./scripts/bootstrap_env.sh`

## 安装器侧修复目标

CC Switch 安装器的根因修复不在这个仓库里，但兼容行为应收敛到以下三个职责接口：

- `discover_skill_root(extract_dir)`：从解压目录中发现唯一 Skill 根目录；不得把解压目录名硬编码成仓库名
- `classify_install_state(repo, branch, install_dir)`：区分首次安装、升级、修复重装、数据库残留、目录残留
- `stage_validate_swap(source, existing_install)`：先校验新版本，再替换旧目录；失败时必须回滚

对应的错误语义应至少包含：

- `missing SKILL.md`
- `multiple skill roots`
- `subpath not supported`
- `stale local state`
- `replace failed and rolled back`

## 仓库侧验证范围

仓库中的 `scripts/ci/check_cc_switch_remote_contract.py` 会持续验证：

- 发布态根目录直接包含 `SKILL.md` 和 `README.md`
- 发布态 Markdown 相对链接都能在发布态解析
- 发布态不泄漏 `tests/`、`.github/`、`policy/`、`scripts/ci/` 等开发内容
- synthetic archive 即使使用任意顶层目录名，也能通过 `discover_skill_root` 找到唯一 Skill 根目录

