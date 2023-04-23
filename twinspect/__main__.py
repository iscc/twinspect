# -*- coding: utf-8 -*-
import twinspect as ts
import pathlib
import yaml

HERE = pathlib.Path(__file__).parent.absolute()


def main():
    config = yaml.safe_load(open(HERE.parent / "config.yml"))
    root_folder = pathlib.Path(config['root_folder'])
    for dataset in config['datasets']:
        ds_obj = ts.Dataset.parse_obj(dataset)
        ts.install_dataset(ds_obj, root_folder)


if __name__ == '__main__':
    main()
