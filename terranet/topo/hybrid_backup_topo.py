from .terratopo import Terratopo
from ..wifi.channel import Channel

class HybridBackupTerragraphTopo(Terratopo):
    '''
    mmWave Distribution Network backhaul
    ====================================

            +-----+            +-----+           +-----+
            |cn_a1|            |cn_b1|           |cn_c1|
            +-----+            +-----+           +-----+
      5GHz .   |             .    |            .    |
          .                 .                 .
    +----+     |      +----+      |     +----+      |
    |ap_a|   60GHz    |ap_b|    60GHz   |ap_c|    60GHz
    +----+     |      +----+      |     +----+      |
          \                 \                 \ 
     cable \   |             \    |            \    |
            +------+  60GHz   +------+  60GHz   +------+
            | dn_a |- - - - - | dn_b |- - - - - | dn_c |
            +------+          +------+          +------+
                |
                | cable
                |
            + -_-_- +
            |  _X_  | gw
            + - - - +
              | | |
              | | | cable
             .-~~~-~.
     .- ~ ~-(         )_ _
    /                      ~ -.
   |  s1a1 s1b1 s1c1 s2c1 s3c1  \ 
    \                        _.~'
      ~- . ______________ . -



    WiFi backup edge
    ================

             h1a1              h1b1         h1c1 h2c1 h3c1    (CPEs)
               |                 |            \    |    /
       ^       |                 |             \   |   /     -- cable
       |    +-----+           +-----+           +-----+
    20 |    |cn_a1|           |cn_b1|           |cn_b2|     (STAs/ CNs)
       |    +-----+           +-----+           +-----+
       |       .                 .                 .
       |       .                 .                 .
    10 |       . CH:42           .      CH:58      .        ... 5GHz WiFi
       |       .                 .                 .
       |       .                 .                 .
       |    +------+          +------+          +------+
     0 |    | ap_a |          | ap_b |          | ap_c |    (APs/ DNs)
       |    +------+          +------+          +------+
       ----------------------------------------------->
     -15       0       25       50       75        100
    '''
    def build(self, *args, **kwargs):
        # Segment A
        channel_list_a = [
            Channel(42), # 80MHz
            Channel(38), Channel(46), # 40MHz
            Channel(36), Channel(40), Channel(44), Channel(48) # 20MHz
        ]
        dn_a = self.add_distribution_node_60('dn_a')
        ap_a = self.add_smart_access_point(
            'ap_a',
            ssid='A',
            available_channels=channel_list_a,
            coordinates={'x': 0, 'y': 0}
        )
        self.add_ip_link(dn_a, ap_a)

        cn_a1 = self.add_client_node('cn_a1', coordinates={'x': 0, 'y': 20})
        self.add_terragraph_link(dn_a, cn_a1)
        self.add_wifi_link(ap_a, cn_a1)


        # Segment B
        channel_list_b = [
            Channel(58), # 80MHz
            Channel(54), Channel(62), # 40MHz
            Channel(52), Channel(56), Channel(60), Channel(64) # 20MHz
        ]
        dn_b = self.add_distribution_node_60('dn_b')
        ap_b = self.add_smart_access_point(
            'ap_b',
            ssid='B',
            available_channels=channel_list_b,
            coordinates={'x': 50, 'y': 0}
        )
        self.add_ip_link(dn_b, ap_b)

        cn_b1 = self.add_client_node('cn_b1', coordinates={'x': 50, 'y': 20})
        self.add_terragraph_link(dn_b, cn_b1)
        self.add_wifi_link(ap_b, cn_b1)


        # Segment C
        channel_list_c = [
            Channel(58), # 80MHz
            Channel(54), Channel(62), # 40MHz
            Channel(52), Channel(56), Channel(60), Channel(64) # 20MHz
        ]
        dn_c = self.add_distribution_node_60('dn_c')
        ap_c = self.add_smart_access_point(
            'ap_c',
            ssid='C',
            available_channels=channel_list_c,
            coordinates={'x': 100, 'y': 0}
        )
        self.add_ip_link(dn_c, ap_c)

        cn_c1 = self.add_client_node('cn_c1', coordinates={'x': 100, 'y': 20})
        self.add_terragraph_link(dn_c, cn_c1)
        self.add_wifi_link(ap_c, cn_c1)


        # Add WiFi 60GHz Links between DN_A and DN_B
        self.add_terragraph_link(dn_a, dn_b)
        self.add_terragraph_link(dn_b, dn_c)

        # Add GW switch behind DN_A
        gw = self.add_gateway('s1')
        self.add_ip_link(gw, dn_a)

        # cn_a1 customer flows
        h1a1, s1a1 = self.add_customer_flow(cn_a1, gw,
            suffix='1a1',
            network=('10.145.129.0/24',
                     'fd00:0:0:8101:8001::0/80'),
            autostart_client=True
        )

        # cn_b1 customer flows
        h1b1, s1b1 = self.add_customer_flow(cn_b1, gw,
            suffix='1b1',
            network=('10.161.129.0/24',
                     'fd00:0:0:8201:8001::0/80'),
            autostart_client=True
        )

        # cn_c1 customer flows
        h1c1, s1c1 = self.add_customer_flow(cn_c1, gw,
            suffix='1c1',
            network=('10.177.129.0/24',
                     'fd00:0:0:8301:8001::0/80'),
            autostart_client=True
        )
        h2c1, s2c1 = self.add_customer_flow(cn_c1, gw,
            suffix='2c1',
            network=('10.177.130.0/24',
                     'fd00:0:0:8301:8002::0/80'),
            autostart_client=True
        )
        h3c1, s3c1 = self.add_customer_flow(cn_c1, gw,
            suffix='3c1',
            network=('10.177.131.0/24',
                     'fd00:0:0:8301:8003::0/80'),
            autostart_client=True
        )
