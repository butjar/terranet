.PHONY: generate simulate create_topo clean

BASE_CFG ?= ./cfg/terranet_000.cfg
TOPO_FILE ?= ./topo.py

all: generate_cfg simulate # create_topo

generate_cfg:
	./generate.py

simulate:
	komondor_simulator.py $(KOMONDOR_ARGS)

#create_topo:
#	mn_topo_generator.py --topo=$(BASE_CFG) > $(TOPO_FILE)
#	chmod +x $(TOPO_FILE)

clean:
	rm -rf cfg/*
	rm -rf out/*
	rm -rf $(TOPO_FILE)
