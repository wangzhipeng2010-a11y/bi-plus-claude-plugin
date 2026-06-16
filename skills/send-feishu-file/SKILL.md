---
name: send-feishu-file
description: Send a generated report or result file to the current user's Feishu through the BI Plus backend. Use when the user asks to send a Markdown document, CSV, Excel, PDF, or other generated result file to their Feishu.
---

# Send Feishu File

Use this skill when the user asks for a result file to be sent to their Feishu, for example:

- "把刚才生成的报表发到我飞书"
- "把 reports/recharge_2026_04.csv 发给我"
- "把 docs/analysis.md 发送到飞书"

User-facing delivery target:

- Markdown files should be sent to Feishu as documents by the backend.
- CSV / XLS / XLSX files should be sent to Feishu as spreadsheets by the backend.
- Other files should remain normal file delivery.
- This plugin must not convert file types locally. It only calls the server-side `send-feishu-file` client with the path.

## Product Boundary

BI Plus is only the Claude Code user entrypoint. Do not implement or explain backend approval, account creation, database lookup, Feishu Bot logic, MCP permission facts, or audit decisions here.

This skill must not:

- store Feishu App Secret
- store MCP token
- connect to databases
- call Feishu APIs directly
- use sudo
- decide whether the user has permission

The BI Plus backend service is responsible for user identity, allowed-path validation, type-aware Feishu delivery, and audit records.

## How To Run

1. Identify the file the user wants to send.
2. If the file is unclear or there are multiple likely files, ask the user which one.
3. Run the bundled command with the path exactly as the user specified — do not resolve relative paths to absolute:

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/send-feishu-file" --file "<path>"
```

Relative paths (e.g. `reports/a.csv`) are resolved by the backend relative to the Linux user's home directory. Do not expand them yourself.

4. Reply to the user with only the stdout from the command. Do not add interpretation or explanation.

## User-Facing Results

Show the backend's stdout verbatim. The backend controls all user-facing messages. Examples of what the backend may return:

- `文件已发送到你的飞书`
- `文件不存在`
- `文件不在允许目录`
- `你还没有发送权限`
- `暂时无法连接 BI Plus 后台服务`

Do not expose backend socket paths, HTTP status codes, systemd service names, stack traces, open_id, token names, or any internal service details to the user.
