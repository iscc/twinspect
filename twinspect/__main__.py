# -*- coding: utf-8 -*-
import twinspect as ts
import pathlib
from loguru import logger as log
import argparse

HERE = pathlib.Path(__file__).parent.absolute()


def main():
    parser = argparse.ArgumentParser(description="TwinSpect Runner")
    parser.add_argument('args', nargs='*', help='The arguments (assumed function name + params)')
    args = parser.parse_args()
    if args.args:
        log.info(f"Arguments {args.args}")
        func = ts.load_function(args.args[0])
        # func = getattr(ts, args.args[0])
        func(*args.args[1:])
    else:
        log.info(f"Running TwinSpect v{ts.__version__}")
        log.debug("Installing algorithm dependencies")
        for alg_obj in ts.cnf.algorithms:
            ts.install_algorithm(alg_obj)

        for alg_obj in ts.cnf.algorithms:
            log.info(f"Benchmarking {alg_obj.name}")
            datasets = ts.datasets(mode=alg_obj.mode)
            for ds_obj in datasets:
                log.info(f"Benchmarking {alg_obj.name} on {ds_obj.name}")
                ts.install_dataset(ds_obj)


if __name__ == '__main__':
    main()
