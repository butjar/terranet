#!/usr/bin/python3

import os
import sys
import argparse

from jinja2 import Environment, PackageLoader

from terranet.config.config import Config

def render_template(*args,**kwargs):
    env = Environment(
        loader=PackageLoader('terranet', 'templates'),
    )
    template = env.get_template('terragraph.py.j2')
    print(template.render(*args, **kwargs))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--topo', help='topology for komondor simulation')
    parser.add_argument('--cfg', help='result file from komondor simulation')

    args = parser.parse_args()
    if not (args.topo and os.path.isfile(args.topo)):
        sys.exit("Topology file required")

    config = Config.from_file(args.topo)
    config.build()
    render_template(config=config)
