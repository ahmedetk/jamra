# Written with the help of an AI coding assistant (Claude Code by Anthropic).
PY ?= python
export PYTHONPATH := pipeline

data:
	$(PY) -m jamra.download
	$(PY) -m jamra.build
	$(PY) scripts/story_numbers.py

live:
	$(PY) -m jamra.live

test:
	$(PY) -m pytest -q

pages:
	$(PY) scripts/build_pages.py

serve:
	$(PY) -m http.server 8000 --directory web/public

.PHONY: data live test pages serve
