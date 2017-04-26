.PHONY: all

all:
	./check.sh
	pip install pep8 pep257
	cd ../utils/ && pep8 *.py
	cd ../utils/ && pep257 *.py
	pep8 *.py
	pep257 *.py
