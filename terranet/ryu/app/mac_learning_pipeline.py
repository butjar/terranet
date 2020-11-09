from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv6


class MacLearningPipeline(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    SRC_MAC_TABLE = 0
    DST_MAC_TABLE = 1

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self._init_src_mac_table(datapath)
        self._init_dst_mac_table(datapath)

    def _init_src_mac_table(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        table_id = self.__class__.SRC_MAC_TABLE
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=table_id,
                                priority=0,
                                match=parser.OFPMatch(),
                                instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("MacLearningPipeline: Initialized src MAC table {}. "
                         "On table-miss send to controller.".format(table_id))

    def _init_dst_mac_table(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        table_id = self.__class__.DST_MAC_TABLE
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD, 0)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=table_id,
                                priority=0,
                                match=parser.OFPMatch(),
                                instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("MacLearningPipeline: Initialized dst MAC table {}. "
                         "On table-miss flood.".format(table_id))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        in_port = msg.match['in_port']
        table_id = msg.table_id
        self.logger.info("MacLearningPipeline: Packet in at port {} "
                         "from table {}.".format(in_port,
                                                 table_id))

        if table_id == self.__class__.SRC_MAC_TABLE:
            self._handle_new_src_mac(ev)

    def _handle_new_src_mac(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        buffer_id = msg.buffer_id
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        self.logger.info("MacLearningPipeline: New src MAC {} "
                         "at port {}.".format(eth.src,
                                              in_port))

        self._add_flow_mod_mac_dst(datapath, eth.src, in_port)
        self._add_flow_mod_mac_src(datapath, eth.src, in_port, buffer_id)

    def _add_flow_mod_mac_dst(self, datapath, eth_dst, out_port):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        table_id = self.__class__.DST_MAC_TABLE
        match = parser.OFPMatch(eth_dst=eth_dst)
        actions = [parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=table_id,
                                match=match,
                                instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("MacLearningPipeline: "
                         "Sending packets with dst MAC {} "
                         "out at port {}. "
                         "Flow mod added to table {}.".format(eth_dst,
                                                              out_port,
                                                              table_id))

    def _add_flow_mod_mac_src(self, datapath, eth_src, in_port, buffer_id):
        parser = datapath.ofproto_parser
        table_id = self.__class__.SRC_MAC_TABLE
        match = parser.OFPMatch(in_port=in_port,
                                eth_src=eth_src)
        dst_table_id = self.__class__.DST_MAC_TABLE
        inst = [parser.OFPInstructionGotoTable(dst_table_id)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=table_id,
                                buffer_id=buffer_id,
                                match=match,
                                instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("MacLearningPipeline: Process packets from port {} "
                         "with src MAC {} "
                         "at table {}. "
                         "Flow mod added to table {}.".format(in_port,
                                                              eth_src,
                                                              dst_table_id,
                                                              table_id))
