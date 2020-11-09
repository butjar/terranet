import os
import inspect
import time
import shlex, subprocess
import glob
import shutil
import logging
from influxdb import InfluxDBClient
import json
import csv

from mininet.log import lg, info, warn, error
from ipmininet.clean import cleanup

class TerranetSimulator():
    def __init__(self, name, net,
                 home_dir=None,
                 clean_before=True,
                 clean_after=True,
                 log_level='info',
                 compress=True,
                 influx_config={'host': 'localhost',
                                'port': 8086,
                                'user': 'admin',
                                'password': 'admin',
                                'databases': ['customerstats',
                                              'switchstats']},
                 *args, **kwargs):
        self.name = name
        self.net = net
        if not home_dir:
            home_dir = '/var/terranet/{}'.format(self.name)
        self.home_dir = home_dir
        self.clean_before = clean_before
        self.clean_after = clean_after
        self.log_level = log_level
        self.compress = compress
        self.simulation_start = self.time_ns()
        self.simulation_end = None
        self.net_started = None
        self.net_stopped = None
        self.simulation_dir = None
        self.log_name = '{}.log'.format(
            self.__class__.__name__)
        self.simulation_dir = os.path.join(
            self.home_dir, str(self.simulation_start))
        self.logfile = os.path.join(
            self.simulation_dir, self.log_name)
        self.influx_config = influx_config
        self.archive = None

    @staticmethod
    def time_ns():
        return int(round(time.time() * 1000000000))

    def __enter__(self):
        self.setup()
        self.run()
        return self.net

    def __exit__(self, type, value, traceback):
        self.stop()
        self.teardown()
        return True

    def run(self):
        info('***** Simulation {} started at: {}\n'
             .format(self.name, self.simulation_start))
        net_name = self.net.__class__.__name__
        info('***** Starting net {}\n'.format(net_name))

        self.net.start()
        self.net_started = self.time_ns()
        info('***** {} started at {}\n'
             .format(net_name, self.net_started))

    def setup(self):
        info('***** Setup\n')
        self._setup_logfile()
        if self.clean_before:
            self.clean(caller='setup')

    def _setup_logfile(self):
        os.makedirs(self.simulation_dir, exist_ok=True)

        if self.logfile:
            lg.addHandler(logging.FileHandler(self.logfile))
            lg.setLogLevel(self.log_level)
            info('***** Logfile: {}\n'.format(self.logfile))


    def stop(self):
        net_name = self.net.__class__.__name__
        self.net_stopped = self.time_ns()
        info('***** {} stopped at: {}\n'
            .format(net_name, self.net_stopped))
        self.net.stop()
        self.simulation_end = self.time_ns()
        info('***** Simulation {} ended at: {}\n'
            .format(self.name, self.simulation_end))

    def teardown(self):
        info('***** Teardown\n')
        self._archive_topo_file()
        self._archive_logs()
        self._archive_komondor_cache()
        self._archive_influx()
        if self.compress:
            self._compress_simulation_dir()
            self._delete_simulation_dir()
        if self.clean_after:
            self.clean(caller='teardown')

    def sh(self, command,
           **kwargs):
        defaults = {'shell': True,
                    'universal_newlines': True,
                    'stdout': subprocess.PIPE,
                    'stderr': subprocess.PIPE}
        defaults.update(kwargs)
        info('\n/bin/sh# {}\n'.format(command))
        with subprocess.Popen(command, **defaults) as p:
            stdout, stderr = p.communicate()
            if stdout:
                info('/bin/sh(OUT)# {}\n'.format(stdout))
            if stderr:
                error('/bin/sh(ERR)# {}\n'.format(stderr))

    def clean(self, caller=None):
        info('***** Cleaning logs\n')
        shutil.rmtree('/var/tmp/log', ignore_errors=True)
        self._clean_influx()
        if caller == 'teardown':
            if self.archive:
                info('***** Deleting compressed simulation dir\n')
                self._delete_simulation_dir()
            info('***** (IP)mininet cleanup\n')
            cleanup()

    def _clean_influx(self):
        info('***** Cleaning influxdb\n')
        for db in self.influx_config['databases']:
            influx = InfluxDBClient(self.influx_config['host'],
                self.influx_config['port'], self.influx_config['user'],
                self.influx_config['password'], db)
            info('***** Dropping database {}\n'.format(db))
            influx.drop_database(db)
            info('***** Creating database {}\n'.format(db))
            influx.create_database(db)

    def archive_file(self, file,
                     path=None,
                     sub_dirs=None,
                     new_file_name=None):
        src = os.path.abspath(file)
        if not new_file_name:
            new_file_name = os.path.basename(file)
        if not path:
            path = self.simulation_dir
        if sub_dirs:
            path = os.path.join(path, sub_dirs)
        os.makedirs(path, exist_ok=True)
        dst = os.path.join(path, new_file_name)
        copy = shutil.copy2(src, dst)
        info('***** File {} archived to {}\n'.format(src, copy))
        return copy

    def archive_dirs(self, dir,
                     path=None,
                     sub_dirs=None,
                     new_dir_name=None):
        src = os.path.abspath(dir)
        if not new_dir_name:
            new_dir_name = os.path.basename(dir)
        if not path:
            path = self.simulation_dir
        if sub_dirs:
            path = os.path.join(path, sub_dirs)
        dst = os.path.join(path, new_dir_name)
        copy = shutil.copytree(src, dst)
        info('***** Directory tree {} archived to {}\n'.format(src, copy))

    def _archive_topo_file(self):
        topo_file = os.path.abspath(inspect.getfile(
            self.net.topo.__class__))
        info('***** Archiving topo file: {}\n'.format(topo_file))
        self.archive_file(topo_file)

    def _archive_influx(self):
        influx_archive = os.path.join(self.simulation_dir, 'influx')
        for db in self.influx_config['databases']:
            db_archive = os.path.join(influx_archive, db)
            os.makedirs(db_archive, exist_ok=True)
            influx = InfluxDBClient(self.influx_config['host'],
                self.influx_config['port'], self.influx_config['user'],
                self.influx_config['password'], db)
            measurements = [x['name'] for x in influx.get_list_measurements()]
            for m in measurements:
                info('***** Archiving measurement {} '
                     'from database: {}\n'.format(m, db))
                q = 'SELECT * FROM {measurement} ' \
                    'WHERE time > {start} ' \
                    'AND time < {end}'.format(measurement=m,
                                              start=self.net_started,
                                              end=self.net_stopped)
                rs = influx.query(q, database=db, epoch='ns')
                json_file = os.path.join(db_archive, '{}.json'.format(m))
                self._write_resultset(json_file, rs, format='json')
                dat_file = os.path.join(db_archive, '{}.dat'.format(m))
                self._write_resultset(dat_file, rs, format='csv')

    def _write_resultset(self, file, result_set, format='json'):
        if format == 'json':
            with open(file, 'w') as json_file:
                json.dump(result_set.raw, json_file, indent=4, sort_keys=True)
            return json_file
        if format == 'csv':
            with open(file, 'w', newline='') as dat_file:
                writer = csv.writer(dat_file, dialect='unix', delimiter='\t')
                # write header
                writer.writerow(result_set.raw['series'][0]['columns'])
                writer.writerows(result_set.raw['series'][0]['values'])
            return dat_file
        return None

    def _archive_logs(self):
        info('***** Archiving logs\n')
        log_archive = os.path.join(self.simulation_dir, 'log')
        os.makedirs(log_archive, exist_ok=True)
        self.archive_dirs('/var/tmp/log/', sub_dirs='log/openr')
        log_files = [*glob.glob('/tmp/*.log'),
                     *glob.glob('/var/log/iperf_*.log')]
        for log in log_files:
            self.archive_file(log, sub_dirs='log')

    def _archive_openr_configs(self):
        info('***** Archiving OpenR config files\n')
        for conf in glob.glob('/tmp/openr_*.cfg'):
            self.archive_file(conf, sub_dirs='conf/openr')

    def _archive_komondor_cache(self):
        info('***** Archiving komondor cache\n')
        cache_dir = os.path.join(self.net.topo.komondor_config_dir())
        self.archive_dirs(os.path.join(cache_dir, 'input'),
                          sub_dirs='komondor/input')
        self.archive_dirs(os.path.join(cache_dir, 'output'),
                          sub_dirs='komondor/output')

    def _compress_simulation_dir(self):
        info('***** Compressing simulation directory\n')
        root_dir = os.path.dirname(self.simulation_dir)
        base_dir = os.path.basename(self.simulation_dir)
        archive_name = os.path.join(root_dir, base_dir)
        self.archive = shutil.make_archive(archive_name,
                                           format='gztar',
                                           root_dir=root_dir,
                                           base_dir=base_dir)

    def _delete_simulation_dir(self):
        shutil.rmtree(self.simulation_dir)
