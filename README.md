# terranet
Simulate a terragraph network in ip mininet. This approach is a two step
simulation. In the first step the wireless network is simulated in our
[komondor fork](https://github.com/Bustel/Komondor). The mininet simulation
creates a network and adjusts the link speeds according to the simulation
results from the first simulation. Terranet builds on top of the
[ipmininet](https://github.com/cnp3/ipmininet) mininet plugin.

# Install terranet
Wtih setuptools:

```
python setup.py install
```

With pip (from parent directory):

```
pip install terranet/
```

# Create mininet topology
Run the mn_topo_generator executable:

```
python ./bin/mn_topo_generator.py --topo=simulations/in/telegraph_gen_network_1.cfg
```
