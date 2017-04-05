NAME    = $(shell cat bundle.json | sed -n 's/"name"//p' | tr -d '", :')

PROJECT = sanji-bundle-$(NAME)
VERSION = $(shell cat bundle.json | sed -n 's/"version"//p' | tr -d '", :')

DISTDIR = $(PROJECT)-$(VERSION)
ARCHIVE = $(CURDIR)/$(DISTDIR).tar.gz

SANJI_VER   ?= 1.0
PROJECT_DIR = /usr/lib/sanji-$(SANJI_VER)/$(NAME)
INSTALL_DIR = $(DESTDIR)/$(PROJECT_DIR)
STAGING_DIR = $(CURDIR)/staging
PROJECT_STAGING_DIR = $(STAGING_DIR)/$(DISTDIR)

TARGET_FILES = \
	LICENSE \
	bundle.json \
	requirements.txt \
	ethernet.py \
	data/ethernet.json.factory \
	ip/__init__.py \
	ip/addr.py \
	ip/route.py \
	hooks/dhclient-script \
	tools/dhclient-updater.py \
	tools/link-updater.py
DIST_FILES= \
	$(TARGET_FILES) \
	README.md \
	Makefile \
	hooks/ifplugd/sanji-bundle-ethernet.in \
	tests/requirements.txt \
	tests/test_ethernet.py \
	tests/data/ethernet.json.factory \
	tests/test_e2e/bundle.json \
	tests/test_e2e/view_ethernet.py
INSTALL_FILES=$(addprefix $(INSTALL_DIR)/,$(TARGET_FILES))
STAGING_FILES=$(addprefix $(PROJECT_STAGING_DIR)/,$(DIST_FILES))

IN_FILES=$(shell find ./ -name *.in)
OUT_FILES=$(IN_FILES:.in=)

replace = sed -e 's|@pkgdir@|$(PROJECT_DIR)|g'


all: $(OUT_FILES)

$(OUT_FILES):
	@$(replace) $@.in >$@
	@chmod a+x $@
	@rm $@.in

clean:
	rm -rf $(DISTDIR)*.tar.gz $(STAGING_DIR) $(OUT_FILES)
	@rm -rf .coverage
	@find ./ -name *.pyc | xargs rm -rf

distclean: clean

pylint:
	flake8 -v --exclude=.git,__init__.py .
test:
	nosetests --with-coverage --cover-erase --cover-package=$(NAME) -v

dist: $(ARCHIVE)

$(ARCHIVE): distclean $(STAGING_FILES)
	@mkdir -p $(STAGING_DIR)
	cd $(STAGING_DIR) && \
		tar zcf $@ $(DISTDIR)

$(PROJECT_STAGING_DIR)/%: %
	@mkdir -p $(dir $@)
	@cp -a $< $@

install: $(INSTALL_FILES:.in=)

$(INSTALL_DIR)/%: %
	@mkdir -p $(dir $@)
	@cp -a $< $@

uninstall:
	-rm $(addprefix $(INSTALL_DIR)/,$(TARGET_FILES))

.PHONY: all clean install distclean dist pylint test
