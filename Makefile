install:
	mkdir database
	mkdir logs
	pip install -e . && python setup.py develop
