import functools

from influxdb import InfluxDBClient

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

from .customer_flow_pipeline import EventCustomerFlowAdded, \
    EventCustomerFlowRemoved
from .ipv6_address_helper import IPv6AddressHelper

class CustomerAllocationMonitor(app_manager.RyuApp):

    INTERVAL = 10
    INFLUX_DATABASE = 'switchstats'
    INFLUX_USERNAME = 'admin'
    INFLUX_PASSWORD = 'admin'

    def __init__(self, *args, **kwars):
        super().__init__(*args, **kwars)

        self.customer_allocation = {}
        self.influx = InfluxDBClient(username=self.__class__.INFLUX_USERNAME,
                                     password=self.__class__.INFLUX_PASSWORD,
                                     database=self.__class__.INFLUX_DATABASE)
        self.monitor_thread = hub.spawn(self._monitor)

    def customers(self):
        return functools.reduce(lambda x, y: [*x, *y['customers']],
                                self.customer_allocation.values(),
                                [])

    def customer_count(self):
        return len(self.customers())

    def dn_customers(self, dn_id):
        return self.customer_allocation[dn_id]['customers']

    def dn_customer_count(self, dn_id):
        return len(self.dn_customers(dn_id))

    def _monitor(self):
        while True:
            self._influx_write_total_customer_count()
            self._influx_write_dn_customer_counts()
            hub.sleep(self.__class__.INTERVAL)

    def _influx_write_total_customer_count(self):
        datapoints = [
                {
                    'measurement': 'total_customer_count',
                    'fields': {
                           'value': self.customer_count()
                    }
                }
        ]
        self.influx.write_points(datapoints)
        return datapoints

    def _influx_write_dn_customer_counts(self):
        datapoints = []

        for dn_id in self.customer_allocation.keys():
            datapoint = {
                'measurement': 'customer_counts',
                'tags': {
                    'DN': dn_id
                },
                'fields': {
                    'value': self.dn_customer_count(dn_id)
                }
            }
            datapoints.append(datapoint)

        self.influx.write_points(datapoints)
        return datapoints

    @set_ev_cls(EventCustomerFlowAdded)
    def _customer_flow_added_handler(self, ev):
        self.logger.debug('CustomerAllocationMonitor: Received event '
                          '{}.'.format(ev.__class__.__name__))
        ipv6 = ev.customer_ipv6
        dn_id = IPv6AddressHelper.distribution_id(ipv6)
        if not self.customer_allocation.get(dn_id):
            self.customer_allocation[dn_id] = {'customers': []}
        self.customer_allocation[dn_id]['customers'].append(ipv6)
        self.logger.info('CustomerAllocationMonitor: Allocation between '
                         'customer {} and DN {} added.'.format(ipv6, dn_id))
        return self.customer_allocation

    @set_ev_cls(EventCustomerFlowRemoved)
    def _customer_flow_removed_handler(self, ev):
        self.logger.debug('CustomerAllocationMonitor: Received event '
                          '{}.'.format(ev.__class__.__name__))
        ipv6 = ev.customer_ipv6
        dn_id = IPv6AddressHelper.distribution_id(ipv6)
        self.customer_allocation[dn_id]['customers'].remove(ipv6)
        self.logger.info('CustomerAllocationMonitor: Allocation between '
                         'customer {} and DN {} removed.'.format(ipv6, dn_id))
        return self.customer_allocation
