#!make

PROVIDERS := aws virtualbox
BASE_TARGETS := all build clean

AWS_TARGETS := $(addprefix aws-,$(BASE_TARGETS))
VIRTUALBOX_TARGETS := $(addprefix virtualbox-,$(BASE_TARGETS))

.PHONY: all
all: aws virtualbox

.PHONY: aws $(AWS_TARGETS)
aws: aws-all
$(AWS_TARGETS): aws-%:
	$(MAKE) -C aws $*

.PHONY: virtualbox $(VIRTUALBOX_TARGETS)
virtualbox: virtualbox-all
$(VIRTUALBOX_TARGETS): virtualbox-%:
	$(MAKE) -C virtualbox $*

.PHONY: clean
clean: aws-clean virtualbox-clean
