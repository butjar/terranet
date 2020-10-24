from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller.event import EventBase
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv6

from .mac_learning_pipeline import MacLearningPipeline
from .ipv6_address_helper import IPv6AddressHelper


class EventCustomerFlowAdded(EventBase):
    def __init__(self, customer_ipv6):
        super().__init__()
        self.customer_ipv6 = customer_ipv6


class EventCustomerFlowRemoved(EventBase):
    def __init__(self, customer_ipv6):
        super().__init__()
        self.customer_ipv6 = customer_ipv6


class CustomerFlowPipeline(MacLearningPipeline):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    SRC_MAC_TABLE = 100
    DST_MAC_TABLE = 101
    DN_TABLE = 3
    FIRST_CUSTOMER_TABLE = 4
    NEXT_TABLE = FIRST_CUSTOMER_TABLE
    CUSTOMER_FLOW_IDLE_TIMEOUT = 10

    _EVENTS = [
        EventCustomerFlowAdded,
        EventCustomerFlowRemoved
    ]

    def __init__(self, *args, **kwargs):
        self.customer_table_allocation = {}
        super().__init__(*args, **kwargs)

    def _notify_customer_event_flow_added(self, customer_ipv6):
        ev = EventCustomerFlowAdded(customer_ipv6)
        self.send_event_to_observers(ev)
        self.logger.info('CustomerFlowPipeline: '
                         'Sent event {} to observers.'
                         .format(ev.__class__.__name__))

    def _notify_customer_event_flow_removed(self, customer_ipv6):
        ev = EventCustomerFlowRemoved(customer_ipv6)
        self.send_event_to_observers(ev)
        self.logger.info('CustomerFlowPipeline: '
                         'Sent event {} to observers.'
                         .format(ev.__class__.__name__))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        super().switch_features_handler(ev)
        datapath = ev.msg.datapath
        self._init_table_zero(datapath)
        self._init_dn_table(datapath)

    def _init_table_zero(self, datapath):
        ofp_parser = datapath.ofproto_parser
        table_id = 0

        # Send traffic to/ from DN subnets to DN table
        dn_table_id = self.__class__.DN_TABLE
        dn_match_inst = [ofp_parser.OFPInstructionGotoTable(dn_table_id)]

        dst_match = ofp_parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_dst=("fd00:0:0:8000::", "ffff:ffff:ffff:8000::"))
        mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                    table_id=table_id,
                                    match=dst_match,
                                    instructions=dn_match_inst)
        datapath.send_msg(mod)

        src_match = ofp_parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_src=("fd00:0:0:8000::", "ffff:ffff:ffff:8000::"))
        mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                    table_id=table_id,
                                    match=src_match,
                                    instructions=dn_match_inst)
        datapath.send_msg(mod)

        self.logger.info("CustomerFlowPipeline: Initialized table {}. "
                         "Processing dn subnet match at table {}.".format(
                             table_id,
                             dn_table_id))

        # Send other traffic directly to MAC learning table
        src_mac_table_id = self.__class__.SRC_MAC_TABLE
        table_miss_inst = [ofp_parser.OFPInstructionGotoTable(src_mac_table_id)]
        mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                    table_id=table_id,
                                    match=ofp_parser.OFPMatch(),
                                    instructions=table_miss_inst)
        datapath.send_msg(mod)
        self.logger.info("CustomerFlowPipeline: Initialized table {}. "
                         "On table-miss send to table {}.".format(
                             table_id,
                             src_mac_table_id))

    def _init_dn_table(self, datapath):
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        table_id = self.__class__.DN_TABLE
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        inst = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
        mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                    table_id=table_id,
                                    priority=0,
                                    match=ofp_parser.OFPMatch(),
                                    instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("CustomerFlowPipeline: Initialized DN table {}. "
                         "On table-miss send to controller.".format(table_id))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # MAC learning
        super()._packet_in_handler(ev)
        msg = ev.msg
        in_port = msg.match["in_port"]

        table_id = msg.table_id
        self.logger.info("CustomerFlowPipeline: Packet in at port {} "
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
        ofp_parser = datapath.ofproto_parser
        buffer_id = msg.buffer_id
        pkt = packet.Packet(msg.data)

        pkt_ipv6 = pkt.get_protocols(ipv6.ipv6)[0]
        subnet_prefix = IPv6AddressHelper.subnet_prefix(pkt_ipv6.src)
        subnet_id = IPv6AddressHelper.subnet_id(pkt_ipv6.src)
        dn_id = IPv6AddressHelper.distribution_id(pkt_ipv6.src)
        cn_id = IPv6AddressHelper.client_id(pkt_ipv6.src)
        self.logger.info("CustomerFlowPipeline: Distribution/ Client network "
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
        customer_inst = [ofp_parser.OFPInstructionGotoTable(dn_table_id)]

        dst_customer_match = ofp_parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_dst=("{}:8000::".format(subnet_prefix),
                      "ffff:ffff:ffff:ffff:8000::"))
        mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                    priority=200,
                                    table_id=table_id,
                                    match=dst_customer_match,
                                    instructions=customer_inst)
        datapath.send_msg(mod)

        src_customer_match = ofp_parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_src=("{}:8000::".format(subnet_prefix),
                      "ffff:ffff:ffff:ffff:8000::"))
        mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                    priority=200,
                                    table_id=table_id,
                                    match=src_customer_match,
                                    instructions=customer_inst)
        datapath.send_msg(mod)

        # Process other traffic from subnet at MAC learning table
        src_mac_table_id = self.__class__.SRC_MAC_TABLE
        client_net_inst = [ofp_parser.OFPInstructionGotoTable(src_mac_table_id)]

        dst_client_net_match = ofp_parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_dst=("{}::".format(subnet_prefix),
                      "ffff:ffff:ffff:ffff::"))
        mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                    priority=100,
                                    table_id=table_id,
                                    match=dst_client_net_match,
                                    instructions=client_net_inst)
        datapath.send_msg(mod)

        src_client_net_match = ofp_parser.OFPMatch(
            eth_type=0x86dd,
            ipv6_src=("{}::".format(subnet_prefix),
                      "ffff:ffff:ffff:ffff::"))
        mod = ofp_parser.OFPFlowMod(datapath=datapath,
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
            self.customer_table_allocation[dn_id] = { "table_id": table_id }
            if distribution_net:
                dn_entry = self.customer_table_allocation[dn_id]
                dn_entry["distribution_net"] = distribution_net
            self.__class__.NEXT_TABLE += 1
            self._init_customer_table(datapath, table_id)

            self.logger.info("CustomerFlowPipeline: "
                             "No table allocated for DN yet. "
                             "Allocated table {}".format(table_id))

        return self.customer_table_allocation[dn_id]["table_id"]

    def _init_customer_table(self, datapath, table_id):
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        inst = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
        mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                    table_id=table_id,
                                    priority=0,
                                    match=ofp_parser.OFPMatch(),
                                    instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("CustomerFlowPipeline: Initialized table {}. "
                         "On table-miss send to controller.".format(table_id))

    def _handle_new_customer_address(self, ev):
        msg = ev.msg
        table_id = msg.table_id
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        buffer_id = msg.buffer_id
        pkt = packet.Packet(msg.data)
        pkt_ipv6 = pkt.get_protocols(ipv6.ipv6)[0]
        idle_timeout = self.__class__.CUSTOMER_FLOW_IDLE_TIMEOUT

        src_mac_table_id = self.__class__.SRC_MAC_TABLE
        inst = [ofp_parser.OFPInstructionGotoTable(src_mac_table_id)]

        customer_ips = []
        if IPv6AddressHelper.is_customer_address(pkt_ipv6.src):
            customer_ips.append(pkt_ipv6.src)
        if IPv6AddressHelper.is_customer_address(pkt_ipv6.dst):
            customer_ips.append(pkt_ipv6.dst)
        if not customer_ips:
            raise RuntimeError("CustomerFlowPipeline: Packet does not include "
                               "customer ipv6 address.")

        for customer_ip in customer_ips:
            dst_match = ofp_parser.OFPMatch(
                eth_type=0x86dd,
                ipv6_dst=customer_ip)
            mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                        table_id=table_id,
                                        match=dst_match,
                                        idle_timeout=idle_timeout,
                                        instructions=inst,
                                        flags=ofp.OFPFF_SEND_FLOW_REM)
            datapath.send_msg(mod)

            src_match = ofp_parser.OFPMatch(
                eth_type=0x86dd,
                ipv6_src=customer_ip)
            mod = ofp_parser.OFPFlowMod(datapath=datapath,
                                        buffer_id=buffer_id,
                                        table_id=table_id,
                                        match=src_match,
                                        instructions=inst)
            datapath.send_msg(mod)

            self._notify_customer_event_flow_added(customer_ip)
            self.logger.info("CustomerFlowPipeline: "
                             "New customer: {} "
                             "added to table {}".format(pkt_ipv6,
                                                        table_id))

    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def _flow_removed_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        reason = 'unknown'
        if msg.reason == ofp.OFPRR_IDLE_TIMEOUT:
            reason = 'IDLE TIMEOUT'
        elif msg.reason == ofp.OFPRR_HARD_TIMEOUT:
            reason = 'HARD TIMEOUT'
        elif msg.reason == ofp.OFPRR_DELETE:
            reason = 'DELETE'
        elif msg.reason == ofp.OFPRR_GROUP_DELETE:
            reason = 'GROUP DELETE'

        table_id = msg.table_id
        ipv6_dst = msg.match['ipv6_dst']

        self.logger.info('CustomerFlowPipeline: '
                         'A flow was removed from table {}. '
                         'Reason: {}.'
                         .format(table_id, reason))

        if ipv6_dst:
            src_match = ofp_parser.OFPMatch(
                eth_type=0x86dd,
                ipv6_src=ipv6_dst)
            mod = ofp_parser.OFPFlowMod(command=ofp.OFPFC_DELETE,
                                        datapath=datapath,
                                        table_id=table_id,
                                        match=src_match)
            datapath.send_msg(mod)
            self.logger.info('CustomerFlowPipeline: '
                             'Match for ipv6_dst {} at table {} timed out. '
                             'Removed match for ipv6_src.'
                             .format(ipv6_dst, table_id))
        self._notify_customer_event_flow_removed(ipv6_dst)
