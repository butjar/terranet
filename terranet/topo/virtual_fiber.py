import ipaddress

from .terratopo import Terratopo
from ..wifi.channel import Channel


class HybridVirtualFiberTopo(Terratopo):
    '''
    mmWave Distribution Network backhaul
    ====================================

            +------+   60GHz  +------+   60GHz  +------+
            | dn_a |- - - - - | dn_b |- - - - - | dn_c |
            +------+          +------+          +------+
                |
                | cable
                |
            + -_-_- +
            |  _X_  | gw
            + - - - +
             | |    |
             | |    |  cable
             .-~~~-.|
     .- ~ ~-(| |     \)_ _
    /        / |      \    ~ -.
   |     s1a1 s1a2 ... s3c3     \ 
    \                        _.~'
      ~- . ______________ . -



    WiFi edge
    =========

        h1a1  ...  h5a1   h1b1  ...   h5b1  h1c1  ...   h5c1    (CPEs)
          \    |    /       \    |    /       \    |    /
       ^   \   |   /         \   |   /         \   |   /      -- cable
       |    +-----+           +-----+           +-----+
    20 |    |cn_a1|           |cn_b1|           |cn_b2|       (STAs/ CNs)
       |    +-----+           +-----+           +-----+
       |       .                 .                 .
       |       .                 .                 .
    10 |       .                 .                 .        ... 5GHz WiFi
       |       .                 .                 .
       |       .                 .                 .
       |    +------+          +------+          +------+
     0 |    | dn_a |          | dn_b |          | dn_c |      (APs/ DNs)
       |    +------+          +------+          +------+
       ----------------------------------------------->
     -15       0       25       50       75        100
    '''

    def build(self, *args, **kwargs):
        channel_list = [Channel(42), Channel(36), Channel(38), Channel(40),
                        Channel(44), Channel(46), Channel(48)]

        # Segment A
        dn_a = self.add_distribution_node_5_60(
            'dn_a',
            ssid='A',
            available_channels=channel_list,
            coordinates={'x': 0, 'y': 0, 'z': 0},
            proxy_port=8199)

        cn_a1 = self.add_client_node('cn_a1',
                                     coordinates={'x': 0, 'y': 20, 'z': 0})
        self.add_wifi_link(dn_a, cn_a1)


        # Segment B
        dn_b = self.add_distribution_node_5_60(
            'dn_b',
            ssid='B',
            available_channels=channel_list,
            coordinates={'x': 20, 'y': 0, 'z': 0},
            proxy_port=8299)

        cn_b1 = self.add_client_node('cn_b1',
                                     coordinates={'x': 50, 'y': 20, 'z': 0})
        self.add_wifi_link(dn_b, cn_b1)


        # Segment C
        dn_c = self.add_distribution_node_5_60(
            'dn_c',
            ssid='C',
            available_channels=channel_list,
            coordinates={'x': 40, 'y': 0, 'z': 0},
            proxy_port=8399)

        cn_c1 = self.add_client_node('cn_c1',
                                     coordinates={'x': 100, 'y': 20, 'z': 0})
        self.add_wifi_link(dn_c, cn_c1)


        # Add WiFi 60GHz Links between DN_A and DN_B
        self.add_terragraph_link(dn_a, dn_b)

        # Add WiFi 60GHz Links between DN_B and DN_C
        self.add_terragraph_link(dn_b, dn_c)

        # Add GW switch behind DN_A
        gw = self.add_gateway('s1')
        self.add_ip_link(gw, dn_a)

        # cn_a1 customer flows
        self._create_customer_flows(cn_a1, gw, 'a1',
                                    subnet=('10.145.128.0/24',
                                            'fd00:0:0:8101:8000::0/80'))

        # cn_b1 customer flows
        self._create_customer_flows(cn_b1, gw, 'b1',
                                    subnet=('10.161.128.0/24',
                                            'fd00:0:0:8201:8000::0/80'))

        # cn_c1 customer flows
        self._create_customer_flows(cn_c1, gw, 'c1',
                                    subnet=('10.177.128.0/24',
                                            'fd00:0:0:8301:8000::0/80'))
        super().build(*args, **kwargs)

    def _create_customer_flows(self, cn, gw, cn_suffix,
                               num_flows=5,
                               num_enabled=1,
                               subnet=('10.128.128.0/24',
                                       'fd00:0:0:8000:8000::0/80')):

        ipv4_net_address, ipv4_prefix_str = subnet[0].split('/')
        ipv4_prefix = int(ipv4_prefix_str)
        ipv6_net_address, ipv6_prefix_str = subnet[1].split('/')
        ipv6_prefix = int(ipv6_prefix_str)
        ipv4_subnets = list(
            ipaddress.ip_network('{}/{}'.format(ipv4_net_address,
                                                ipv4_prefix - 7))
                     .subnets(new_prefix=ipv4_prefix))
        ipv6_subnets = list(
            ipaddress.ip_network('{}/{}'.format(ipv6_net_address,
                                                ipv6_prefix - 7))
                     .subnets(new_prefix=ipv6_prefix))

        for i in range(1, (num_flows+1)):
            suffix = f'{i}{cn_suffix}'
            if i <= num_enabled:
                autostart_client = True
            else:
                autostart_client = False

            self.add_customer_flow(cn, gw,
                                   suffix=suffix,
                                   network=(ipv4_subnets[i],
                                            ipv6_subnets[i]),
                                   autostart_client=autostart_client)
