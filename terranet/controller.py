import os
from mininet.node import Controller

from .ryu import app


class RyuManager(Controller):
    def __init__(self, name,
                 *ryuArgs,
                 modules=['terranet.ryu.app.mac_learning_pipeline'],
                 **kwargs):
        self.modules = modules
        command = 'ryu-manager'
        ryuArgs = ' '.join(ryuArgs)
        cargs = '--ofp-tcp-listen-port %s {ryuArgs} {modules}' \
                .format(ryuArgs=ryuArgs,
                        modules=' '.join(self.modules))
        cdir = os.path.dirname(app.__file__)
        kwargs.update({'command': command,
                       'cargs': cargs,
                       'cdir': cdir})
        super().__init__(name, **kwargs)
