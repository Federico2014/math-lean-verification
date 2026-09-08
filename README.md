# math-lean-verification

[![Registry CI](https://github.com/Federico2014/math-lean-verification/actions/workflows/ci.yml/badge.svg)](https://github.com/Federico2014/math-lean-verification/actions/workflows/ci.yml)

面向数学成果的 Lean 形式化证明核验基础设施，首个应用场景是孙宇晨奖。目标是同时核对：**证明在认可的逻辑下成立，且确实对应指定的数学难题。**

## 当前状态

仓库处于基础设施初始化阶段，**没有候选项目，也没有任何已验证成果**。

已提供候选提交表单、登记 schema、原题与命题对应性模板、哈希及目标完整性校验、CI 测试和维护者预检入口。CI 徽章只代表仓库代码与登记校验结果。

**Comparator／双检查器执行后端、认可工具链和长期归档尚未接入。** 当前 `plan` 只输出预检阻塞原因并返回非零退出码，不下载、不执行候选代码，不会产生“证明通过”结果。后端上线需要完成 [实施清单](docs/implementation-status.md)。

## 添加候选

1. 通过 [候选提交表单](https://github.com/Federico2014/math-lean-verification/issues/new?template=candidate.yml) 提交原题、论文、Lean 仓库、完整 commit 和目标定理。
2. 新题先完成官方命题登记及独立审查；已有同版本题目可复用。
3. 按 [贡献流程](CONTRIBUTING.md) 新增登记 PR；不在 Issue 中提交凭据、KYC 或未授权公开材料。
4. 维护者合并登记并运行预检；完整证明核验在后端上线后另行运行。

## 核验原则

```text
原始数学问题
    ↓ 独立数学审查：量词、定义、范围、前提和结论
官方 Lean 命题（固定版本）
    ↓ 机器比对 + 公理审计 + 独立检查器重放
候选证明（固定 commit）
    ↓ 完整证据归档与审查记录关联
形式化采信状态（与奖金、首解和受奖身份分开）
```

自然语言到 Lean 的忠实性需要独立审查；机器检查不能单独证明自然语言理解正确。候选人不能修改题目或白名单来让自己的证明通过。

## 本地开发

使用 Python 3.12。维护者开发环境可通过下列固定版本安装依赖；`requirements-dev.txt` 不用于正式 CI。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m verifier validate
python -m verifier list
```

CI 在 Linux x86_64 / Python 3.12 上使用 `requirements-ci.lock` 和 `--require-hashes` 安装依赖。两份清单必须保持版本一致。

登记之后可运行 `python -m verifier plan <submission-id> --output plan.json`。退出码：`0` 为登记校验成功；`2` 为输入无效；`3` 为预检完成但正式核验仍被阻止。任何一项都不等于证明通过。

## 文档

- [设计文档](docs/design.md)
- [添加候选流程](CONTRIBUTING.md)
- [命题对应性审查](docs/statement-review.md)
- [维护者操作手册](docs/maintainer-runbook.md)
- [当前实现与后续验收](docs/implementation-status.md)
- [采信政策](policy/verification.md)
- [安全边界](SECURITY.md)

本仓库代码采用 MIT License。外部数学论文和证明源码的许可由原权利方决定，接入或归档不会自动改变其许可证。
