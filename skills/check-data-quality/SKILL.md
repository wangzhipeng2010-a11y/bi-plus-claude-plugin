---
name: check-data-quality
description: "Run a multi-dimensional quality audit on a tab-separated recharge/subscription CSV file (columns: 日期, 大区, 城市, 充值人数). Use when the user wants to know whether their data file is trustworthy or has problems - e.g., 检查数据质量, 数据有没有异常, 这份 CSV 数据可信吗, 帮我看看数据有没有问题, 数据对不对, 数据靠谱吗, data quality check, validate my recharge data."
---

# 数据质量检测

对充值/订阅类 Tab 分隔 CSV 数据（列：`日期  大区  城市  充值人数`）做多维度质量审计。

## 如何运行

1. 确认用户指定了 CSV 文件路径。不清楚时，询问用户。
2. 运行检测脚本：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/check-data-quality/scripts/quality_check.py" "<csv文件路径>"
```

3. 把脚本的 stdout 原样给用户，并根据"总结"部分给出一句判断。

## 检测维度

| 维度 | 检查内容 |
|------|---------|
| 基础质量 | 日期完整性、零值/负值/非整数值、无法解析行、实际行数 vs 预期行数 |
| 统计分布 | 均值/中位数/标准差、最高/最低日、年度趋势 |
| 异常检测 | 各城市 IQR 异常点、日总量异常高低天 |
| 业务一致性 | 大区覆盖率、城市走势是否背离全国、月度排名稳定性、日环比暴涨暴跌 |

## 数据格式要求

- 分隔符：Tab（`\t`），**不是逗号**
- 列顺序：`日期`（YYYYMMDD）、`大区`、`城市`、`充值人数`（整数）
- 第一行为表头

## 判读指南

- **日期缺失或零值/负值** → 数据源问题，需排查上游
- **行数校验偏差 > 1%** → 某些城市有长期缺失天数
- **年度日均下滑 > 10%** → 业务层面需关注，区分市场原因和口径变化
- **某城市趋势与全国背离** → 该城市可能有特殊事件或数据异常
- **同天多城市暴涨** → 可能是促销/节假日（正常），也可能是数据异常
- **排名跳变频繁** → 数据不稳定，使用前需确认
