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


def test_benchmark_files_treat_zarr_directories_as_single_media_inputs(tmp_path):
    cluster = tmp_path / "0000000"
    cluster.mkdir()
    original = cluster / "0original.czi"
    original.write_bytes(b"czi")

    zarr = cluster / "1variant_ome.zarr"
    nested = zarr / "0" / "0" / "0"
    nested.mkdir(parents=True)
    (zarr / ".zattrs").write_text("{}", encoding="utf-8")
    (nested / "0").write_bytes(b"chunk")

    plain_dir = cluster / "sidecar"
    plain_dir.mkdir()
    sidecar_file = plain_dir / "metadata.txt"
    sidecar_file.write_text("metadata", encoding="utf-8")

    assert benchmark_files(tmp_path) == [original, zarr, sidecar_file]
