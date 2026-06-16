# BI Plus Claude Code Plugin 交接文档

> 截止日期：2026-06-07  
> 当前版本：0.1.5（publish rules documented）

---

## 一、这个项目是什么

这个 Plugin 的总览和边界以 `README.md` 为准。

交接时只需要记住一句话：用户在 Claude Code 里说"把报表发到飞书"，Plugin 负责接住这个入口，把文件路径交给 EC2 后台命令；真正的身份校验、路径校验、按类型转成飞书文档 / 表格 / 文件、飞书发送和审计都在后台完成。

---

## 二、系统结构

```
用户（Claude Code）
    │
    │ "把 reports/a.csv 发到我飞书"
    ▼
SKILL（skills/send-feishu-file/SKILL.md）
    │ 识别意图，提取文件路径
    ▼
Plugin 脚本（bin/send-feishu-file）
    │ subprocess 调用，路径原样传入
    ▼
后台命令（/opt/bi-plus/bin/send-feishu-file）  ← 由 BIAIAgent 部署维护
    │ BI Plus 后台服务
    ▼
飞书（发送结果）
    │ stdout 回传
    ▼
用户看到："文件已发送到你的飞书"
```

Plugin 和后台的边界：Plugin 只负责 Claude Code 里的用户入口和结果展示，后台负责一切实质性操作。Markdown 优先作为飞书文档交付，CSV / XLS / XLSX 优先作为飞书表格交付，其他文件保留普通文件交付；这些转换和回退策略都属于 BIAIAgent 后台。

---

## 三、关键文件

| 路径 | 用途 |
|---|---|
| `.claude-plugin/plugin.json` | Plugin 元信息，Claude Code 识别入口 |
| `skills/send-feishu-file/SKILL.md` | 告诉 Claude 何时触发、如何调用 |
| `bin/send-feishu-file` | 实际执行脚本，调用后台命令 |
| `tests/test_send_feishu_file.py` | 单元测试，用 fake shell script mock 后台 |
| `deploy.conf` | 服务器地址和路径备忘（不进 git） |

---

## 四、服务器信息

| 项目 | 值 |
|---|---|
| EC2 SSH | 见运维私有配置 |
| Plugin 路径（EC2） | 见运维私有配置 |
| 后台命令 | `/opt/bi-plus/bin/send-feishu-file` |
| 后台服务 | 由 BIAIAgent 部署维护 |

后台命令和服务由 BIAIAgent 项目（`~/projects/bi-ai-agent`）维护，Plugin 不负责。

---

## 五、日常运维

### 更新 Plugin 代码

本地改完测试通过后：

```bash
# 本地
git push origin main

# EC2
ssh <EC2_SSH>
cd ~/projects/bi-plus-claude-plugin && git pull
```

### 验证 Plugin 测试

```bash
# 本地
python3 -m unittest discover -s tests -v

# EC2
python3 -m unittest discover -s ~/projects/bi-plus-claude-plugin/tests -v
```

### 验证后台命令（EC2）

```bash
# 已绑定用户，预期返回"文件已发送到你的飞书"
sudo -n -u <bound-user> bash -lc 'printf "x,y\n1,2\n" > ~/reports/canary.csv'
sudo -n -u <bound-user> /opt/bi-plus/bin/send-feishu-file -- reports/canary.csv

# 未绑定用户，预期返回"你还没有发送权限"
sudo -n -u <unbound-user> /opt/bi-plus/bin/send-feishu-file -- reports/canary.csv
```

### 检查后台服务状态

```bash
ssh <EC2_SSH> '<check backend service status>'
```

---

## 六、用户如何使用 Plugin

用户的 Claude Code 需要加载 Plugin。最简单的方式：

```bash
claude --plugin-dir ~/projects/bi-plus-claude-plugin
```

或者企业统一配置 managed settings（见 `docs/managed-settings.example.json`）。

企业正式分发见 `README.md` 的 marketplace 安装说明。托管环境必须开启 `autoUpdate`，不要依赖用户手动执行 `plugin update`。source 可以是公开 Git、企业 Git 或本地目录，但必须对用户当前机器可访问。

用户会看到 `/bi-plus:send-feishu-file` 可用，也可以自然语言触发：

```text
把 reports/recharge_2026_04.csv 发到我飞书
把 docs/analysis.md 发送到飞书
```

