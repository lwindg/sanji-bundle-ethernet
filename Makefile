
FILES = README.md bundle.json ethernet.py ip.py requirements.txt
DIRS = data

all: pylint test

pylint:
	flake8 -v --exclude=.git,__init__.py .
test:
	nosetests --with-coverage --cover-erase --cover-package=ethernet -v

deb:
	mkdir -p deb
	cp -a debian deb/
	cp -a debian.mk deb/Makefile
	cp -a README.md $(FILES) $(DIRS) deb/
	(cd deb; \
		dpkg-buildpackage -us -uc -rfakeroot;)

clean:
	rm -rf deb

.PHONY: pylint test
