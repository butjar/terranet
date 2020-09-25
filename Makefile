#!make
SHELL := /bin/bash
VERSION := $(shell cat VERSION)
_VERSION := $(subst .,_,$(VERSION))

# Python packaging variables
pypi_package_name := terranet
pypi_release_target := pypi-release-$(pypi_package_name)
pypi_clean_packaging_targets := pypi-clean-dist pypi-clean-build

# Vagrant variables
## ENV
BASEVM_VERSION := $(shell cat BASEVM_VERSION)
_BASEVM_VERSION := $(subst .,_,$(BASEVM_VERSION))
VAGRANTFILE_BUILD := Vagrantfile.build
include atlas.env
export $(shell sed 's/=.*//' atlas.env)
## Targets
vagrant_provider := virtualbox
vagrant_machine_targets := vagrant-terranet-build vagrant-terranet-base-build
vagrant_release_targets := vagrant-release-terranet vagrant-release-terranet-base
vagrant_box_targets := terranet-$(_VERSION).box terranet-base-$(_BASEVM_VERSION).box
vagrant_upload_targets := terranet-$(_VERSION)-upload.json terranet-base-$(_BASEVM_VERSION)-upload.json
vagrant_clean_machine_targets := vagrant-clean-terranet vagrant-clean-terranet-base
vagrant_clean_box_targets := vagrant-clean-terranet-boxes vagrant-clean-terranet-base-boxes
vagrant_clean_upload_targets := vagrant-clean-terranet-uploads vagrant-clean-terranet-base-uploads

# General targets
.PHONY: clean-all
clean-all: pypi-clean-all vagrant-clean-all

.PHONY: release-terranet release-terranet-base
release-terranet: release-%: pypi-release-% vagrant-release-%
release-terranet-base: release-%: vagrant-release-%

# Python package targets
.PHONY: $(pypi_release_target)
$(pypi_release_target): pypi-release-%: dist/%-$(VERSION)-py3-none-any.whl dist/%-$(VERSION).tar.gz
	python3 -m twine upload dist/$*-$(VERSION)* --config-file .pypirc

dist/$(pypi_package_name)-$(VERSION)-py3-none-any.whl: VERSION
	python3 setup.py bdist_wheel

dist/$(pypi_package_name)-$(VERSION).tar.gz: VERSION
	python3 setup.py sdist

.PHONY: pypi-clean-all $(pypi_clean_packaging_targets)
pypi-clean-all: $(pypi_clean_packaging_targets)
pypi-clean-dist:
	rm -rf dist/
pypi-clean-build:
	rm -rf build/

# Vagrant targets
## Vagrant machine provisioning
.PHONY: $(vagrant_machine_targets)
vagrant-terranet-build: machine ?= terranet-build
vagrant-terranet-base-build: machines ?= terranet-base-build
$(vagrant_machine_targets): vagrant-%: .vagrant/machines/%/$(vagrant_provider)/id
.vagrant/machines/%/$(vagrant_provider)/id: $(VAGRANTFILE_BUILD)
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant plugin install vagrant-disksize --local
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant up $(machine)
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant reload $(machine)

## Vagrant release targets
.PHONY: $(vagrant_release_targets)
vagrant-release-terranet: version := $(VERSION)
vagrant-release-terranet: _version := $(_VERSION)
vagrant-release-terranet: machine := terranet-build
vagrant-release-terranet: box := terranet
vagrant-release-terranet: vagrant-release-%: %-$(_VERSION)-upload.json
vagrant-release-terranet-base: version := $(BASEVM_VERSION)
vagrant-release-terranet-base: _version := $(_BASEVM_VERSION)
vagrant-release-terranet-base: machine := terranet-base-build
vagrant-release-terranet-base: box := terranet-base
vagrant-release-terranet-base: vagrant-release-%: %-$(_BASEVM_VERSION)-upload.json
$(vagrant_release_targets): release_url = $(shell cat $< | jq -r '.upload_path')
$(vagrant_release_targets):
	curl -v \
		 -XPUT \
		 -T $(box)-$(_version).box \
		 $(release_url)
	curl -v \
	     -XPUT \
		 -H "Authorization: Bearer $(ATLAS_ACCESS_TOKEN)" \
		 "https://app.vagrantup.com/api/v1/box/$(ATLAS_USER)/$(box)/version/$(version)/release"

