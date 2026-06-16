.PHONY: ai-review test smoke

# 本地 AI review：让另一个 claude 审查 git diff origin/main...HEAD
ai-review:
	.agent/local-claude-review.sh

# 跑单元测试
test:
	python3 -m unittest discover -s tests -v

# Skill smoke tests
smoke:
	bash skills/check-data-quality/tests/smoke_test.sh
