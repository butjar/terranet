import os
from mininet.node import Controller

from .ryu import app

class RyuManager(Controller):
    def __init__(self, name,
                 modules=['terranet.ryu.app.mac_learning_pipeline'],
                 **kwargs):
        self.modules = modules
        command = 'ryu-manager'
        cargs = '--ofp-tcp-listen-port %s {}' \
                .format(' '.join(self.modules))
        cdir = os.path.dirname(app.__file__)
        kwargs.update({'command': command,
                       'cargs': cargs,
                       'cdir': cdir})
        super().__init__(name, **kwargs)
