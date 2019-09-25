# Single 160MHz band
This example emulates a terranet access network with two distribution nodes for
all possible channel configurations in a single 160MHz band.

## Simulation
### Channels

### Network nodes
```
   ^
   |  +--+      +--+      +--+      +--+      +--+
20 |  |A1|      |A2|      |B1|      |B2|      |B3|   (STAs/ CNs)
   |  +--+      +--+      +--+      +--+      +--+
   |      \      |            \      |      /
   |       \     |             \     |     /
10 |        \    |              \    |    /
   |         \   |               \   |   /
   |          \  |                \  |  /
   |          +-----+             +-----+
 0 |          |  A  |             |  B  |            (APs/ DNs)
   |          +-----+             +-----+
   ---------------------------------------------->
       10   20   30   40   50   60   70   80   90
```

## Generate files
Running the example requires several steps:
1. Generation of the config files
2. Simulation of the link speeds
3. Creation of a terranet topology file

All steps have been automated in the Makefile. Be sure you have terranet
installed and run `make`.

If komondor is not available in path run:

```
KOMONDOR_ARGS="--komondor ./path/to/komondor_main" make
```
