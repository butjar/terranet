#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import argparse

from jinja2 import Environment, PackageLoader

from terranet.config import KomondorConfig


def render_template(*args,**kwargs):
    env = Environment(
        loader=PackageLoader('terranet', 'templates'),
    )
    template = env.get_template('terragraph.py.j2')
    print(template.render(*args, **kwargs))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', help='topology for komondor simulation')

    args = parser.parse_args()
    if not (args.cfg and os.path.isfile(args.cfg)):
        sys.exit("Topology file required")

    cfg_file = args.cfg
    komondor_config = KomondorConfig(cfg_file=cfg_file)
    render_template(komondor_config=komondor_config)
