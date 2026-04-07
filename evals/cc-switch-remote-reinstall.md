# CC Switch Remote Reinstall Eval

> 目标：复现并验证 `leahana/m2c-pipeline@skill` 在 CC Switch 中的首次安装、升级、删除后重装和失败回退路径。

## 基线

- 客户端版本：`CC Switch 3.12.3`
- 观察日期：`2026-04-06`
- 远程入口：Repository=`leahana/m2c-pipeline`，Branch=`skill`

## 场景 1：首次安装

1. 打开 CC Switch → Skills → Add Repository
2. 输入 `leahana/m2c-pipeline` 和 `skill`
3. 完成安装并确认本地 Skill 目录包含 `SKILL.md`、`README.md`、`scripts/bootstrap_env.sh`

通过标准：

- 首次安装成功
- Skill 可见且可启用
- 根目录结构与发布契约一致

## 场景 2：升级安装

1. 在仓库发布一个新版本并确认 `skill` 分支已更新
2. 在 CC Switch 中触发更新或覆盖安装
3. 校验升级后目录仍完整，且旧版本不会在失败路径中被提前移除

通过标准：

- 升级安装成功
- 新版本内容生效
- 安装失败时旧版本仍可用

## 场景 3：删除后重装

1. 删除本地 `m2c-pipeline` Skill
2. 重新使用 `leahana/m2c-pipeline@skill` 执行安装
3. 记录数据库状态、日志和最终目录状态

通过标准：

- 删除后重装成功
- 若失败，错误明确指向 `stale local state`、`missing SKILL.md`、`multiple skill roots` 或 `subpath not supported`
- 不再出现“旧目录被删但新目录没装上”的半失败状态

## 场景 4：失败回退

1. 若场景 3 失败，改用 GitHub Release 压缩包安装
2. 或直接拉取 `skill` 分支：

```bash
git clone --branch skill --single-branch https://github.com/leahana/m2c-pipeline.git
cd m2c-pipeline
./scripts/bootstrap_env.sh
```

通过标准：

- GitHub Release 压缩包可作为稳定 fallback
- 直接拉取 `skill` 分支可作为稳定 fallback
- fallback 安装后的根目录与远程分支发布态同构

