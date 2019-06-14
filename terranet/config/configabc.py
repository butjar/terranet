from abc import ABCMeta, abstractproperty

import sys

class ConfigABC(metaclass=ABCMeta):

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
                      "attribute {}.".format(cfg_obj, key),
                      file=sys.stderr)

        return cfg_obj


