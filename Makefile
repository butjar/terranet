#!make
SHELL := /bin/bash
VERSION := $(shell cat VERSION)
_VERSION := $(subst .,_,$(VERSION))

# Vagrant variables
## ENV
BASEVM_VERSION := $(shell cat BASEVM_VERSION)
_BASEVM_VERSION := $(subst .,_,$(BASEVM_VERSION))
VAGRANTFILE_BUILD := Vagrantfile.build
include atlas.env
export $(shell sed 's/=.*//' atlas.env)
## Targets
vagrant_provider := virtualbox
vagrant_machine_targets := vagrant-terranet vagrant-terranet-base
vagrant_release_targets := vagrant-release-terranet vagrant-release-terranet-base
vagrant_box_targets := terranet-$(_VERSION).box terranet-base-$(_BASEVM_VERSION).box
vagrant_upload_targets := terranet-$(_VERSION)-upload.json terranet-base-$(_BASEVM_VERSION)-upload.json
vagrant_clean_machine_targets := vagrant-clean-terranet vagrant-clean-terranet-base
vagrant_clean_box_targets := vagrant-clean-terranet-boxes vagrant-clean-terranet-base-boxes
vagrant_clean_upload_targets := vagrant-clean-terranet-uploads vagrant-clean-terranet-base-uploads



# Vagrant targets
## Vagrant machine provisioning
.PHONY: $(vagrant_machine_targets)
$(vagrant_machine_targets): vagrant-%: .vagrant/machines/%/$(vagrant_provider)/id

.vagrant/machines/%/$(vagrant_provider)/id: $(VAGRANTFILE_BUILD)
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant plugin install vagrant-disksize --local
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant up $*
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant reload $*

## Vagrant release targets
.PHONY: $(vagrant_release_targets)
vagrant-release-terranet: version := $(VERSION)
vagrant-release-terranet: _version := $(_VERSION)
vagrant-release-terranet: machine := terranet
vagrant-release-terranet: vagrant-release-%: %-$(_VERSION)-upload.json
vagrant-release-terranet-base: version := $(BASEVM_VERSION)
vagrant-release-terranet-base: _version := $(_BASEVM_VERSION)
vagrant-release-terranet-base: machine := terranet-base
vagrant-release-terranet-base: vagrant-release-%: %-$(_BASEVM_VERSION)-upload.json
$(vagrant_release_targets): release_url = $(shell cat $< | jq -r '.upload_path')
$(vagrant_release_targets):
	curl -v \
		 -XPUT \
		 -T $*-$(_version).box \
		 $(release_url)
	curl -v \
	     -XPUT \
		 -H "Authorization: Bearer $(ATLAS_ACCESS_TOKEN)" \
		 "https://app.vagrantup.com/api/v1/box/$(ATLAS_USER)/$*/version/$(version)/release"

# See: - https://www.vagrantup.com/vagrant-cloud/boxes/create
#      - https://www.vagrantup.com/vagrant-cloud/api
.INTERMEDIATE: $(vagrant_upload_targets)
terranet-$(_VERSION)-upload.json: version ?= $(VERSION)
terranet-$(_VERSION)-upload.json: machine ?= terranet
terranet-base-$(_BASEVM_VERSION)-upload.json: version ?= $(BASEVM_VERSION)
terranet-base-$(_BASEVM_VERSION)-upload.json: machine ?= terranet-base
$(vagrant_upload_targets): %-upload.json: %.box
	curl -v \
	     -H "Content-Type: application/json" \
		 -H "Authorization: Bearer $(ATLAS_ACCESS_TOKEN)" \
		 -d '{"version": {"version": "$(version)"}}' \
		 "https://app.vagrantup.com/api/v1/box/$(ATLAS_USER)/$(machine)/versions"
	curl -v \
	     -H "Content-Type: application/json" \
		 -H "Authorization: Bearer $(ATLAS_ACCESS_TOKEN)" \
		 -d '{"provider": {"name": "$(vagrant_provider)"}}' \
		 "https://app.vagrantup.com/api/v1/box/$(ATLAS_USER)/$(machine)/version/$(version)/providers"
	curl -v \
		 -o $@ \
		 -H "Authorization: Bearer $(ATLAS_ACCESS_TOKEN)" \
		 "https://vagrantcloud.com/api/v1/box/$(ATLAS_USER)/$(machine)/version/$(version)/provider/$(vagrant_provider)/upload"

terranet-$(_VERSION).box: version ?= $(VERSION)
terranet-$(_VERSION).box: machine ?= terranet
terranet-$(_VERSION).box: %.box: .vagrant/machines/terranet/$(vagrant_provider)/id
terranet-base-$(_BASEVM_VERSION).box: version ?= $(BASEVM_VERSION)
terranet-base-$(_BASEVM_VERSION).box: machine ?= terranet-base
terranet-base-$(_BASEVM_VERSION).box: %.box: .vagrant/machines/terranet-base/$(vagrant_provider)/id
$(vagrant_box_targets):
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant package $(machine) --base $$(cat .vagrant/machines/$(machine)/$(vagrant_provider)/id) --output $@

## Vagrant clean targets
.PHONY: vagrant-clean-all $(vagrant_clean_machine_targets)
vagrant-clean-all: $(vagrant_clean_machine_targets)
$(vagrant_clean_machine_targets): vagrant-clean-%: vagrant-clean-%-boxes vagrant-clean-%-uploads
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant destroy $* -f
	rm -rf .vagrant/machines/$*

.PHONY: vagrant-clean-boxes $(vagrant_clean_box_targets)
vagrant-clean-boxes: $(vagrant_clean_box_targets)
$(vagrant_clean_box_targets): vagrant-clean-%-boxes:
	rm -rf $*-*.box

.PHONY: vagrant-clean-uploads $(vagrant_clean_upload_targets)
vagrant-clean-uploads: $(vagrant_clean_upload_targets)
$(vagrant_clean_upload_targets): vagrant-clean-%-uploads:
	rm -rf $*-*-upload.json
