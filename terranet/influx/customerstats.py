from influxdb import InfluxDBClient


class CustomerstatsContinuousQueries:

    DATABASE = 'customerstats'
    USERNAME = 'admin'
    PASSWORD = 'admin'
    DEFAULT_INTERVAL = 10
    CONTINUOUS_QUERIES = ['rx_throughputs',
                          'sum_rx_throughputs',
                          'janes_customer_count',
                          'janes_pow2_sum_throughputs',
                          'janes_sum_pow2_throughputs',
                          'janes_fairness_index']

    @classmethod
    def create_cqs(cls,
                   username=USERNAME,
                   password=PASSWORD,
                   database=DATABASE,
                   interval=DEFAULT_INTERVAL):
        influx = InfluxDBClient(username=username,
                                password=password,
                                database=database)

        cqs = []
        cqs.append(cls.create_rxthroughputs_cq(influx, interval=interval,
                                               database=database))
        cqs.append(cls.create_customer_count_cq(influx, interval=interval,
                                                database=database))
        cqs.append(cls.create_sum_rxthroughputs_cq(influx, interval=interval,
                                                   database=database))
        cqs.append(cls.create_pow2_sum_throughputs_cq(influx,
                                                      interval=interval,
                                                      database=database))
        cqs.append(cls.create_sum_pow2_throughputs_cq(influx,
                                                      interval=interval,
                                                      database=database))
        cqs.append(cls.create_fairness_index_cq(influx, interval=interval,
                                                database=database))
        return cqs

    @classmethod
    def drop_cqs(cls,
                 username=USERNAME,
                 password=PASSWORD,
                 database=DATABASE,
                 interval=DEFAULT_INTERVAL,
                 cqs=CONTINUOUS_QUERIES):
        influx = InfluxDBClient(username=username,
                                password=password,
                                database=database)
        return [ influx.drop_continuous_query(cq, database=database) \
                 for cq in cqs ]

    @classmethod
    def create_rxthroughputs_cq(cls, client,
                                cq_name='rx_throughputs',
                                interval=DEFAULT_INTERVAL,
                                database=DATABASE):
        select = (
            'SELECT non_negative_derivative(max("value"), 1s) * 8 '
            'AS "value" '
            'INTO "rx_throughputs" '
            'FROM "rx_bytes_value" '
            'WHERE time > now() - {interval}s '
            'GROUP BY time({interval}s), "host"'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)

    @classmethod
    def create_sum_rxthroughputs_cq(cls, client,
                                    cq_name='sum_rx_throughputs',
                                    interval=DEFAULT_INTERVAL,
                                    database=DATABASE):
        select = (
            'SELECT sum("value") '
            'AS "value" '
            'INTO "sum_rx_throughputs" '
            'FROM "rx_throughputs" '
            'GROUP BY time({interval}s)'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)

    @classmethod
    def create_customer_count_cq(cls, client,
                                 cq_name='janes_customer_count',
                                 interval=DEFAULT_INTERVAL,
                                 database=DATABASE):
        select = (
            'SELECT count("last") '
            'AS "customer_count" '
            'INTO "janes_fairness_index" '
            'FROM (SELECT last("value")'
                  'FROM "rx_throughputs"'
                  'GROUP BY "host") '
            'GROUP BY time({interval}s)'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)

    @classmethod
    def create_pow2_sum_throughputs_cq(cls, client,
                                       cq_name='janes_pow2_sum_throughputs',
                                       interval=DEFAULT_INTERVAL,
                                       database=DATABASE):
        select = (
            'SELECT pow(last("value"), 2) '
            'AS "pow2_sum_throughputs" '
            'INTO "janes_fairness_index" '
            'FROM "sum_rx_throughputs" '
            'GROUP BY time({interval}s)'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)

    @classmethod
    def create_sum_pow2_throughputs_cq(cls, client,
                                          cq_name='janes_sum_pow2_throughputs',
                                          interval=DEFAULT_INTERVAL,
                                          database=DATABASE):
        select = (
            'SELECT sum(pow2_throughputs) '
            'AS "sum_pow2_throughputs" '
            'INTO "janes_fairness_index" '
            'FROM (SELECT pow(last("value"), 2)'
                  'AS "pow2_throughputs"'
                  'FROM "rx_throughputs"'
                  'GROUP BY "host") '
            'GROUP BY time({interval}s)'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)

    @classmethod
    def create_fairness_index_cq(cls, client,
                                 cq_name='janes_fairness_index',
                                 interval=DEFAULT_INTERVAL,
                                 database=DATABASE):
        select = (
            'SELECT last("index") '
            'AS "value" '
            'INTO "janes_fairness_index" '
            'FROM (SELECT "pow2_sum_throughputs"'
                          '/ "customer_count"'
                          '/ "sum_pow2_throughputs"'
                          'AS "index"'
                          'FROM "janes_fairness_index") '
            'GROUP BY time({interval}s)'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)
