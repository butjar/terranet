from influxdb import InfluxDBClient


class SwitchstatsContinuousQueries:

    DATABASE = 'switchstats'
    USERNAME = 'admin'
    PASSWORD = 'admin'
    DEFAULT_INTERVAL = 10
    CONTINUOUS_QUERIES = ['dl_throughputs',
                          'ul_throughputs',
                          'sum_dl_throughputs',
                          'sum_ul_throughputs']

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
        cqs.append(cls.create_dlthroughputs_cq(influx, interval=interval,
                                               database=database))
        cqs.append(cls.create_ulthroughputs_cq(influx, interval=interval,
                                               database=database))
        cqs.append(cls.create_sum_dlthroughputs_cq(influx, interval=interval,
                                                   database=database))
        cqs.append(cls.create_sum_ulthroughputs_cq(influx, interval=interval,
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
    def create_dlthroughputs_cq(cls, client,
                                cq_name='dl_throughputs',
                                interval=DEFAULT_INTERVAL,
                                database=DATABASE):
        select = (
            'SELECT non_negative_derivative(max("value"), 1s) * 8 '
            'AS "value" '
            'INTO "dl_throughputs" '
            'FROM "byte_count_dl" '
            'WHERE time > now() - {interval}s '
            'GROUP BY time({interval}s), "host"'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)

    @classmethod
    def create_ulthroughputs_cq(cls, client,
                                cq_name='ul_throughputs',
                                interval=DEFAULT_INTERVAL,
                                database=DATABASE):
        select = (
            'SELECT non_negative_derivative(max("value"), 1s) * 8 '
            'AS "value" '
            'INTO "ul_throughputs" '
            'FROM "byte_count_ul" '
            'WHERE time > now() - {interval}s '
            'GROUP BY time({interval}s), "host"'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)

    @classmethod
    def create_sum_dlthroughputs_cq(cls, client,
                                    cq_name='sum_dl_throughputs',
                                    interval=DEFAULT_INTERVAL,
                                    database=DATABASE):
        select = (
            'SELECT sum("value") '
            'AS "value" '
            'INTO "sum_dl_throughputs" '
            'FROM "dl_throughputs" '
            'GROUP BY time({interval}s)'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)

    @classmethod
    def create_sum_ulthroughputs_cq(cls, client,
                                    cq_name='sum_ul_throughputs',
                                    interval=DEFAULT_INTERVAL,
                                    database=DATABASE):
        select = (
            'SELECT sum("value") '
            'AS "value" '
            'INTO "sum_ul_throughputs" '
            'FROM "ul_throughputs" '
            'GROUP BY time({interval}s)'
        ).format(interval=interval)
        return client.create_continuous_query(cq_name, select,
                                              database=database)
