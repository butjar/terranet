# Single 160MHz band
This example simulates two networks with all possible channel configurations in
a single 160MHz band.

## Network

```
   ^
   |
20 |  A1  A2  B1  B2  B3
   |   \  |    \  |  /
10 |    \ |     \ | /
   |     \|      \|/
 0 |      A       B
   ---------------------->
      10  20  30  40  50
```

## Generate files
Running the example requires several steps:
1. Generation of the config files
2. Simulation of the link speeds
3. Creation of the (terra)mininet topology

All steps have been automated in the Makefile. Be sure you have terranet
installed and run `make`.

If komondor is not available in path run:

```
KOMONDOR_ARGS="--komondor ./path/to/komondor_main" make
```
