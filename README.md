# Terranet
Terranet is an emulator for wireless access networks based on [virtual
fiber](https://www.telekom.com/en/company/details/virtual-fiber-563322) and
[terragraph](https://terragraph.com/). Terranet networks have a wireless
backbone connected by mmWave Links (60GHz). The wireless last mile - the
connection between the wireless backbone and the customer premises - is
connected with 5GHz WiFi equipment.

## Concept
### Architecture
```
+-----+  +-----+    +-----+  +-----+           +-----+ +-----+  +-----+
| CPE |  | CPE |    | CPE |  | CPE |           | CPE | | CPE |  | CPE |
+-----+  +-----+    +-----+  +-----+           +-----+ +-----+  +-----+
      \  /              \   /                         \   |    /
    +----+            +----+                            +----+
    | CN |            | CN |                            | CN |
    +----+            +----+                            +----+
       \\            //                                   ||
        \\          //                                    ||
         \\        //                                     ||
          +--------+                                  +--------+
          | DN5_60 |-  -  -  -  -  -  -  -  -  -  -  -| DN5_60 |
          |  (GW)  |                                  +--------+
          +--------+
              |
       +-------------+
       |             |
       | ISP Network |
       |             |
       +-------------+
              |
          .-~~~-.
  .- ~ ~-(       )_ _                   cable connection  ---------- (straight)
 /                     ~ -.         5GHz Wifi connection  ========== (double)
|         Internet          \      60GHz Wifi connection  -  -  -  - (dotted)
 \                         .'
   ~- . _____________ . -~
```

- DN - Distribution node: Backbone router of the wireless access network.
  Distribution nodes are connected to other distribution nodes over 60GHz
  links. The numbers behind the distribution node show which spectrum is used
  e.g. a DN5_60 is connected to client nodes via 5GHz links, to other
  distribution nodes it is connected via 60GHz links. Some distribution nodes
  are connected to the internet service provider's (ISP) network, other
  distribution nodes forward traffic to these gateways. Distribution nodes
  form a terragraph mesh network.
- CN - Client node: Router that forwards customer traffic to the wireless
  backbone network. A client node is connected to a single distribution node
  and has multiple customers connected via their CPE. The connection between
  client nodes and CPEs can be cabled or wireless.
- CPE - Customer premises equipment: Customer equipment for internet access
  over the wireless access network. A CPE could be a regular home router. A CPE
  is connected to a single client node via cable or wireless.

### Routing
To forward traffic from the customer over the wireless access network to the
ISP's core network the network nodes run the
[OpenR](https://code.fb.com/connectivity/introducing-open-r-a-new-modular-routing-platform/)
routing platform. Both, distribution nodes and client nodes run an [OpenR
daemon](https://github.com/facebook/openr) to exchange routes.

## Implementation
### Two-step emulation
The emulation of the wireless access network with terranet is separated in two
steps:

1. Simulation of 5GHz link speeds and delays between distribution and client
   nodes with
   [komondor](https://github.com/wn-upf/Komondor).
2. Network emulation with the terranet [mininet](http://mininet.org/)/
   [ipmininet](https://github.com/cnp3/ipmininet) extension.

### Komondor WiFi simulation
Distribution nodes and client nodes are connected through 5GHz WiFi links. The
distribution nodes are WiFi access points, client nodes connect as WiFi
stations. We call this the wireless fronthaul of the access network as opposed
to the wireless backbone connecting the distribution nodes. Terranet does not
really run WiFi access points or stations. The mininet based network has nodes,
i.e. network namespaces that isolate the nodes networks, connected through veth
pairs.

Basically, the wireless fronthaul is simulated in komondor, a 802.11ax WiFi
Simulator. Before launching the mininet based network, all possible WiFi
configurations must be pre-simulated with our [komondor
fork](https://github.com/Bustel/Komondor).

### Terranet network emulation
Terranet is a mininet/ ipmininet extension. The class naming follows the
components introduced in [architecture](###-architecture). The `Terranet` class
itself extends ipmininet's `IPNet`. A `Terranet` holds a reference to the
`FronthaulEmulator` of the network that emulates the wireless 5GHz fronthaul of
the wireless access network. The `FronthaulEmulator` implements an observer
based event handling to adjust link speeds and delays to emulate the wireless
fronthaul. The [next section](###-emulating-wifi-links-in-terranet) explains
this emulation in detail.

Mininet uses linux [network
namespaces](http://man7.org/linux/man-pages/man8/ip-netns.8.html) to isolate
the network stacks of several `Node`s. `Link`s connect `Node`s to form a
network topology. `Link`s are basically [veth
pairs](http://man7.org/linux/man-pages/man4/veth.4.html) plugged into the
network namespaces of the `Node`s.

Ipmininet is a mininet extension for building IP based networks with mininet.
Terranet builds on top of ipmininet for two reasons:

1. Support for `Router` nodes that run routing daemons, especially the `OpenR`
   daemon
2. Support for IPv6 which is essential for running OpenR

Most terranet classes extend ipmininet classes. `ClientNode`s and
`DistributionNode`s extend ipmininets `Router` class to run the OpenR daemon
that exchanges the routes between the `Node`s.

Moreover, the terranet module ships [scripts](bin), that help running the
komondor simulation required for the emulation of the 5GHz fronthaul. In the
[example directory](example) we demonstrate a terranet emulation of a wireless
fronthaul occupying the spectrum of a single [160MHz band](examples/160MHz).
Please consult the documentation of this example for more details.

### Emulating WiFi links in terranet
Terranet reads komondor configuration and result files and adjusts the
resulting WiFi link bandwidths and delays of the interfaces with respect to the
komondor simulation. To limit the link bandwidth, mininets `TCIntf` are
configured with token bucket filters (tbf). Since WiFi links potentially
operate in the same collision domain, the selection of the appropriate
simulation results requires the knowledge of the whole fronthaul configuration.
Therefore, terranet has a central component, the `FronthaulEmulator`, that
applies the simulation results of the fronthaul to all relevant interfaces.

Configuration changes can be triggered to the client nodes, via the
`ConfigAPI`. Currently only channel switches, i.e. changes of the WiFi
channels, are supported. If the `ConfigAPI` of a client node receives a channel
switch request, the client node changes it's channel configuration and informs
the `FronthaulEmulator` about the change. The `FronthaulEmulator` selects the
simulation configurations and results according to the new fronthaul
configuration and adjusts the configuration of the link bandwidths and delays
by configuring the `TCIntf`s.

Following drawing illustrates how a channel switch is applied in terranet:

```
+----+             +----+                 +----+             +----+
| CN |             | CN |                 | CN |             | CN |
+----+             +----+                 +----+             +----+
   \\               //                       \\               //
    \\             //                         \\             //
     \\           //                           \\           //
+-----------------------+                 +-----------------------+
| +--------+ +--------+ |                 | +--------+ +--------+ |
| | TCIntf | | TCIntf | |                 | | TCIntf | | TCIntf | |
| +--------+ +--------+ |                 | +--------+ +--------+ |
|     ^          ^      |                 |     ^          ^      |
|     |          |      |                 |     |          |      |
|     +----------+--------------+---------------+----------+      |
|        DN5_60         |       | 3.      |        DN5_60         |
|     +-----------+     |  +-----------+  |     +-----------+     |
|     | ConfigAPI |------->| Fronthaul |  |     | ConfigAPI |     |
|     +-----------+  2. |  | Emulator  |  |     +-----------+     |
+----------^------------+  +-----------+  +-----------------------+
           | 1.
     +-----------+
     | ConfigAPI |
     |  Client   |
     +-----------+
```

1. A client (e.g. a SDN controller ) requests a channel switch to the
   `ConfigAPI` of a DistributionNode5_60.
2. The distribution node changes it's configuration and informs the
   `FronthaulEmulator` about the channel switch.
3. The `FronthaulEmulator` builds the komondor configuration of the whole
   network, looks up for the appropriate file in the simulation configurations
   directory and selects the appropriate file with the simulation results. The
   `FronthaulEmulator` configures the interfaces with the resulting bandwidths
   and delays.

## Installing and running terranet
### Dependencies
#### Komondor
The WiFi link simulation requires the installation of our [komondor
fork](https://github.com/Bustel/Komondor). Clone the repository from github and
build the komondor binary using `cmake`:

#### Openr
Openr is the routing daemon running in distribution and client nodes of
terranet. Before running a terranet emulation you have to build and install
Openr. Usually, Openr is build in docker containers, see
https://github.com/facebook/openr/tree/master/build. You can use the
`debian_system_builder` to build Openr for `ubuntu 16.04`, consult
https://github.com/facebook/openr/tree/master/build#build-on-debian-host-without-docker
for further instructions.

#### Mininet and Ipmininet
Mininet and ipmininet are python modules that can be installed with
`setuptools` or `pip`. However, both have additional external dependencies. The
`util` directories of both projects include install scripts for installation of
dependencies and required system configurations:

- https://github.com/mininet/mininet/tree/master/util
- https://github.com/cnp3/ipmininet/tree/master/util

#### Ipmininet install scripts
You can use ipmininets install script to install `mininet`, `ipmininet` and
`openr` and its dependencies and configuration requirements in one go:

```
python util/install.py -iamf
```

### Install terranet module
Python requirements of terranet are defined in the `requirements.txt` file.
Install the requirements with `pip` before running terranet:

```
pip install -r requirements.txt
```

To install terranet with `setuptools`:

```
python setup.py install -f
```

Alternatively you can install terranet using `pip` (from parent directory):

```
pip install terranet/
```

