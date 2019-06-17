.PHONY: generate simulate clean

all: simulate

generate:
	./generate.py

simulate: generate
	komondor_simulator.py --komondor ../../../Komondor/Code/build/komondor_main

clean:
	rm -rf cfg/*
	rm -rf out/*
