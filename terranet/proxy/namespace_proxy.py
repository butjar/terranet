import os
import proxy
from multiprocessing import Process
import shlex, subprocess

class NamespaceProxy:
    def __init__(self, nspid, port,
                 num_workers=1,
                 hostname='::',
                 *args, **kwargs):
        self.nspid = nspid
        self.port = port
        self.num_workers = num_workers
        self.hostname = hostname
        self.process = None

    def start_proxy_process(self):
        args = (self.nspid, self.port,)
        kwargs = {'num_workers': self.num_workers,
                  'hostname': self.hostname}
        env = os.environ.copy()
        env['NSPID'] = str(self.nspid)
        cmd = 'proxy' \
              ' --num-workers {workers}' \
              ' --hostname {host}' \
              ' --port {port}' \
              ' --plugins terranet.proxy.NamespaceProxyPlugin' \
              ' --enable-web-server'.format(workers=self.num_workers,
                                            host=self.hostname,
                                            port=self.port)
        args = shlex.split(cmd)
        p = subprocess.Popen(args, env=env, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
        self.process = p
        return p
