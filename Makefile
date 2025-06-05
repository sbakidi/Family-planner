.PHONY: test

test:
	TEST_MODE_ENABLED=1 python src/database.py >/dev/null 2>&1 || true
	TEST_MODE_ENABLED=1 pytest
