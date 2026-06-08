import twinspect as ts


def test_bioimage_dataset_algorithm_and_benchmark_are_configured():
    dataset = ts.Dataset.from_label("bioimage_convert_1000")
    assert dataset is not None
    assert dataset.samples == 1000
    assert dataset.clusters == 1000
    assert dataset.installer == "twinspect.datasets.bioimage_convert:install"

    algorithm = next(algo for algo in ts.cnf.algorithms if algo.label == "bioimage_data_code_iw_64")
    assert algorithm.function == "twinspect.algos.iscc_bio:bioimage_data_code_iw_64"
    assert algorithm.mode.value == "image"

    benchmark = next(
        bench
        for bench in ts.cnf.benchmarks
        if bench.algorithm_label == "bioimage_data_code_iw_64"
        and bench.dataset_label == "bioimage_convert_1000"
    )
    assert benchmark.active is True
    assert "effectiveness" in benchmark.metric_labels
