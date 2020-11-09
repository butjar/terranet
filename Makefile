#!make

# pypi
include pypi.mk

# Vagrant
BOXES := terranet terranet-base
PROVIDERS := aws virtualbox
BASE_TARGETS := all build clean

PROVIDER_TARGET_SUFFIXES := aws virtualbox
PROVIDER_TARGET_SUFFIXES += $(foreach provider,$(PROVIDERS),\
	$(addprefix $(provider)-,$(BASE_TARGETS)))

BOX_TARGET_SUFFIXES := terranet terranet-clean \
	terranet-base terranet-base-clean
BOX_TARGET_SUFFIXES += $(foreach box,$(BOXES),\
	$(addprefix $(box)-,$(PROVIDER_TARGET_SUFFIXES)))

VAGRANT_TARGETS := vagrant-all vagrant-clean
VAGRANT_TARGETS += $(addprefix vagrant-,$(BOX_TARGET_SUFFIXES))

.PHONY: vagrant $(VAGRANT_TARGETS)
vagrant: vagrant-all
$(VAGRANT_TARGETS): vagrant-%:
	$(MAKE) -C vagrant $*


# Main targets
.PHONY: release release-terranet release-terranet-base
release: release-terranet release-terranet-base
release-terranet: release-%: pypi-release-%-dist vagrant-%
release-terranet-base: release-%: vagrant-%

.PHONY: clean
clean:
	rm -rf *.log *.egg-info

.PHONY: clean-all clean-terranet clean-terranet-base
clean-all: clean clean-terranet clean-terranet-base
clean-terranet: pypi-clean vagrant-terranet-clean
clean-terranet-base: vagrant-terranet-base-clean
