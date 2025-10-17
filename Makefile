.PHONY: all setup clean

all: setup

setup: venv
	@echo "Installing dependencies..."
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Setup complete."

venv:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Virtual environment created."

download_transcripts: venv
	. venv/bin/activate && python download_transcripts.py

clean:
	@echo "Cleaning up..."
	rm -rf venv
	rm -rf Suits_Transcripts
	@echo "Cleanup complete."

make venv_init:
	source .venv/bin/activate
