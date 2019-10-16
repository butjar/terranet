import sys
import os
import subprocess
from whichcraft import which


def run_komondor_worker(cfg_file,
                        output_dir=None,
                        komondor_executable=None,
                        komondor_args={}):
    file_name = os.path.basename(cfg_file)
    result_file = os.path.join(output_dir, file_name)
    args = komondor_args.copy()
    args["stats"] = result_file
    k = Komondor(executable=komondor_executable)
    (proc, stdout, stderr) = k.run(cfg_file, **args)
    return stderr


class Komondor(object):
    """Wrapper for Komondor simulator"""
    def __init__(self, executable=None):
        if not executable:
            executable = which('komondor_main')
        self.executable = executable

        if not (self.executable and os.path.isfile(self.executable)):
            raise ValueError("Komondor executable {} not found."
                             .format(executable))

    def run(self, cfg, time=100, seed=1000, stats=None, **kwargs):
        defaults = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE
        }
        defaults.update(kwargs)
        kwargs = defaults

        if not os.path.isfile(cfg):
            raise ValueError("Parameter cfg must be a valid file path.")

        if not (stats):
            stats = "{0}_{2}{1}"\
                    .format(*os.path.splitext(cfg) + ("_result",))

        args = ["--time", str(time),
                "--seed", str(seed),
                "--stats", stats,
                cfg]
        cmd = [self.executable] + args

        proc = subprocess.Popen(cmd, **kwargs)
        (stdout, stderr) = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("""Komondor exited with error code {}: \n
                                  stdout: {}\n
                                  stderr: {}\n"""
                               .format(proc.returncode, stdout, stderr))
        return (proc, stdout, stderr)
