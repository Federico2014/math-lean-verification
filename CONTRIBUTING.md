# 添加候选与贡献流程

本仓库尚无候选项目。提交候选只表示申请核验，不表示已获奖、已证明或具备首解资格。

## 1. 登记材料

新建“提交候选成果”Issue，填写原始数学问题、论文、首次公开时间、拟证明／反驳／部分推进的范围、Lean 仓库 URL、完整 40 位 commit、全部目标定理、版本和贡献归属。只有公开且获准分享的材料进入本仓库。

没有 Lean 工程时可先登记 Issue，并明确“待补形式化材料”。不为此创建看似已可核验的虚假 submission。

Issue 不会自动获取或运行任何源码，不会自动转换成官方命题或核验结论。

## 2. 新题或已有题

若精确题目与官方陈述版本已存在，引用对应 `problem_id` 和 `statement_version`。同一题可有多个不同证明工程，各自使用全局唯一 `submission_id`。

新题先创建 `problems/<problem-id>/v1/`：

```text
problem.json
statement.md
correspondence.md
definitions.md
Challenge.lean
```

使用 [题目模板](templates/problem/)，根据原题撰写材料。模板含占位字段，不能原样通过校验。正式陈述需要 [独立审查](docs/statement-review.md)，不得复制候选代码后声称已经盲写。

`problem.json` 记录原题出处、范围、结论方向和全部 `required_theorems`。`trusted_files` 必须包含题目目录里除 `problem.json` 外的所有文件及其 SHA-256。每次修改绑定文件都须更新哈希；已有批准记录还需重审。

生成文件哈希可用 `shasum -a 256 <file>`（macOS）或 `sha256sum <file>`（Linux）。当前工具链未接入时 `toolchain_id` 为 `null`，审查保持 `pending`。

## 3. 新增证明登记

复制 [登记模板](templates/submission.json) 到：

```text
submissions/<problem-id>/<submission-id>.json
```

填入固定公开仓库地址、commit、目标模块和定理。每个官方目标必须恰好对应一条目标记录，不能只登记已经容易通过的部分。

登记不接受 `main`、`latest`、任意 shell 命令或候选自行设置的公理白名单。需要适配时提交独立、经审查的 `adapters/` 变更；当前后端未实现，登记适配器 ID 不会执行适配器。

保留作者、形式化方和证明路线，特别注明在先结果、额外假设和部分进展。公开署名不包含收款、证件和内部背景审查信息。

## 4. 本地校验及 PR

按 README 安装开发依赖，然后执行：

```bash
python -m verifier validate
python -m unittest discover -s tests -v
```

新建分支提交 PR，关联登记 Issue，解释变更、来源与核验范围。元数据通过只说明登记结构和引用有效，不说明数学证明成立。

## 5. 维护者预检与后续完整核验

维护者完成登记审查后合并 PR，在 Actions 中选择 **Verification preflight**，分支固定为 `main`，输入 `submission_id`。

当前工作流只检查登记并产生绑定输入哈希的 `plan.json`。后端未接入时返回退出码 3，明确显示阻塞原因；不会下载候选、运行 Lean 或标记成功。该 artifact 是临时预检材料，不是正式证据档案。

完整核验上线后，另行运行断网洁净构建、可信命题比对、公理审计、双检查器重放和长期归档。正式通过仍要求有效命题审查，详见 [上线清单](docs/implementation-status.md)。

## 6. 修改与重新提交

改变候选 commit 或目标会产生新预检输入哈希。后续正式记录必须追加，禁止覆写旧记录。官方题目或其定义勘误需作废原版本、发布新版本并重审；不能用修改题目来迎合当前证明。
