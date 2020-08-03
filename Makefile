#!make
SHELL := /bin/bash

VERSION = $(shell cat VERSION)
VAGRANTFILE_BUILD = Vagrantfile.build
include atlas.env
export $(shell sed 's/=.*//' atlas.env)

provider = virtualbox
machines = terranet-base terranet
boxes = $(addsuffix .box,$(machines))
release_targets = $(addprefix release-,$(machines))
upload_targets = $(addsuffix -upload.json,$(machines))
clean_targets = $(addprefix clean-,$(machines))
clean_box_targets = $(addsuffix -box,$(clean_targets))
clean_upload_targets = $(addprefix clean-,$(upload_targets))

.PHONY: $(machines)
$(machines): %: .vagrant/machines/%/$(provider)/id

.vagrant/machines/%/$(provider)/id: $(VAGRANTFILE_BUILD)
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant plugin install vagrant-disksize --local
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant up $*
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant reload $*

$(boxes): %.box: .vagrant/machines/%/$(provider)/id
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant package $* --base $$(cat .vagrant/machines/$*/$(provider)/id) --output $@

# See: https://www.vagrantup.com/vagrant-cloud/boxes/create
.INTERMEDIATE: $(upload_targets)
terranet-upload.json: version = $(shell cat VERSION)
terranet-base-upload.json: version = $(shell cat BASEVM_VERSION)
$(upload_targets): %-upload.json: %.box
	curl -o $@ -v "https://vagrantcloud.com/api/v1/box/$(ATLAS_USER)/$*/version/$(version)/provider/$(provider)/upload?access_token=$(ATLAS_ACCESS_TOKEN)"

.PHONY: $(release_targets)
$(release_targets): release-%: %-upload.json
	curl -v -XPUT --upload-file $*.box $$(cat $< | jq -r '.upload_path')

.PHONY: clean $(clean_targets) $(clean_box_targets) $(clean_upload_targets)
clean: $(clean_targets)

$(clean_targets): clean-%: clean-%-box clean-%-upload.json
	VAGRANT_VAGRANTFILE=$(VAGRANTFILE_BUILD) vagrant destroy $* -f
	rm -rf .vagrant/machines/$*

$(clean_box_targets): clean-%-box:
	rm -rf $*.box

$(clean_upload_targets): clean-%:
	rm -rf $*
