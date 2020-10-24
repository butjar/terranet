from influxdb import InfluxDBClient

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.controller import dpset


class CustomerStatsMonitor(app_manager.RyuApp):
    '''
    https://osrg.github.io/ryu-book/en/html/traffic_monitor.html
    '''

    INTERVAL = 5
    INFLUX_DATABASE = 'switchstats'
    INFLUX_USERNAME = 'admin'
    INFLUX_PASSWORD = 'admin'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.datapaths = {}
        self.table_ids = []
        self.influx = InfluxDBClient(username=self.__class__.INFLUX_USERNAME,
                                     password=self.__class__.INFLUX_PASSWORD,
                                     database=self.__class__.INFLUX_DATABASE)
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info('CustomerStatsMonitor: Register '
                                 'datapath {}.'.format(datapath.id))
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info('CustomerStatsMonitor: Unregister '
                                 'datapath {}.'.format(datapath.id))
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_table_stats(dp)
                self._request_customer_stats(dp)
            hub.sleep(self.__class__.INTERVAL)

    def _request_table_stats(self, datapath):
        self.logger.debug('CustomerStatsMonitor: Sending TableStatsRequest to '
                          'datapath {}.'.format(datapath.id))
        ofp_parser = datapath.ofproto_parser

        req = ofp_parser.OFPTableStatsRequest(datapath, 0)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPTableStatsReply, MAIN_DISPATCHER)
    def _table_stats_reply_handler(self, ev):
        self.logger.debug('CustomerStatsMonitor: TableStatsReply received.')
        for stat in ev.msg.body:
            table_id = stat.table_id
            if (not self._is_customer_table(table_id) or
                not stat.active_count):
                continue
            if not table_id in self.table_ids:
                self.table_ids.append(table_id)
                self.logger.info('CustomerStatsMonitor: Added id {} to table_ids.'
                                  .format(table_id))

    def _is_customer_table(self, table_id):
        return (table_id > 3 and
                table_id < 100)

    def _request_customer_stats(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for table_id in self.table_ids:
            req = parser.OFPFlowStatsRequest(datapath, table_id=table_id)
            datapath.send_msg(req)
            self.logger.debug('CustomerStatsMonitor: '
                              'FlowStatsRequest send for table_id {} '
                              'to datapath {}.'
                              .format(table_id, datapath.id))

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        self.logger.debug('CustomerStatsMonitor: FlowStatsReply received.')
        body = ev.msg.body

        for stat in [flow for flow in body if flow.priority > 1]:
            self.logger.debug('CustomerStatsMonitor: Received stats: '
                              'table_id {}, '
                              'match {}, '
                              'packet_count {}, '
                              'byte_count {}.'.format(stat.table_id,
                                                      stat.match,
                                                      stat.packet_count,
                                                      stat.byte_count))

            if stat.match.get('ipv6_src'):
                ipv6 = stat.match['ipv6_src']
                measurements = ('packet_count_ul', 'byte_count_ul')

            if stat.match.get('ipv6_dst'):
                ipv6 = stat.match['ipv6_dst']
                measurements = ('packet_count_dl', 'byte_count_dl')

            if measurements:
                datapoints = [
                    {
                        'measurement': measurements[0],
                        'tags': {
                            'host': ipv6
                        },
                        'fields': {
                            'value': stat.packet_count
                        }
                    },
                    {
                        'measurement': measurements[1],
                        'tags': {
                            'host': ipv6
                        },
                        'fields': {
                            'value': stat.byte_count
                        }
                    }
                ]

                self.influx.write_points(datapoints)
