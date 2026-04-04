# GitHub Setup Checklist

这份清单汇总了当前仓库后续需要你在 GitHub 后台和本地完成的操作，按顺序勾选即可。

## 1. 本地分支与提交

- [ ] 确认当前工作目录仍在仓库根目录
- [ ] 确认本地分支已存在：`dev`
- [ ] 确认本地分支已存在：`dev`
- [ ] 将当前未提交改动整理到准备推送的工作分支
- [ ] 切换到 `dev`
- [ ] 提交当前改动
- [ ] 推送 `dev` 到远端

建议命令：

```bash
git switch dev
git add .
git commit -m "ci: harden generic skill release and governance gates"
git push -u origin dev
```

## 2. 让 CI 先在 GitHub 上跑出来

- [ ] 在 GitHub 上为 `dev` 创建一个 PR
- [ ] 等待 `ci` workflow 至少运行一轮
- [ ] 在 `Actions > ci` 中确认以下 job 名都已经出现：
  - [ ] `policy-pr-head`
  - [ ] `skill-spec`
  - [ ] `repo-policy`
  - [ ] `unit-tests`
  - [ ] `offline-smoke`
  - [ ] `package-dryrun`
  - [ ] `required-job-contract`

说明：

- GitHub 的 branch protection 页面通常只有在这些 checks 实际跑出来后，才会在 “required checks” 搜索框里出现它们的名字。

## 3. 配置 `main` 分支保护

路径：

- [ ] 打开 `Settings`
- [ ] 打开 `Branches`
- [ ] 编辑 `main` 对应的 `Branch protection rule`

在该页面中：

- [ ] 勾选 `Require a pull request before merging`
- [ ] 勾选 `Require status checks before merging`
- [ ] 在 `Status checks that are required` 中添加：
  - [ ] `policy-pr-head`
  - [ ] `skill-spec`
  - [ ] `repo-policy`
  - [ ] `unit-tests`
  - [ ] `offline-smoke`
  - [ ] `package-dryrun`
  - [ ] `required-job-contract`
- [ ] 勾选 `Require branches to be up to date before merging`
- [ ] 勾选 `Include administrators`
- [ ] 不配置任何 bypass
- [ ] 保存规则

## 4. 配置 `v*` tag ruleset

路径：

- [ ] 打开 `Settings`
- [ ] 打开 `Rules`
- [ ] 打开 `Rulesets`
- [ ] 新建一个 tag ruleset

规则内容：

- [ ] 名称可设为：`Protect release tags`
- [ ] `Enforcement status` 设为 `Active`
- [ ] 匹配模式设为：`v*`
- [ ] 不配置任何 bypass actor
- [ ] 勾选 `Restrict updates`
- [ ] 勾选 `Restrict deletions`
- [ ] 不勾选 `Restrict creations`
- [ ] 保存规则

说明：

- 当前治理基线是：允许首次创建 release tag，但禁止后续更新或删除已有 `v*` tag。
- 如果开启 `Restrict creations`，在无 bypass 的前提下会阻断正常 release tag 创建。

## 5. 配置治理审计 Secret

路径：

- [ ] 打开 `Settings`
- [ ] 打开 `Secrets and variables`
- [ ] 打开 `Actions`
- [ ] 新建 repository secret

内容：

- [ ] Secret 名称设为：`REPO_ADMIN_AUDIT_TOKEN`
- [ ] 填入一个可读取 branch protection 与 rulesets 的 token
- [ ] 保存

## 6. 验证治理审计

- [ ] 打开 `Actions`
- [ ] 手动运行 `governance-audit`
- [ ] 确认 `branch-protection-audit` 通过
- [ ] 确认 `tag-ruleset-audit` 通过

如果失败：

- [ ] 对照日志检查 `main` 分支保护配置是否完整
- [ ] 对照日志检查 `v*` tag ruleset 是否只包含 `update` 和 `deletion`
- [ ] 确认 `bypass` 仍为空

## 7. 验证 Release 流程

- [ ] 确认版本号与目标 tag 一致
- [ ] 在 `main` 上准备一个新的发布版本
- [ ] 推送一个新的 `vX.Y.Z` tag
- [ ] 打开 `Actions > release-generic`
- [ ] 确认以下 job 通过：
  - [ ] `version-guard`
  - [ ] `main-ancestry-guard`
  - [ ] `governance-precheck`
  - [ ] `build-and-release`

## 8. 本地回归命令

如需在本地再次确认，可使用当前虚拟环境执行：

```bash
./venv/bin/python -m unittest discover -s tests -p 'test_*.py'
./venv/bin/python scripts/ci/check_skill_spec.py
./venv/bin/python scripts/ci/check_repo_policy.py
./venv/bin/python scripts/ci/check_required_job_contract.py
./venv/bin/python scripts/ci/package_generic.py --output-dir dist
./venv/bin/python -m m2c_pipeline tests/fixtures/test_input.md --dry-run --translation-mode fallback --log-level ERROR
```
