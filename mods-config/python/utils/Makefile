database="dump.db"
reports=

.PHONY: all

all: transform report

clean:
	rm -f $(database)

transform: clean
	cat trace.log* | python2.7 store.py

report:
	python2.7 report.py --database $(database) $(reports) > reports.log
