#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import argparse

from jinja2 import Environment, PackageLoader

from terranet.config import Config

def render_template(*args,**kwargs):
    env = Environment(
        loader=PackageLoader('terranet', 'templates'),
    )
    template = env.get_template('terragraph.py.j2')
    print(template.render(*args, **kwargs))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', help='topology for komondor simulation')
    parser.add_argument('--out', help='result file from komondor simulation')

    args = parser.parse_args()
    if not (args.cfg and os.path.isfile(args.cfg)):
        sys.exit("Topology file required")

    cfg = [args.cfg]
    if args.out and os.path.isfile(args.out):
        cfg.append(args.out)
    config = Config.from_file(cfg)
    config.build()
    render_template(config=config)
