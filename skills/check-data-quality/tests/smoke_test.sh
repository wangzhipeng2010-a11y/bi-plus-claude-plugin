#!/usr/bin/env bash
# Smoke test for quality_check.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/../scripts/quality_check.py"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

pass() { echo "  PASS"; }
fail() { echo "  FAIL: $1"; cat "$2" 2>/dev/null || true; exit 1; }

echo "=== Smoke test: quality_check.py ==="

# Shared sample CSV (2 years, 2 regions, 3 cities, 5 days each)
SAMPLE="$TMPDIR/sample.csv"
printf '日期\t大区\t城市\t充值人数\n' > "$SAMPLE"
for d in 20250101 20250102 20250103 20250104 20250105; do
  printf '%s\t南区\t拉各斯\t1000\n' "$d" >> "$SAMPLE"
  printf '%s\t南区\t阿布贾\t800\n' "$d" >> "$SAMPLE"
  printf '%s\t北区\t卡诺\t600\n' "$d" >> "$SAMPLE"
done
for d in 20260101 20260102 20260103 20260104 20260105; do
  printf '%s\t南区\t拉各斯\t950\n' "$d" >> "$SAMPLE"
  printf '%s\t南区\t阿布贾\t780\n' "$d" >> "$SAMPLE"
  printf '%s\t北区\t卡诺\t590\n' "$d" >> "$SAMPLE"
done

# [1/4] --help
echo "[1/4] --help"
python3 "$SCRIPT" --help > /dev/null
pass

# [2/4] Normal run produces expected sections
echo "[2/4] Normal run"
python3 "$SCRIPT" "$SAMPLE" > "$TMPDIR/out.txt"
grep -q "基础质量检查" "$TMPDIR/out.txt" || fail "missing section 1" "$TMPDIR/out.txt"
grep -q "统计分布"     "$TMPDIR/out.txt" || fail "missing section 2" "$TMPDIR/out.txt"
grep -q "异常值检测"   "$TMPDIR/out.txt" || fail "missing section 3" "$TMPDIR/out.txt"
grep -q "业务一致性"   "$TMPDIR/out.txt" || fail "missing section 4" "$TMPDIR/out.txt"
grep -q "总结"         "$TMPDIR/out.txt" || fail "missing summary"    "$TMPDIR/out.txt"
pass

# [3/4] File not found: exits non-zero with Chinese error message, no traceback
echo "[3/4] File not found"
python3 "$SCRIPT" "$TMPDIR/nonexistent.csv" 2>"$TMPDIR/err.txt" && fail "should have exited non-zero" "$TMPDIR/err.txt" || true
grep -q "错误" "$TMPDIR/err.txt" || fail "no Chinese error message" "$TMPDIR/err.txt"
pass

# [4/4] Rows with bad values are counted and reported, script does not crash
echo "[4/4] Bad data tolerance"
BAD="$TMPDIR/bad.csv"
printf '日期\t大区\t城市\t充值人数\n' > "$BAD"
printf '20260101\t南区\t拉各斯\t1000\n'  >> "$BAD"
printf '20260102\t南区\t拉各斯\tN/A\n'   >> "$BAD"
printf '20260103\t南区\t拉各斯\t\n'      >> "$BAD"
printf '20260104\t南区\t拉各斯\t900\n'   >> "$BAD"
python3 "$SCRIPT" "$BAD" > "$TMPDIR/bad_out.txt"
grep -q "无法解析" "$TMPDIR/bad_out.txt" || fail "bad rows not reported" "$TMPDIR/bad_out.txt"
pass

echo ""
echo "=== All smoke tests passed ==="
