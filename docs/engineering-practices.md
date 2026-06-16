# 工程准则：开发工作流 / TDD / 测试质量标准

> 本文档是「怎么写代码」的唯一权威正文。红线与路由在 `AGENTS.md`（五大准则），此处是展开正文，别处用链接指向。

---

## 一、为什么测试先行（TDD）

本项目的代码大量由 AI agent 代写。在这个场景下，TDD 的价值不是「覆盖率」，而是**给 agent 上护栏**。

关键风险：**让 AI 事后补测试，等于让它给自己的作业打分。** 常见的「作弊」行为——

- 写**同义反复**的测试（把实现逻辑原样抄一遍，永远通过，测不出任何缺陷）；
- 为了让测试变绿，直接**删掉或弱化**测试，而不是修代码；
- 用 mock / monkey-patch 骗过评分流程。

结果是覆盖率好看、却给人虚假的安全感。先写测试，把 AI 的行为提前锁死在需求边界内，是目前已知最有效的防线。

---

## 二、红绿重构循环（核心流程）

每个功能按 红 → 绿 → 重构 跑一遍，跑完一个再做下一个。

1. **红（Red）：先写测试，并运行确认它失败。** 必须亲眼看到测试失败、并贴出真实失败输出——不能口头声称「应该会失败」。跳过这一步，可能写了个一开始就通过的测试，等于啥也没验证。
2. **绿（Green）：写最少的代码让测试通过，不多写一行。** 只写测试要求的东西，不顺手加未要求的功能（呼应「极简优先」）。运行测试，确认由红变绿，贴出真实输出。
3. **重构（Refactor）：在保持绿的前提下清理代码。** 重构后重新跑测试确认仍全绿。代码已经简单清晰时，跳过重构。

---

## 三、防作弊红线（违反即视为未完成）

- **不得删除或弱化测试来凑绿。** 测试失败是反馈，要改的是代码，不是测试。确需改测试，必须说明为什么原测试是错的。
- **不得写同义反复测试。** 测试要验证「期望的行为」，不能照抄实现逻辑。
- **测公开行为，不测实现细节。** 好测试读起来像一份规格说明：描述系统从外部看「做了什么」，而非「怎么做的」。
- **必须贴真实测试输出。** 失败就说失败并贴输出；禁止「我以为通过了」。

---

## 四、本项目落地约束

- 测试框架用标准库 `unittest`；测试文件放 `tests/`，文件名以 `test_` 开头。
- 测试中**禁止连接外部服务**（真实飞书、EC2 后台命令、数据库），一律用 mock / fake script 替代。
- 正面范例：`tests/test_send_feishu_file.py` 用 fake shell script 通过 `BI_PLUS_BACKEND_CMD` 顶替真实后台命令，覆盖入口脚本对各类返回的处理——新测试照此搭。
- 运行：

```bash
python3 -m unittest discover -s tests -v
# 或
make test
```

---

## 五、本地 AI Review

提交后、合并前，让另一个 claude 审查本次改动：

```bash
make ai-review
```

约束：

- Review 范围只允许 `git diff origin/main...HEAD` 和 `git log origin/main..HEAD`；禁止 review 整仓、禁止 review `main` 既有代码、禁止提出与当前 diff 无关的大规模重构。
- 脚本只审查**已提交** diff；存在未提交改动时会警告（提醒先提交），但仍会就已提交部分出报告。
- 允许在 `main` 上运行（这是小插件，未强制 feature 分支）；但 `git diff origin/main...HEAD` 为空时会报错——说明你还没提交，或已与 `origin/main` 一致。
- 每次结果写入 `.agent/reviews/<branch>-<timestamp>.md`，并更新 `.agent/latest-review.md` 作为最近一次副本；这些运行产物不进 git。
- review prompt 在 `.agent/review-request.md`，输出固定四级：Critical / Major / Minor / Suggestion。

常用环境变量：

- `AI_REVIEW_CLAUDE_MODEL`：审查用模型，默认 `opus`；快速试跑可用 `haiku`。
- `AI_REVIEW_CLAUDE_EFFORT_LEVEL`：推理深度，默认 `high`；可选 `low` / `medium` / `high` / `xhigh` / `max`。
- `AI_REVIEW_CLAUDE_PERMISSION_MODE`：可选 permission mode；默认不设置，禁止设为 `plan`。
- `AI_REVIEW_CLAUDE_TIMEOUT`：单次执行超时秒数，默认 `1800`（本机无 `timeout` 命令时此项不生效，脚本会直接运行）。
- `AI_REVIEW_BASE_REMOTE` / `AI_REVIEW_BASE_BRANCH`：基线，默认 `origin` / `main`。
- `AI_REVIEW_CLAUDE_CMD`：claude 命令名，默认 `claude`。

本机依赖：`git`、Claude Code CLI（`claude`）。`timeout` 可选（macOS 默认没有，脚本会自动跳过超时）。
