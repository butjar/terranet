#!make

SHELL := /bin/bash
VERSION := $(shell cat ../../../VERSION)
_VERSION := $(subst .,_,$(VERSION))

ATLAS_ENV := ../../../atlas.env
include $(ATLAS_ENV)
export $(shell sed 's/=.*//' $(ATLAS_ENV))
ATLAS_CLOUD_API :=  https://app.vagrantup.com/api/v1
ATLAS_CLOUD_BOX_RESOURCE := $(ATLAS_CLOUD_API)/box/$(ATLAS_USER)/terranet
ATLAS_CLOUD_VERSION_RESOURCE := $(ATLAS_CLOUD_BOX_RESOURCE)/version/$(VERSION)
ATLAS_CLOUD_VIRTUALBOX_PROVIDER_RESOURCE := \
	$(ATLAS_CLOUD_VERSION_RESOURCE)/provider/virtualbox

BUILD_SRCS := packer.json \
	Vagrantfile.tpl \
	Vagrantfile
BUILD_ARTIFACT := build/$(_VERSION)/package.box
RELEASE_SRCS := packer.json
RELEASE_ARTIFACTS := $(BUILD_ARTIFACT) \
	build/$(_VERSION)/provider.json

.PHONY: all build
all: build/$(_VERSION)/provider.json # Build n' release
build: $(BUILD_ARTIFACT)

$(BUILD_ARTIFACT):: $(BUILD_SRCS)
	packer build -var 'version=$(VERSION)' \
				 -var '_version=$(_VERSION)' \
				 -except='vagrant-cloud-uploader' \
				 $<

$(RELEASE_ARTIFACTS) &:: $(RELEASE_SRCS)
	packer build -var 'version=$(VERSION)' \
				 -var '_version=$(_VERSION)' \
				 $<
	resp=$$(curl -f $(ATLAS_CLOUD_VIRTUALBOX_PROVIDER_RESOURCE)) \
		 && echo $$resp | jq '.' > $@

.PHONY: clean
clean:
	rm -f *.log
	rm -rf build
