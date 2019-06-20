BASE_CFG ?= ./cfg/$(shell ls ./cfg | head -n1)

.PHONY: generate simulate create_topo clean terranet

all: generate_cfg simulate terranet

generate_cfg:
	./generate.py

simulate:
	komondor_simulator.py $(KOMONDOR_ARGS)

terranet:
	mn_topo_generator.py --topo=$(BASE_CFG) > $@_topo.py
	chmod +x $@_topo.py

clean:
	rm -rf cfg/*
	rm -rf out/*
	rm -rf terranet_topo.py
