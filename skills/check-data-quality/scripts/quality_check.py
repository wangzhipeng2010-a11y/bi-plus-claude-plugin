#!/usr/bin/env python3
"""
充值数据可信度检测脚本

用法:
    python3 quality_check.py <csv文件路径>
    python3 quality_check.py --help
"""
import argparse
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta


def load_data(csv_path: str) -> tuple:
    """Load tab-separated CSV. Returns (daily_totals, city_data, all_rows, bad_rows).

    all_rows items: (date, region, city, count:int, is_non_int:bool)
    bad_rows items: (lineno, raw_line, reason)
    """
    daily_totals = defaultdict(int)
    city_data = defaultdict(list)
    all_rows = []
    bad_rows = []

    with open(csv_path, encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return daily_totals, city_data, all_rows, bad_rows

    for lineno, line in enumerate(lines[1:], start=2):
        row = line.rstrip("\n").split("\t")
        if len(row) < 4:
            bad_rows.append((lineno, line.strip(), "列数不足"))
            continue
        date, region, city, raw = row[0], row[1], row[2], row[3].strip()
        try:
            val = float(raw)
        except ValueError:
            bad_rows.append((lineno, line.strip(), f"无法解析数值: {raw!r}"))
            continue
        is_non_int = (val != int(val))
        count = int(val)
        daily_totals[date] += count
        city_data[(region, city)].append((date, count, is_non_int))
        all_rows.append((date, region, city, count, is_non_int))

    return daily_totals, city_data, all_rows, bad_rows


def _missing_dates(dates: set) -> list:
    if not dates:
        return []
    dates_sorted = sorted(dates)
    d0 = datetime.strptime(dates_sorted[0], "%Y%m%d")
    d1 = datetime.strptime(dates_sorted[-1], "%Y%m%d")
    full = set()
    d = d0
    while d <= d1:
        full.add(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return sorted(full - dates)


def check_basics(all_rows, bad_rows):
    print("=" * 60)
    print("1. 基础质量检查")
    print("=" * 60)

    if bad_rows:
        print(f"  ⚠ 无法解析的行: {len(bad_rows)} 条")
        for lineno, _, reason in bad_rows[:3]:
            print(f"    行{lineno}: {reason}")
    else:
        print("  无法解析的行: ✓ 无")

    if not all_rows:
        print("  无有效数据行")
        return

    dates = set(r[0] for r in all_rows)
    dates_sorted = sorted(dates)
    missing = _missing_dates(dates)

    zeros = sum(1 for r in all_rows if r[3] == 0)
    negatives = sum(1 for r in all_rows if r[3] < 0)
    non_int = sum(1 for r in all_rows if r[4])

    print(f"  总行数: {len(all_rows)}")
    print(f"  日期范围: {dates_sorted[0]} ~ {dates_sorted[-1]}")
    if missing:
        sample = missing[:5]
        suffix = "..." if len(missing) > 5 else ""
        print(f"  日期完整性: ✗ 缺{len(missing)}天: {sample}{suffix}")
    else:
        print("  日期完整性: ✓ 无缺失")

    if zeros or negatives:
        print(f"  ⚠ 零值:{zeros}, 负值:{negatives}")
    else:
        print("  零值/负值: ✓ 无")
    print(f"  非整数值: {'✓ 无' if non_int == 0 else f'✗ {non_int}条'}")

    cities = set((r[1], r[2]) for r in all_rows)
    expected = len(cities) * len(dates)
    diff = expected - len(all_rows)
    print(f"  行数校验: 实 {len(all_rows)} / 预期 {expected} (差{diff}, {diff / expected * 100:.1f}%)")


def check_statistics(all_rows, daily_totals):
    print(f"\n{'=' * 60}")
    print("2. 统计分布")
    print("=" * 60)

    vals = [r[3] for r in all_rows]
    dt_vals = list(daily_totals.values())

    if len(vals) < 2 or len(dt_vals) < 2:
        print("  数据量不足，跳过统计")
        return

    print(f"  单城市-日级: 均值={statistics.mean(vals):.0f} 中位数={statistics.median(vals):.0f} 标准差={statistics.stdev(vals):.0f}")
    print(f"  全国-日总量: 均值={statistics.mean(dt_vals):.0f} 中位数={statistics.median(dt_vals):.0f} 标准差={statistics.stdev(dt_vals):.0f}")

    sp = sorted(daily_totals.items(), key=lambda x: x[1])
    print(f"  最低日: {sp[0][0]} ({sp[0][1]:,})")
    print(f"  最高日: {sp[-1][0]} ({sp[-1][1]:,})")

    yearly = defaultdict(list)
    for d, v in daily_totals.items():
        yearly[d[:4]].append(v)
    print("  年度趋势:")
    for y in sorted(yearly):
        yv = yearly[y]
        print(f"    {y}: {len(yv)}天, 日均={statistics.mean(yv):.0f}, 合计={sum(yv):,}")


def check_outliers(city_data, daily_totals):
    print(f"\n{'=' * 60}")
    print("3. 异常值检测")
    print("=" * 60)

    city_outliers = []
    for (region, city), vals in city_data.items():
        counts = sorted(v for _, v, _ in vals)
        n = len(counts)
        if n < 10:
            continue
        q1, q3 = counts[n // 4], counts[3 * n // 4]
        iqr = q3 - q1
        if iqr == 0:
            continue
        upper = q3 + 3 * iqr
        for d, v, _ in vals:
            if v > upper:
                city_outliers.append((d, region, city, v))

    city_outliers.sort(key=lambda x: x[3], reverse=True)
    print(f"  IQR异常高点: {len(city_outliers)} 个")
    for d, r, c, v in city_outliers[:5]:
        print(f"    {d} {r}/{c}: {v:,}")

    dt_vals = sorted(daily_totals.values())
    n = len(dt_vals)
    if n < 4:
        return
    q1, q3 = dt_vals[n // 4], dt_vals[3 * n // 4]
    iqr = q3 - q1
    high_days = [(d, v) for d, v in daily_totals.items() if v > q3 + 2 * iqr]
    low_days = [(d, v) for d, v in daily_totals.items() if v < q1 - 2 * iqr]
    print(f"  日总量异常高: {len(high_days)}天 (>{q3 + 2 * iqr:.0f})")
    for d, v in sorted(high_days, key=lambda x: x[1], reverse=True)[:5]:
        print(f"    {d}: {v:,}")
    print(f"  日总量异常低: {len(low_days)}天")


def check_consistency(city_data, daily_totals, all_rows):
    print(f"\n{'=' * 60}")
    print("4. 业务一致性")
    print("=" * 60)

    dates_all = sorted(set(r[0] for r in all_rows))
    region_dates = defaultdict(set)
    for r in all_rows:
        region_dates[r[1]].add(r[0])

    print("  大区覆盖:")
    for region in sorted(region_dates):
        pct = len(region_dates[region]) / len(dates_all) * 100
        print(f"    {region}: {len(region_dates[region])}/{len(dates_all)}天 ({pct:.1f}%)")

    # Year-over-year H1 comparison — derived from actual data years
    years = sorted({d[:4] for d in dates_all})
    if len(years) >= 2:
        prev_y, cur_y = years[-2], years[-1]
        monthly_nat = defaultdict(int)
        for r in all_rows:
            monthly_nat[r[0][:6]] += r[3]
        h1_prev = sum(v for k, v in monthly_nat.items() if k.startswith(prev_y) and k[4:] <= "06")
        h1_cur = sum(v for k, v in monthly_nat.items() if k.startswith(cur_y) and k[4:] <= "06")

        if h1_prev > 0 and h1_cur > 0:
            nat_chg = (h1_cur - h1_prev) / h1_prev * 100
            city_monthly = defaultdict(lambda: defaultdict(int))
            for (region, city), vals in city_data.items():
                for d, v, _ in vals:
                    city_monthly[(region, city)][d[:6]] += v

            against = []
            for (region, city), mth in city_monthly.items():
                c_prev = sum(v for k, v in mth.items() if k.startswith(prev_y) and k[4:] <= "06")
                c_cur = sum(v for k, v in mth.items() if k.startswith(cur_y) and k[4:] <= "06")
                if c_prev > 500 and c_cur > 500:
                    c_chg = (c_cur - c_prev) / c_prev * 100
                    if (nat_chg < -5 and c_chg > 5) or (nat_chg > 5 and c_chg < -5):
                        against.append((region, city, c_chg))

            print(f"\n  趋势一致性 ({prev_y} vs {cur_y} H1, 全国 {nat_chg:+.1f}%):")
            if against:
                for region, city, chg in against:
                    print(f"    ⚠ {region}/{city}: {chg:+.1f}% (背离)")
            else:
                print("    ✓ 所有城市走势与全国一致")

    # Monthly rank stability
    region_cities = defaultdict(list)
    for region, city in city_data:
        region_cities[region].append(city)

    big_shifts = 0
    for region, cities in region_cities.items():
        if len(cities) < 5:
            continue
        monthly_totals = defaultdict(lambda: defaultdict(int))
        for city in cities:
            for d, v, _ in city_data[(region, city)]:
                monthly_totals[d[:6]][city] += v
        prev_ranks = None
        for month in sorted(monthly_totals):
            ranked = sorted(monthly_totals[month].items(), key=lambda x: x[1], reverse=True)
            cur_ranks = {c: i for i, (c, _) in enumerate(ranked)}
            if prev_ranks:
                for city in cur_ranks:
                    if city in prev_ranks and abs(cur_ranks[city] - prev_ranks[city]) >= 3:
                        big_shifts += 1
            prev_ranks = cur_ranks
    print(f"  排名稳定性: 跳变≥3位: {big_shifts}次 {'✓' if big_shifts <= 5 else '⚠'}")

    # Day-over-day spike detection
    spikes = 0
    for vals in city_data.values():
        sv = sorted(vals, key=lambda x: x[0])
        for i in range(1, len(sv)):
            pv, cv = sv[i - 1][1], sv[i][1]
            if pv > 0 and cv > 0 and (cv / pv > 3 or cv / pv < 0.33):
                spikes += 1
    print(f"  暴涨暴跌(日环比>3x): {spikes}次")


def print_summary(daily_totals, all_rows, bad_rows):
    print(f"\n{'=' * 60}")
    print("总结")
    print("=" * 60)

    issues = []
    if bad_rows:
        issues.append(f"{len(bad_rows)} 行无法解析")

    missing = _missing_dates(set(daily_totals.keys()))
    if missing:
        issues.append(f"缺失 {len(missing)} 天数据")

    zeros = sum(1 for r in all_rows if r[3] == 0)
    negatives = sum(1 for r in all_rows if r[3] < 0)
    if zeros:
        issues.append(f"存在 {zeros} 条零值")
    if negatives:
        issues.append(f"存在 {negatives} 条负值")

    yearly = defaultdict(list)
    for d, v in daily_totals.items():
        yearly[d[:4]].append(v)
    years = sorted(yearly)
    for i in range(1, len(years)):
        prev_avg = statistics.mean(yearly[years[i - 1]])
        cur_avg = statistics.mean(yearly[years[i]])
        chg = (cur_avg - prev_avg) / prev_avg * 100
        if chg < -10:
            issues.append(f"{years[i]} 日均较 {years[i-1]} 下降 {abs(chg):.1f}%")

    if issues:
        print("发现以下需关注的问题:")
        for idx, issue in enumerate(issues, 1):
            print(f"  {idx}. {issue}")
    else:
        print("✓ 数据质量良好，未发现明显问题")


def main():
    parser = argparse.ArgumentParser(
        description="对充值/订阅类 CSV 数据（Tab 分隔，列：日期 大区 城市 充值人数）做多维度质量检查。"
    )
    parser.add_argument("csv", help="CSV 文件路径")
    args = parser.parse_args()

    print(f"分析对象: {args.csv}\n")
    try:
        daily_totals, city_data, all_rows, bad_rows = load_data(args.csv)
    except FileNotFoundError:
        print(f"错误: 文件不存在: {args.csv}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    if not all_rows and not bad_rows:
        print("文件为空或只有表头，无可检查数据。")
        sys.exit(0)

    check_basics(all_rows, bad_rows)
    check_statistics(all_rows, daily_totals)
    check_outliers(city_data, daily_totals)
    check_consistency(city_data, daily_totals, all_rows)
    print_summary(daily_totals, all_rows, bad_rows)


if __name__ == "__main__":
    main()
