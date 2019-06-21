#!/usr/bin/env python

from __future__ import print_function

import sys
import os
import argparse
import multiprocessing, logging
from functools import partial

from terranet.komondor import Komondor

def run_komondor_worker(cfg,
                        dirs=[],
                        komondor=None,
                        komondor_args={}):
    cfg_file = os.path.abspath(os.path.join(dirs["cfg"], cfg))
    result_file = os.path.abspath(os.path.join(dirs["out"], cfg))
    args = komondor_args.copy()
    args["stats"] = result_file
    k = Komondor(executable=komondor)

    (proc, stdout, stderr) = k.run(cfg_file, **args)
    return stderr

def run_komondor_simulations(dirs,
                             processes,
                             komondor,
                             komondor_args):
    cfg_files = list(filter(
        lambda x: x.endswith(".cfg"),
        os.listdir(dirs["cfg"])
    ))
    
    pool = multiprocessing.Pool(processes)
    f = partial(run_komondor_worker, dirs=dirs, komondor=komondor,
                komondor_args=komondor_args)
    pool.map(f, cfg_files)


if __name__ == '__main__':
    current_dir = os.getcwd()

    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg_dir', 
                        nargs='?', 
                        default="{}/cfg".format(current_dir), 
                        type=str,
                        help='')
    parser.add_argument('--out_dir', 
                        nargs='?',
                        default="{}/out".format(current_dir),
                        type=str,
                        help='')
    parser.add_argument('--time',
                        nargs='?',
                        default=100,
                        type=int, 
                        help="")
    parser.add_argument('--seed', 
                        nargs='?',
                        default=1000,
                        type=int,
                        help='')
    parser.add_argument('--processes', 
                        nargs='?',
                        default=None,
                        type=int,
                        help='')
    parser.add_argument('--komondor', 
                        nargs='?',
                        type=str,
                        help='')

    args = parser.parse_args()
    if not os.path.isdir(args.cfg_dir):
        raise ValueError("--cfg_dir must be a valid directory.")
    if not os.path.isdir(args.out_dir):
        raise ValueError("--out_dir must be a valid directory.")

    dirs = {"cfg": args.cfg_dir, "out": args.out_dir}
    komondor_args = {"time": args.time, "seed": args.seed}
    run_komondor_simulations(dirs,
                             args.processes,
                             args.komondor,
                             komondor_args)
