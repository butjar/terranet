#!make

SHELL := /bin/bash
TERRANET_BASE_VERSION := $(shell cat ../../../TERRANET_BASE_VERSION)
_TERRANET_BASE_VERSION := $(subst .,_,$(TERRANET_BASE_VERSION))

ATLAS_ENV := ../../../atlas.env
include $(ATLAS_ENV)
export $(shell sed 's/=.*//' $(ATLAS_ENV))
ATLAS_CLOUD_API :=  https://app.vagrantup.com/api/v1
ATLAS_CLOUD_BOX_RESOURCE := $(ATLAS_CLOUD_API)/box/$(ATLAS_USER)/terranet-base
ATLAS_CLOUD_VERSION_RESOURCE := $(ATLAS_CLOUD_BOX_RESOURCE)/version/$(TERRANET_BASE_VERSION)
ATLAS_CLOUD_AWS_PROVIDER_RESOURCE := \
	$(ATLAS_CLOUD_VERSION_RESOURCE)/provider/aws

INSTALL_SCRIPT := ../../../install/install_terranet_base.sh
BUILD_SRCS := packer.json \
	$(INSTALL_SCRIPT)
BUILD_ARTIFACT := build/$(_TERRANET_BASE_VERSION)/package.box
RELEASE_SRCS := packer.json
RELEASE_ARTIFACTS := $(BUILD_ARTIFACT) \
	build/$(_TERRANET_BASE_VERSION)/provider.json

.PHONY: all build
all: build/$(_TERRANET_BASE_VERSION)/provider.json # Build n' release
build: $(BUILD_ARTIFACT)

$(BUILD_ARTIFACT):: $(BUILD_SRCS)
	packer build -var 'version=$(TERRANET_BASE_VERSION)' \
				 -var '_version=$(_TERRANET_BASE_VERSION)' \
				 -var 'script=$(INSTALL_SCRIPT)' \
				 -except='vagrant-cloud-uploader' \
				 $<

$(RELEASE_ARTIFACTS) &:: $(RELEASE_SRCS)
	packer build -var 'version=$(TERRANET_BASE_VERSION)' \
				 -var '_version=$(_TERRANET_BASE_VERSION)' \
				 -var 'script=$(INSTALL_SCRIPT)' \
				 $<
	resp=$$(curl -f $(ATLAS_CLOUD_AWS_PROVIDER_RESOURCE)) \
		 && echo $$resp | jq '.' > $@

.PHONY: clean
clean:
	rm -f *.log
	rm -rf build
