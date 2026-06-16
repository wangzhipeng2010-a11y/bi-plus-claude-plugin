# BI Plus Claude Code Plugin

BI Plus 是企业 BI AI Agent 的用户侧增强工具包。这个项目只提供 Claude Code 里的官方入口、Skill 发现、参数整理、命令调用和结果展示。

第一版只包含一个 Skill：`bi-plus:send-feishu-file`，用于把本地生成的结果文件交给 BI Plus 后台服务，由后台完成身份校验、路径校验、飞书发送和审计。

用户体验目标：用户只说“发到飞书”。Markdown 文件由后台优先作为飞书文档交付，CSV / XLS / XLSX 文件由后台优先作为飞书表格交付，其他文件保留普通文件交付。Plugin 不做格式转换，只把文件路径交给后台。

## 目录结构

```text
.
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── send-feishu-file/
│       └── SKILL.md
├── bin/
│   └── send-feishu-file
├── tests/
│   └── test_send_feishu_file.py
└── docs/
    ├── managed-settings.example.json
    ├── marketplace-entry.example.json
    ├── testing-checklist.md
    └── future-skills.md
```

未来新增 Skill 时放在 `skills/<skill-name>/SKILL.md`，配套脚本放 `bin/` 或该 Skill 自己的 `scripts/` 目录。

## 工作原理

Plugin 不直接调用飞书 API，不连接数据库，不保存任何密钥。

用户在 Claude Code 里说：

```text
把 reports/recharge_2026_04.csv 发到我飞书
```

Claude 触发 Skill，Skill 调用 Plugin 的 bundled 脚本：

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/send-feishu-file" --file reports/recharge_2026_04.csv
```

脚本内部调用部署在服务器上的后台命令：

```bash
/opt/bi-plus/bin/send-feishu-file <path>
```

后台由 BIAIAgent 的文件发送服务负责处理用户身份、路径校验、按文件类型交付到飞书、飞书发送和审计。Plugin 只负责 Claude Code 里的用户入口、参数传递和结果展示。

## 本地试用

```bash
python3 -m unittest discover -s tests
claude --plugin-dir .
```

在 Claude Code 里可以自然表达：

```text
把 reports/recharge_2026_04.csv 发给我
把 docs/analysis.md 发送到飞书
```

也可以直接调用：

```text
/bi-plus:send-feishu-file reports/recharge_2026_04.csv
```

> 注：`/opt/bi-plus/bin/send-feishu-file` 只存在于部署服务器，本地测试使用 mock subprocess。

## 用户会看到什么

用户看到的是“发送到飞书”的结果，不需要关心底层是文档、表格还是普通文件：

- Markdown：后台优先转成飞书文档交付。
- CSV / XLS / XLSX：后台优先转成飞书表格交付。
- 其他文件：后台按普通文件交付。

后台返回什么，用户就看到什么。Plugin 原样展示，不翻译：

```text
文件已发送到你的飞书
文件不存在
文件不在允许目录
文件不允许发送
不能发送目录或特殊文件
文件过大，暂时无法发送
你还没有发送权限
暂时无法连接 BI Plus 后台服务
请求格式不正确
```

不会展示后台 socket 路径、systemd 服务名、HTTP 状态码、密钥名、堆栈或内部服务细节。

## 企业统一启用

企业分发建议走 Claude Code marketplace。管理员在 managed settings 里统一声明 marketplace，并启用插件。

macOS 文件位置：

```text
/Library/Application Support/ClaudeCode/managed-settings.json
```

示例见 `docs/managed-settings.example.json`。企业环境必须开启 `autoUpdate`，这样用户启动 Claude Code 时会自动刷新 marketplace 和已安装插件。

跨设备分发时，marketplace source 必须是用户机器可访问的地址：公开 Git 仓库、企业 Git 仓库（用户已配置凭据），或企业内网可达源。私有仓库如果用户没有凭据，自动更新会失败。

```json
{
  "extraKnownMarketplaces": {
    "bi-plus-tools": {
      "source": {
        "source": "git",
        "url": "https://github.com/wangzhipeng2010-a11y/bi-plus-claude-plugin.git"
      },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "bi-plus@bi-plus-tools": true
  }
}
```

EC2 托管用户也可以使用同一 Git source。若处于离线或 GitHub 不可达环境，可临时切回本地目录 marketplace，同样开启 `autoUpdate`：

```json
{
  "extraKnownMarketplaces": {
    "bi-plus-tools": {
      "source": {
        "source": "directory",
        "path": "/opt/bi-plus-plugins-marketplace"
      },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "bi-plus@bi-plus-tools": true
  }
}
```

如企业要限制用户只能安装批准来源，可同时配置 `strictKnownMarketplaces`。

## Marketplace 分发

推荐建一个 BI Plus 官方 marketplace 仓库，在 `.claude-plugin/marketplace.json` 里登记本插件。示例见 `docs/marketplace-entry.example.json`。

用户手动安装时：

```text
/plugin marketplace add your-org/bi-plus-claude-plugins
/plugin install bi-plus@bi-plus-official
```

本地开发时可以直接用：

```text
/plugin marketplace add ./path/to/marketplace
/plugin install bi-plus@bi-plus-official
```

## 升级与回滚

升级：

1. 修改插件代码。
2. 更新 `.claude-plugin/plugin.json` 里的 `version`。
3. 发布到 marketplace 指向的 git ref。
4. 企业 managed settings 开启 `autoUpdate` 后，用户下次启动 Claude Code 会自动更新；如需立即生效，可执行 `/reload-plugins` 或重启会话。

回滚：

1. 将 marketplace 的插件 source 指回上一个稳定 tag 或 commit。
2. 用户下次启动 Claude Code 自动更新到回滚版本；如需立即生效，可执行 `/reload-plugins` 或重启会话。
3. 如果使用 managed settings 分 stable/latest 两个渠道，只把受影响用户切回 stable marketplace。

## 边界

这个 Plugin 不保存飞书 App Secret，不保存 MCP token，不直接连数据库，不直接调用飞书 API，不使用 sudo，不判断用户有没有权限。

后台服务负责用户身份、文件路径校验、按类型转成飞书文档 / 表格 / 文件、飞书发送和审计。
