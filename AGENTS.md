# BI Plus Claude Code Plugin

用户侧 Claude Code 工具包。给运营用户一个入口：在 Claude Code 里把生成的结果文件交给 BI Plus 后台，由后台完成身份校验、路径校验、飞书发送和审计。
架构：用户（Claude Code）→ SKILL → `bin/` 脚本 → EC2 后台命令 → 飞书。

> 本文件是 AI 协作的唯一契约。`CLAUDE.md` 通过 `@AGENTS.md` 引用它，**只改这里**，不要两处各写一份。

## 工作准则（五大准则）

1. **先想再写（Think Before Coding）**：说出假设，不清楚就停下来问；列出权衡取舍，不默默决定；困惑时先澄清，不靠猜。
2. **极简优先（Simplicity First）**：用最少代码解决问题，不加未要求的功能；不做投机性抽象、不为「未来可能」预留扩展；能少写就少写。
3. **外科手术式改动（Surgical Changes）**：只碰该碰的代码，不动无关文件；匹配现有风格，即使自觉更优；只清理自己引入的遗留物，不顺手重构旧代码。
4. **目标驱动（Goal-Driven Execution）**：先定义「怎样算成功」再动手；多步骤任务先给一份简短计划；循环迭代直到验证通过。
5. **测试先行（Test-First / TDD）**：每个功能先写测试并**运行确认它失败**，再写最少代码让它通过；不得事后补测试、不得删改测试凑绿。详见 `docs/engineering-practices.md`。

> 生效判据：diff 里不必要的改动明显减少、过度设计引起的返工消失、澄清问题出现在实施之前而非犯错之后。

## 这个 Plugin 的边界（红线，勿越界）

- 不直接调用飞书 API、不连接数据库、不保存任何密钥（飞书 App Secret / MCP token）。
- 不判断用户权限，不做开户 / 审批 / 收回授权。
- 不发给别人、不发飞书群。
- 不做审计采集 / 日报 / 告警。
- 以上都属于 BIAIAgent 后台或后续规划。Plugin 只负责 Claude Code 里的**入口、参数传递、结果展示**。
- 路径**不展开**（不要加 `os.path.resolve` / `realpath`）：相对路径由后台按 Linux 用户 home 解析。
- 只把后台 **stdout** 原样透传给用户；不透传 stderr、socket 路径、systemd 服务名、HTTP 状态码、堆栈、密钥名。

## 工作目录

- 本机：项目仓库根目录
- EC2：见运维私有配置。后台命令 `/opt/bi-plus/bin/send-feishu-file` 与后端服务由 **BIAIAgent** 项目部署维护，Plugin 不负责、不修改。

## 发布与自动更新

- 企业分发必须走 Claude Code marketplace，并在 managed settings 里开启 `autoUpdate: true`；不要依赖用户手动执行 `plugin update`。
- marketplace source 必须对用户当前机器可访问。跨设备分发优先使用公开 HTTPS Git source：`{"source":"git","url":"https://github.com/wangzhipeng2010-a11y/bi-plus-claude-plugin.git"}`。只有托管 Linux 内部环境才可使用本地 directory source。
- `.claude-plugin/plugin.json` 里声明了 `version`，所以每次发布任何会影响用户看到内容或 Skill 行为的改动，都必须 bump version；否则 Claude Code 会认为已是最新，自动更新会跳过。
- 更新生效需要用户新开会话、重启 Claude Code，或执行 `/reload-plugins`。
- 仓库已公开。提交前必须扫描当前 HEAD，确保没有密钥、token、真实用户账号、真实邮箱、私有主机/IP、个人本机路径、内部运维命令或后台实现细节。

## 文档索引（doc map，唯一权威；别处勿再维护副本）

| 文件 | 唯一负责的内容 |
|------|----------------|
| `README.md` | 总览 / 工作原理 / 本地试用 / 企业分发 / 升级回滚 / 边界 |
| `docs/handover.md` | 交接：系统结构 / 关键文件 / 服务器信息 / 日常运维 / 用户提示对照表 / **BIAIAgent 开户流程集成** |
| `docs/engineering-practices.md` | 开发工作流 / TDD 红绿循环 / 测试质量标准 / AI review 用法 |
| `docs/testing-checklist.md` | 测试清单：自动化测试覆盖 / 人工验收 / 明确不做的测试 |
| `docs/future-skills.md` | 后续 Skill 方向（仅方向，未实现） |
| `docs/managed-settings.example.json` | 企业 managed settings 分发示例 |
| `docs/marketplace-entry.example.json` | marketplace 登记示例 |
| `skills/send-feishu-file/SKILL.md` | Skill 触发条件与后台调用契约 |
| `.claude-plugin/plugin.json` | Plugin 元信息（name / version / skills 入口） |
| `deploy.conf` | 服务器地址与路径备忘（不进 git） |
| `.agent/` | 本地 AI review harness（见下） |

## AI Review（本地）

提交后、合并前，让另一个 Claude 审查本次改动：

```bash
make ai-review
```

- 用**本地** `claude` 审查 `git diff origin/main...HEAD`，输出 Critical / Major / Minor / Suggestion 四级报告。
- 只审查**已提交**的增量；有未提交改动会提醒先提交。
- 结果写入 `.agent/reviews/<branch>-<timestamp>.md`，并复制到 `.agent/latest-review.md`（运行产物，不进 git）。
- 详细约束、环境变量见 `docs/engineering-practices.md` §五。