---

## 七、用户提示对照表

Plugin 原样透传 stdout，不翻译。业务类返回码由后台命令决定，Plugin 原样透传；Plugin 只在超时、命令不可用、stdout 为空时自行返回 exit 1。未提供文件路径时，Plugin 本地返回"请求格式不正确"，exit 2。

| 后台返回 | 含义 |
|---|---|
| 文件已发送到你的飞书 | 成功 |
| 文件不存在 | 路径错误 |
| 文件不在允许目录 | 路径不在白名单 |
| 文件不允许发送 | 文件类型受限 |
| 不能发送目录或特殊文件 | 路径不是普通文件 |
| 文件过大，暂时无法发送 | 超过大小限制 |
| 你还没有发送权限 | 用户未开通 |
| 暂时无法连接 BI Plus 后台服务 | 服务异常、命令不存在、调用超时或 stdout 为空 |
| 请求格式不正确 | 未提供文件路径时由 Plugin 本地生成 |

Plugin 出现"暂时无法连接"通常有三种情况：后台命令不可用、后台调用超时、后台没有输出任何内容。三种情况 Plugin 都统一展示这条提示。

用户提示应统一说“发送到飞书，后台会按类型转成文档 / 表格 / 文件”。不要说“上传 MD 原文件”或“上传 CSV 原文件”，避免用户误解体验只是一份附件。

---

## 八、已明确不做的事

Plugin 边界以 `AGENTS.md` 红线和 `README.md` 为准，本交接文档不重复维护边界清单。

---

## 九、开户流程集成（BIAIAgent）

> 本节给 BIAIAgent 开户 Agent 看。新用户创建完成后，开户流程负责把 Plugin 安装到该用户的 Claude Code 里；**本项目只提供插件包、marketplace 清单和 Skill 内容，不实现开户逻辑**。

### 职责边界

| 由谁负责 | 内容 |
|---|---|
| 本项目（bi-plus-claude-plugin） | 插件包代码、`.claude-plugin/plugin.json`、Skill 内容 |
| BIAIAgent 开户流程 | 新用户安装 Plugin、维护企业 marketplace source |

### 安装步骤

新用户创建完成后，BIAIAgent 以**该新用户身份**依次执行：

```bash
# 注册本地 marketplace（仅首次注册或路径变更时需要）
claude plugin marketplace add /opt/bi-plus-plugins-marketplace

# 安装 Plugin
claude plugin install bi-plus@bi-plus-tools --scope user
```

`--scope user` 确保 Plugin 写入该用户自己的 Claude Code 配置，不影响其他用户。

### 验收标准

安装完成后，以**该新用户身份**验证：

```bash
# 必须看到 bi-plus@bi-plus-tools，Status 为 enabled
claude plugin list

# 必须看到 Skills: check-data-quality, send-feishu-file
claude plugin details bi-plus@bi-plus-tools
```

### 部署约束

- marketplace source 必须对用户当前机器可访问。公开 Git source 适合跨设备自动更新；本地目录 source 只适合托管 Linux 环境。
- 插件仓库有更新时，优先通过 managed settings 的 `autoUpdate: true` 让用户启动 Claude Code 后自动更新。

如需立即补偿更新，可在受影响用户下执行：
  ```bash
  claude plugin update --scope managed bi-plus@bi-plus-tools
  ```
  若版本跨度大，也可先 uninstall 再重新 install。

---

## 十、已知问题 / 注意事项

- `/opt/bi-plus/bin/send-feishu-file` 只存在于 EC2，本地开发不可用；本地测试靠 `BI_PLUS_BACKEND_CMD` env var 指定 fake script。
- 后台调用默认最多等待 120 秒；本地排查可用 `BI_PLUS_BACKEND_TIMEOUT` 临时调整。
- 相对路径由后台按当前 Linux 用户 home 解析，例如 `reports/a.csv` → `~/reports/a.csv`；Plugin 不展开路径，不要自己加 `os.path.resolve()`。
- 后台 stderr 不透传用户，避免泄露内部细节；Plugin 只看 stdout 和 exit code。
- Markdown / CSV / XLS / XLSX 的飞书文档化、表格化转换逻辑放在 BIAIAgent 后台服务；Plugin 不读取文件内容、不调用飞书 API、不读取飞书密钥。
