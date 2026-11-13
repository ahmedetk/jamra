# Written with the help of an SI coding assistant (Claude Code).
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

slides:
	$(PY) scripts/story_numbers.py
	$(PY) slides/build_slides.py
	$(PY) scripts/check_numbers.py

serve:
	$(PY) -m http.server 8000 --directory web/public

.PHONY: data live test slides serve
