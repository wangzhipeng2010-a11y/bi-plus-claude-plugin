# 测试清单

MVP 测试不连接真实飞书，只验证用户入口、参数、路径、错误提示和后台调用封装。

## 自动化测试

```bash
python3 -m unittest discover -s tests
```

覆盖范围：

- 文件不存在时，直接返回 `文件不存在`。
- 文件存在时，调用 BI Plus 后台封装接口。
- 发送给后台的是规范化后的文件路径、文件名、插件名和 Skill 名。
- 后台返回 `path_not_allowed` 时，用户看到 `这个文件不在允许发送的目录里`。
- 后台返回 `permission_denied` 时，用户看到 `你还没有发送权限`。
- 后台不可达时，用户看到 `暂时无法连接 BI Plus 后台服务`。

## 人工验收

- 在 Claude Code 里用 `claude --plugin-dir .` 加载本地插件。
- 输入 `把 reports/recharge_2026_04.csv 发给我`，确认 Claude 会使用 `bi-plus:send-feishu-file`。
- 输入 `把刚才生成的报表发到我飞书`，若文件不明确，Claude 应先问用户具体文件。
- 确认回复只出现运营用户能理解的话，不出现后台地址、HTTP 状态码、堆栈、secret 或 token 名称。

## 不做的测试

- 不测真实飞书发送。
- 不测用户有没有权限。
- 不测允许目录规则。
- 不测数据库查询。
- 不测审批、开户或 MCP 权限事实源。

这些都属于 BIAIAgent 主项目或 BI Plus 后台服务。
