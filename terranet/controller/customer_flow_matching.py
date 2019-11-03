from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv6

import mac_learning_pipeline
from .ipv6_address_helper import IPv6AddressHelper


class CustomerFlowMatching(mac_learning_pipeline.MacLearningPipeline):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    SRC_MAC_TABLE = 100
    DST_MAC_TABLE = 101
    DN_TABLE = 3
    FIRST_CUSTOMER_TABLE = 4
    NEXT_TABLE = FIRST_CUSTOMER_TABLE

    def __init__(self, *args, **kwargs):
        self.customer_table_allocation = {}
        super(CustomerFlowMatching, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        super(CustomerFlowMatching, self).switch_features_handler(ev)
        datapath = ev.msg.datapath
        self._init_table_zero(datapath)
        self._init_dn_table(datapath)

    def _init_table_zero(self, datapath):
        parser = datapath.ofproto_parser
        table_id = 0

        # Send traffic to/ from DN subnets to DN table
        dn_table_id = self.__class__.DN_TABLE
        dn_match_inst = [parser.OFPInstructionGotoTable(dn_table_id)]

        dst_match = parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_dst=("fd00:0:0:8000::", "ffff:ffff:ffff:8000::"))
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=table_id,
                                match=dst_match,
                                instructions=dn_match_inst)
        datapath.send_msg(mod)

        src_match = parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_src=("fd00:0:0:8000::", "ffff:ffff:ffff:8000::"))
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=table_id,
                                match=src_match,
                                instructions=dn_match_inst)
        datapath.send_msg(mod)

        self.logger.info("CustomerFlowMatching: Initialized table {}. "
                         "Processing dn subnet match at table {}.".format(
                             table_id,
                             dn_table_id))

        # Send other traffic directly to MAC learning table
        src_mac_table_id = self.__class__.SRC_MAC_TABLE
        table_miss_inst = [parser.OFPInstructionGotoTable(src_mac_table_id)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=table_id,
                                match=parser.OFPMatch(),
                                instructions=table_miss_inst)
        datapath.send_msg(mod)
        self.logger.info("CustomerFlowMatching: Initialized table {}. "
                         "On table-miss send to table {}.".format(
                             table_id,
                             src_mac_table_id))

    def _init_dn_table(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        table_id = self.__class__.DN_TABLE
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=table_id,
                                priority=0,
                                match=parser.OFPMatch(),
                                instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("CustomerFlowMatching: Initialized DN table {}. "
                         "On table-miss send to controller.".format(table_id))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # MAC learning
        super(CustomerFlowMatching, self)._packet_in_handler(ev)
        msg = ev.msg
        in_port = msg.match["in_port"]

        table_id = msg.table_id
        self.logger.info("CustomerFlowMatching: Packet in at port {} "
                         "from table {}.".format(in_port,
                                                 table_id))

        if table_id == self.__class__.DN_TABLE:
            self._handle_new_distribution_subnet(ev)
        if (table_id >= self.__class__.FIRST_CUSTOMER_TABLE and
                table_id < self.__class__.SRC_MAC_TABLE):
            self._handle_new_customer_address(ev)

    def _handle_new_distribution_subnet(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        buffer_id = msg.buffer_id
        pkt = packet.Packet(msg.data)

        pkt_ipv6 = pkt.get_protocols(ipv6.ipv6)[0]
        subnet_prefix = IPv6AddressHelper.subnet_prefix(pkt_ipv6.src)
        subnet_id = IPv6AddressHelper.subnet_id(pkt_ipv6.src)
        dn_id = IPv6AddressHelper.distribution_id(pkt_ipv6.src)
        cn_id = IPv6AddressHelper.client_id(pkt_ipv6.src)
        self.logger.info("CustomerFlowMatching: Distribution/ Client network "
                         "detected. IPv6: {}, "
                         "Subnet prefix: {}, "
                         "Subnet id: {}, "
                         "Distibution node id: {}, "
                         "Client node id: {}.".format(pkt_ipv6,
                                                      subnet_prefix,
                                                      subnet_id,
                                                      dn_id,
                                                      cn_id))

        # Process traffic to/ from customers at customer table
        table_id = self.__class__.DN_TABLE
        dn_table_id = self._get_customer_table_id(ev)
        customer_inst = [parser.OFPInstructionGotoTable(dn_table_id)]

        dst_customer_match = parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_dst=("{}:8000::".format(subnet_prefix),
                      "ffff:ffff:ffff:ffff:8000::"))
        mod = parser.OFPFlowMod(datapath=datapath,
                                priority=200,
                                table_id=table_id,
                                match=dst_customer_match,
                                instructions=customer_inst)
        datapath.send_msg(mod)

        src_customer_match = parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_src=("{}:8000::".format(subnet_prefix),
                      "ffff:ffff:ffff:ffff:8000::"))
        mod = parser.OFPFlowMod(datapath=datapath,
                                priority=200,
                                table_id=table_id,
                                match=src_customer_match,
                                instructions=customer_inst)
        datapath.send_msg(mod)

        # Process other traffic from subnet at MAC learning table
        src_mac_table_id = self.__class__.SRC_MAC_TABLE
        client_net_inst = [parser.OFPInstructionGotoTable(src_mac_table_id)]

        dst_client_net_match = parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_dst=("{}::".format(subnet_prefix),
                      "ffff:ffff:ffff:ffff::"))
        mod = parser.OFPFlowMod(datapath=datapath,
                                priority=100,
                                table_id=table_id,
                                match=dst_client_net_match,
                                instructions=client_net_inst)
        datapath.send_msg(mod)

        src_client_net_match = parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_src=("{}::".format(subnet_prefix),
                      "ffff:ffff:ffff:ffff::"))
        mod = parser.OFPFlowMod(datapath=datapath,
                                buffer_id=buffer_id,
                                priority=100,
                                table_id=table_id,
                                match=src_client_net_match,
                                instructions=client_net_inst)
        datapath.send_msg(mod)

    def _get_customer_table_id(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        pkt = packet.Packet(msg.data)

        pkt_ipv6 = pkt.get_protocols(ipv6.ipv6)[0]
        dn_id = IPv6AddressHelper.distribution_id(pkt_ipv6.src)
        distribution_net = IPv6AddressHelper.distribution_net(pkt_ipv6.src)

        if not self.customer_table_allocation.get(dn_id):
            table_id = self.__class__.NEXT_TABLE
            self.customer_table_allocation[dn_id] = {
                "table_id": table_id}
            if distribution_net:
                dn_entry = self.customer_table_allocation[dn_id]
                dn_entry["distribution_net"] = distribution_net
            self.__class__.NEXT_TABLE += 1
            self._init_customer_table(datapath, table_id)

            self.logger.info("CustomerFlowMatching: "
                             "No table allocated for DN yet. "
                             "Allocated table {}".format(table_id))

        return self.customer_table_allocation[dn_id]["table_id"]

    def _init_customer_table(self, datapath, table_id):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=table_id,
                                priority=0,
                                match=parser.OFPMatch(),
                                instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("CustomerFlowMatching: Initialized table {}. "
                         "On table-miss send to controller.".format(table_id))

    def _handle_new_customer_address(self, ev):
        msg = ev.msg
        table_id = msg.table_id
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        buffer_id = msg.buffer_id
        pkt = packet.Packet(msg.data)
        pkt_ipv6 = pkt.get_protocols(ipv6.ipv6)[0]

        src_mac_table_id = self.__class__.SRC_MAC_TABLE
        inst = [parser.OFPInstructionGotoTable(src_mac_table_id)]

        customer_ips = []
        if IPv6AddressHelper.is_customer_address(pkt_ipv6.src):
            customer_ips.append(pkt_ipv6.src)
        if IPv6AddressHelper.is_customer_address(pkt_ipv6.dst):
            customer_ips.append(pkt_ipv6.dst)
        if not customer_ips:
            raise RuntimeError("CustomerFlowMatching: Packet does not include "
                               "customer ipv6 address.")

        for customer_ip in customer_ips:
            dst_match = parser.OFPMatch(
                eth_type=0x86dd,
                ipv6_dst=customer_ip)
            mod = parser.OFPFlowMod(datapath=datapath,
                                    table_id=table_id,
                                    match=dst_match,
                                    instructions=inst)
            datapath.send_msg(mod)

            src_match = parser.OFPMatch(
                eth_type=0x86dd,
                ipv6_src=customer_ip)
            mod = parser.OFPFlowMod(datapath=datapath,
                                    buffer_id=buffer_id,
                                    table_id=table_id,
                                    match=src_match,
                                    instructions=inst)
            datapath.send_msg(mod)

            self.logger.info("CustomerFlowMatching: "
                             "New customer: {} "
                             "added to table {}".format(pkt_ipv6,
                                                        table_id))
