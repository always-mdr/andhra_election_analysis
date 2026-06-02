.PHONY: setup extract transform dashboard clean

setup:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	mkdir -p data/raw

extract:
	./venv/bin/python scripts/scrape_ap_elections.py
	./venv/bin/python scripts/scrape_deep_margins.py

transform:
	./venv/bin/python scripts/transform.py

dashboard:
	./venv/bin/streamlit run dashboard.py

run: extract transform dashboard

clean:
	rm -rf data/*
	rm -rf venv
	rm -rf dbt_election/target
