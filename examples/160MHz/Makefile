BASE_CFG ?= ./cfg/$(shell ls ./cfg | head -n1)
TOPO_FILE = terranet.py

.PHONY: generate simulate create_topo clean

all: generate_cfg simulate $(TOPO_FILE)

generate_cfg:
	./generate.py

simulate:
	komondor_simulator.py $(KOMONDOR_ARGS)

$(TOPO_FILE): $(BASE_CFG)
	mn_topo_generator.py --topo=$< > $@
	chmod +x $(TOPO_FILE)

$(BASE_CFG): ;

clean:
	rm -rf cfg/*
	rm -rf out/*
	rm -rf $(TOPO_FILE)