# See: - https://www.vagrantup.com/vagrant-cloud/boxes/create
#      - https://www.vagrantup.com/vagrant-cloud/api
.INTERMEDIATE: $(vagrant_upload_targets)
terranet-$(_VERSION)-upload.json: version ?= $(VERSION)
terranet-$(_VERSION)-upload.json: box ?= terranet
terranet-base-$(_BASEVM_VERSION)-upload.json: version ?= $(BASEVM_VERSION)
terranet-base-$(_BASEVM_VERSION)-upload.json: box ?= terranet-base
$(vagrant_upload_targets): %-upload.json: %.box
	curl -v \
	     -H "Content-Type: application/json" \
		 -H "Authorization: Bearer $(ATLAS_ACCESS_TOKEN)" \
		 -d '{"version": {"version": "$(version)"}}' \
		 "https://app.vagrantup.com/api/v1/box/$(ATLAS_USER)/$(box)/versions"
	curl -v \
	     -H "Content-Type: application/json" \
		 -H "Authorization: Bearer $(ATLAS_ACCESS_TOKEN)" \
		 -d '{"provider": {"name": "$(vagrant_provider)"}}' \
		 "https://app.vagrantup.com/api/v1/box/$(ATLAS_USER)/$(box)/version/$(version)/providers"
	curl -v \
		 -o $@ \
		 -H "Authorization: Bearer $(ATLAS_ACCESS_TOKEN)" \
		 "https://vagrantcloud.com/api/v1/box/$(ATLAS_USER)/$(box)/version/$(version)/provider/$(vagrant_provider)/upload"

terranet-$(_VERSION).box: version ?= $(VERSION)
terranet-$(_VERSION).box: machine ?= terranet-build
terranet-$(_VERSION).box: box ?= terranet
terranet-$(_VERSION).box: %.box: .vagrant/machines/terranet/$(vagrant_provider)/id
terranet-base-$(_BASEVM_VERSION).box: version ?= $(BASEVM_VERSION)
terranet-base-$(_BASEVM_VERSION).box: machine ?= terranet-base-build
terranet-base-$(_BASEVM_VERSION).box: box ?= terranet-base
terranet-base-$(_BASEVM_VERSION).box: %.box: .vagrant/machines/terranet-base/$(vagrant_provider)/id
$(vagrant_box_targets):
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant package $(machine) --base $$(cat .vagrant/machines/$(machine)/$(vagrant_provider)/id) --output $@

## Vagrant clean targets
.PHONY: vagrant-clean-all $(vagrant_clean_machine_targets)
vagrant-clean-all: $(vagrant_clean_machine_targets)
vagrant-clean-terranet: machine := terranet-build
vagrant-clean-terranet-base: machine := terranet-base-build
$(vagrant_clean_machine_targets): vagrant-clean-%: vagrant-clean-%-boxes vagrant-clean-%-uploads
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant destroy $(machine) -f
	rm -rf .vagrant/machines/$(machine)

.PHONY: vagrant-clean-boxes $(vagrant_clean_box_targets)
vagrant-clean-boxes: $(vagrant_clean_box_targets)
$(vagrant_clean_box_targets): vagrant-clean-%-boxes:
	rm -rf $*-*.box

.PHONY: vagrant-clean-uploads $(vagrant_clean_upload_targets)
vagrant-clean-uploads: $(vagrant_clean_upload_targets)
$(vagrant_clean_upload_targets): vagrant-clean-%-uploads:
	rm -rf $*-*-upload.json
