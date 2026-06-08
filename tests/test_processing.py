from twinspect.algos.processing import benchmark_files


def test_benchmark_files_skip_metadata_files(tmp_path):
    cluster = tmp_path / "0000000"
    cluster.mkdir()
    image = cluster / "0original.tif"
    image.write_bytes(b"image")
    top_level_underscore_asset = tmp_path / "_legitimate_asset.tif"
    top_level_underscore_asset.write_bytes(b"image")
    (tmp_path / "_bioimage_convert_build.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".cache.json").write_text("{}", encoding="utf-8")

    assert benchmark_files(tmp_path) == [image, top_level_underscore_asset]
