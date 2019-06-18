BASE_CFG ?= ./cfg/$(shell ls ./cfg | head -n1)

.PHONY: generate simulate create_topo clean terranet.py

all: generate_cfg simulate $(TOPO_FILE)

generate_cfg:
	./generate.py

simulate:
	komondor_simulator.py $(KOMONDOR_ARGS)

terranet.py:
	mn_topo_generator.py --topo=$(BASE_CFG) > $@
	chmod +x $(TOPO_FILE)

clean:
	rm -rf cfg/*
	rm -rf out/*
	rm -rf $(TOPO_FILE)
