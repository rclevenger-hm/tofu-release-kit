.PHONY: test policies demo check

test:
	python -m unittest discover -s tests -v

policies:
	opa check --strict src/tofu_release_kit/policies
	opa test src/tofu_release_kit/policies tests/policies

demo:
	python scripts/demo.py --scenario healthy
	python scripts/demo.py --scenario blocked
	python scripts/demo.py --scenario unhealthy

check: test policies demo
