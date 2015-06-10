NAME    = $(shell cat bundle.json | sed -n 's/"name"//p' | tr -d '", :')
PROJECT = sanji-bundle-$(NAME)
VERSION = $(shell cat bundle.json | sed -n 's/"version"//p' | tr -d '", :')

SRC     = $(PROJECT)-$(VERSION)
ARCHIVE = $(abspath $(SRC).tar.gz)

SANJI_VER   ?= 1.0
INSTALL_DIR = $(DESTDIR)/usr/lib/sanji-$(SANJI_VER)/$(NAME)

FILES = \
	bundle.json \
	README.md \
	requirements.txt \
	ethernet.py \
	data/ethernet.json.factory \
	ip/__init__.py \
	ip/addr.py \
	ip/route.py \
	hooks/dhclient-script \
	tools/dhclient-updater.py
INSTALL_FILES=$(addprefix $(INSTALL_DIR)/,$(FILES))

EXCLUDES = \
	   --exclude "$(SRC)/.git" \
	   --exclude "$(SRC)/.gitignore" \
	   --exclude "$(SRC)/.travis.yml" \
	   --exclude "$(SRC)/build-deb"


all:

clean:
	rm -rf $(SRC)*.tar.gz
	rm -rf .coverage
	find ./ -name *.pyc | xargs rm -rf
	find ./ -name *.bak | xargs rm -rf

distclean: clean


pylint:
	flake8 -v --exclude=.git,__init__.py .
test:
	nosetests --with-coverage --cover-erase --cover-package=$(NAME) -v

archive: $(ARCHIVE)

$(ARCHIVE): distclean $(FILES)
	(cd ..; \
		mv $(CURDIR) ./$(SRC); \
		tar zcf $(SRC)/$(SRC).tar.gz $(SRC) $(EXCLUDES); \
		mv $(SRC) $(CURDIR); )

install: $(INSTALL_FILES)

$(INSTALL_DIR)/%: %
	mkdir -p $(dir $@)
	install $< $@

uninstall:
	-rm $(addprefix $(INSTALL_DIR)/,$(FILES))

.PHONY: pylint test build
