from .terratopo import Terratopo
from ..wifi.channel import Channel

class HybridBackupTerragraphTopo(Terratopo):
    '''
    mmWave Distribution Network backhaul
    ====================================

            +-----+            +-----+
            |cn_a1|            |cn_b1|
            +-----+            +-----+
      5GHz .   |                  |   . 5GHz
          .                            .
    +----+     |                  |      +----+
    |ap_a|      60GHz        60GHz       |ap_b|
    +----+     |                  |      +----+
          \                            /
     cable \   |                  |   / cable
            +------+   60GHz  +------+
            | dn_a |- - - - - | dn_b |
            +------+          +------+
                |
                | cable
                |
            + -_-_- +
            |  _X_  | gw
            + - - - +
             | |  | |
             | |  |  \  cable
             .-~~~-~. \ 
     .- ~ ~-(| |  |    \)_ _
    /        / |   \    \   ~ -.
   |     s1a1 s1a2 s1b1 s2b1    \ 
    \                        _.~'
      ~- . ______________ . -



    WiFi backup edge
    =========

        h1a1 h2a1 h3a1    h1b1 h2b1 h3b1    (CPEs)
          \    |    /       \    |    /
       ^   \   |   /         \   |   /      -- cable
       |    +-----+           +-----+
    20 |    |cn_a1|           |cn_b1|      (STAs/ CNs)
       |    +-----+           +-----+
       |
       |       .                 .
    10 |       .                 .         ... 5GHz WiFi
       |       .                 .
       |       .                 .
       |    +------+          +------+
     0 |    | ap_a |          | ap_b |     (APs/ DNs)
       |    +------+          +------+
       ----------------------------->
     -15       0       25       50
    '''
    def build(self, *args, **kwargs):
        # Segment A
        channel_list_a = [
            Channel(42), # 80MHz
            Channel(38), Channel(46), # 40MHz
            Channel(36), Channel(40), Channel(44), Channel(48) # 20MHz
        ]
        dn_a = self.add_distribution_node_60('dn_a')
        ap_a = self.add_smart_access_point('ap_a',
                                           ssid='A',
                                           available_channels=channel_list_a,
                                           coordinates={'x': 0, 'y': 0})
        self.add_ip_link(dn_a, ap_a)
        cn_a1 = self.add_client_node('cn_a1',
                                     coordinates={'x': 0, 'y': 20})
        self.add_terragraph_link(dn_a, cn_a1)
        self.add_wifi_link(ap_a, cn_a1)


        # Segment B
        channel_list_b = [
            Channel(58), # 80MHz
            Channel(54), Channel(62), # 40MHz
            Channel(52), Channel(56), Channel(60), Channel(64) # 20MHz
        ]
        dn_b = self.add_distribution_node_60('dn_b')
        ap_b = self.add_smart_access_point('ap_b',
                                           ssid='B',
                                           available_channels=channel_list_b,
                                           coordinates={'x': 50, 'y': 0})
        self.add_ip_link(dn_b, ap_b)
        cn_b1 = self.add_client_node('cn_b1',
                                     coordinates={'x': 50, 'y': 20})
        self.add_terragraph_link(dn_b, cn_b1)
        self.add_wifi_link(ap_b, cn_b1)


        # Add WiFi 60GHz Links between DN_A and DN_B
        self.add_terragraph_link(dn_a, dn_b)

        # Add GW switch behind DN_A
        gw = self.add_gateway('s1')
        self.add_ip_link(gw, dn_a)

        # cn_a1 customer flows
        h1a1, s1a1 = self.add_customer_flow(cn_a1, gw,
                                            suffix='1a1',
                                            network=('10.145.128.0/24',
                                                     'fd00:0:0:8101:8001::0/80'),
                                            autostart_client=True)
        h2a1, s2a1 = self.add_customer_flow(cn_a1, gw,
                                            suffix='2a1',
                                            network=('10.145.129.0/24',
                                                     'fd00:0:0:8101:8002::0/80'),
                                            autostart_client=False)

        # cn_b1 customer flows
        h1b1, s1b1 = self.add_customer_flow(cn_b1, gw,
                                            suffix='1b1',
                                            network=('10.161.128.0/24',
                                                     'fd00:0:0:8201:8001::0/80'),
                                            autostart_client=True)
        h2b1, s2b1 = self.add_customer_flow(cn_b1, gw,
                                            suffix='2b1',
                                            network=('10.161.129.0/24',
                                                     'fd00:0:0:8201:8002::0/80'),
                                            autostart_client=False)
