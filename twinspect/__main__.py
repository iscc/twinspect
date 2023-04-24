# -*- coding: utf-8 -*-
import twinspect as ts
import pathlib


HERE = pathlib.Path(__file__).parent.absolute()


def main():
    for ds_obj in ts.cnf.datasets:
        ts.install_dataset(ds_obj)


if __name__ == '__main__':
    main()
