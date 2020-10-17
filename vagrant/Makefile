#!make

BOXES := terranet terranet-base
PROVIDERS := aws virtualbox
BASE_TARGETS := all build clean

AWS_TARGET_SUFFIXES := $(addprefix aws-,$(BASE_TARGETS))
VIRTUALBOX_TARGET_SUFFIXES := $(addprefix virtualbox-,$(BASE_TARGETS))
PROVIDER_TARGET_SUFFIXES := $(AWS_TARGET_SUFFIXES) $(VIRTUALBOX_TARGET_SUFFIXES)
TERRANET_TARGETS := $(addprefix terranet-,$(PROVIDER_TARGET_SUFFIXES))
TERRANET_BASE_TARGETS := $(addprefix terranet-base-,$(PROVIDER_TARGET_SUFFIXES))

.PHONY: all $(BOXES)
all: $(BOXES)
$(BOXES): %: %-all

.PHONY: terranet-all terranet-aws terranet-virtualbox terranet-clean \
	$(TERRANET_TARGETS)
terranet-all: terranet-aws terranet-virtualbox
terranet-aws terranet-virtualbox: %: %-all
terranet-clean: terranet-aws-clean terranet-virtualbox-clean
$(TERRANET_TARGETS): terranet-%:
	$(MAKE) -C terranet $*

.PHONY: terranet-base-all terranet-base-aws terranet-base-virtualbox \
	terranet-base-clean $(TERRANET_BASE_TARGETS)
terranet-base-all: terranet-base-aws terranet-base-virtualbox
terranet-base-aws terranet-base-virtualbox: %: %-all
terranet-base-clean: terranet-base-aws-clean terranet-base-virtualbox-clean
$(TERRANET_BASE_TARGETS): terranet-base-%:
	$(MAKE) -C terranet-base $*

.PHONY: clean
clean: terranet-clean terranet-base-clean
