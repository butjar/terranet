from __future__ import print_function
from abc import ABCMeta, abstractproperty
from future.utils import with_metaclass

import sys

class ConfigABC(with_metaclass(ABCMeta)):

    def getName(self):
        return self._name

    def setName(self, name):
        self._name = name

    name = abstractproperty(getName, setName)

    @classmethod
    def from_config(cls, name, cfg):
        cfg_obj = cls(name=name)
        for key in cfg:
            val = cfg[key]
            try:
                setattr(cfg_obj, key, val)
            except AttributeError as err:
                print("Error while setting attributes: Object {} has no" \
                      "attribute {}."
                      .format(cfg_obj, key), file=sys.stderr)

        return cfg_obj
