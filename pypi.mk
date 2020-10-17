#!make

VERSION := $(shell cat VERSION)
_VERSION := $(subst .,_,$(VERSION))

PYPI_DIST_SRCS := VERSION setup.py
PYPI_DIST_ARTIFACTS := dist/terranet-$(VERSION)-py3-none-any.whl \
	dist/terranet-$(VERSION).tar.gz

.PHONY: pypi-relase-terranet-dist
pypi-relase-terranet-dist: pypi-%: dist/terranet-$(VERSION).tar.gz
	python3 -m twine upload dist/$*-$(VERSION)* --config-file .pypirc

$(PYPI_DIST_ARTIFACTS) &: $(PYPI_DIST_SRCS)
	python3 setup.py bdist_wheel sdist

.PHONY: pypi-clean pypi-clean-dist pypi-clean-build
pypi-clean: pypi-clean-dist pypi-clean-build
pypi-clean-dist:
	rm -rf dist/
pypi-clean-build:
	rm -rf build/
