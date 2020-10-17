#!make

SHELL := /bin/bash
VERSION := $(shell cat ../../../VERSION)
_VERSION := $(subst .,_,$(VERSION))
TERRANET_BASE_AMI := $(shell cat ../../../TERRANET_BASE_AMI)

ATLAS_ENV := ../../../atlas.env
include $(ATLAS_ENV)
export $(shell sed 's/=.*//' $(ATLAS_ENV))
ATLAS_CLOUD_API :=  https://app.vagrantup.com/api/v1
ATLAS_CLOUD_BOX_RESOURCE := $(ATLAS_CLOUD_API)/box/$(ATLAS_USER)/terranet-base
ATLAS_CLOUD_VERSION_RESOURCE := $(ATLAS_CLOUD_BOX_RESOURCE)/version/$(VERSION)
ATLAS_CLOUD_AWS_PROVIDER_RESOURCE := \
	$(ATLAS_CLOUD_VERSION_RESOURCE)/provider/aws

BUILD_SRCS := packer.json
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
				 -var 'aws_source_ami=$(TERRANET_BASE_AMI)' \
				 -except='vagrant-cloud-uploader' \
				 $<

$(RELEASE_ARTIFACTS) &:: $(RELEASE_SRCS)
	packer build -var 'version=$(VERSION)' \
				 -var '_version=$(_VERSION)' \
				 -var 'aws_source_ami=$(TERRANET_BASE_AMI)' \
				 -var 'script=$(INSTALL_SCRIPT)' \
				 $<
	resp=$$(curl -f $(ATLAS_CLOUD_AWS_PROVIDER_RESOURCE)) \
		 && echo $$resp | jq '.' > $@

.PHONY: clean
clean:
	rm -f *.log
	rm -rf build
