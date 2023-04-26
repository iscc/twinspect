# -*- coding: utf-8 -*-
import twinspect as ts
import pathlib
from loguru import logger as log

HERE = pathlib.Path(__file__).parent.absolute()


def main():
    log.info(f"Running TwinSpect v{ts.__version__}")
    log.debug("Installing Algorithms")
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
