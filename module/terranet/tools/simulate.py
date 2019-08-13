import logging
import os
import multiprocessing
import progress.bar
import functools
import time

from ..komondor import Komondor

def init(q):
    global queue
    queue = q


def simulate(args):
    log = logging.getLogger(__name__)
    if not os.path.isdir(args.cfg_dir):
        log.error("--cfg_dir must be a valid directory.")
        return -1

    if not os.path.isdir(args.out_dir):
        log.error("--out_dir must be a valid directory.")
        return -1

    dirs = {"cfg": args.cfg_dir, "out": args.out_dir}
    komondor_args = {"time": args.time, "seed": args.seed}

    cfg_files = list(filter(
        lambda x: x.endswith(".cfg"),
        os.listdir(dirs["cfg"])
    ))

    log.info('Found {} configurations to simulate.'.format(len(cfg_files)))
    q = multiprocessing.Queue()
    bar = progress.bar.Bar('Simulating combinations', max=len(cfg_files))
    pool = multiprocessing.Pool(args.processes, initializer=init, initargs=(q,))
    f = functools.partial(komondor_worker, dirs=dirs, komondor=args.komondor,
                          komondor_args=komondor_args)
    t1 = time.time()
    async_res = pool.map_async(f, cfg_files)

    while not async_res.ready():
        try:
            q.get(timeout=5.0)
            bar.next()
        except Exception as e:
            # Race condition
            # async might not be ready yet
            # but queue is already empty
            pass

    while not q.empty():
        try:
            q.get(False)
            bar.next()
        except:
            log.debug('Timeout while waiting.')

    try:
        async_res.get()  # Get result to trigger possible exceptions
    except RuntimeError as e:
        print(e)

    t2 = time.time()
    pool.close()
    bar.finish()
    log.info('Completed {} simulations in {} seconds.'.format(len(cfg_files), t2 - t1))


def komondor_worker(cfg, dirs, komondor=None, komondor_args=None):
    global queue
    cfg_file = os.path.abspath(os.path.join(dirs["cfg"], cfg))
    result_file = os.path.abspath(os.path.join(dirs["out"], cfg))
    args = komondor_args.copy()
    args["stats"] = result_file
    k = Komondor(executable=komondor)

    (proc, stdout, stderr) = k.run(cfg_file, **args)
    queue.put(stderr + stdout)

    return stderr