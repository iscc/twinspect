from pathlib import Path
from zipfile import ZipInfo

import pytest

from twinspect.datasets import bioimage_convert as bic
from twinspect.metrics.eff import load_simprints


def zinfo(name, size=100):
    info = ZipInfo(name)
    info.file_size = size
    return info


def test_is_eligible_member_filters_non_images_empty_and_oversized():
    assert bic.is_eligible_member(zinfo("a/plate.tif", 42), max_file_size=100)
    assert bic.is_eligible_member(zinfo("a/plate.BMP", 42), max_file_size=100)
    assert not bic.is_eligible_member(zinfo("a/readme.txt", 42), max_file_size=100)
    assert not bic.is_eligible_member(zinfo("a/empty.tif", 0), max_file_size=100)
    assert not bic.is_eligible_member(zinfo("a/huge.tif", 101), max_file_size=100)


def test_select_samples_is_reproducible_and_size_capped(monkeypatch):
    calls = []

    def fake_archive_image_infos(url, max_file_size):
        calls.append((url, max_file_size))
        return [zinfo(f"{Path(url).stem}-{idx}.tif", idx + 1) for idx in range(5)]

    sources = (
        {"label": "a", "url": "https://example.test/a.zip"},
        {"label": "b", "url": "https://example.test/b.zip"},
    )
    monkeypatch.setattr(bic, "archive_image_infos", fake_archive_image_infos)

    first = bic.select_samples(samples=6, seed=7, max_file_size=123, sources=sources)
    second = bic.select_samples(samples=6, seed=7, max_file_size=123, sources=sources)

    assert first == second
    assert len(first) == 6
    assert calls[0][1] == 123
    assert {sample.source_label for sample in first} <= {"a", "b"}


def test_select_samples_fails_when_not_enough_candidates(monkeypatch):
    monkeypatch.setattr(bic, "archive_image_infos", lambda url, max_file_size: [zinfo("one.tif")])
    with pytest.raises(RuntimeError, match="need 2"):
        bic.select_samples(
            samples=2, sources=({"label": "a", "url": "https://example.test/a.zip"},)
        )


def test_manifest_roundtrip(tmp_path):
    samples = [
        bic.BioimageSample(
            source_label="bbbc-test",
            archive_url="https://example.test/archive.zip",
            member_name="folder/source.TIF",
            file_size=10,
        )
    ]
    manifest = tmp_path / "manifest.csv"
    bic.write_manifest(samples, manifest)

    assert bic.load_manifest(manifest) == samples


def test_build_cluster_keeps_original_first_and_conversion_labels(monkeypatch, tmp_path):
    sample = bic.BioimageSample(
        source_label="bbbc-test",
        archive_url="https://example.test/archive.zip",
        member_name="folder/source.TIF",
        file_size=10,
    )

    def fake_extract_member(sample, output_path):
        output_path.write_bytes(b"original")
        return output_path

    def fake_convert_file(input_path, output_path, format_name):
        output_path.write_bytes(format_name.encode("utf-8"))
        return output_path

    monkeypatch.setattr(bic, "extract_member", fake_extract_member)
    monkeypatch.setattr(bic, "convert_file", fake_convert_file)

    cluster = tmp_path / "0000000"
    bic.build_cluster(sample, cluster)

    names = sorted(path.name for path in cluster.iterdir())
    assert names == [
        "0original.TIF",
        "1variant_ome-tiff.ome.tiff",
        "2variant_tiff.tiff",
        "3variant_png.png",
    ]
    bic.validate_cluster(cluster)


def test_bioimage_convert_command_allows_template(monkeypatch):
    monkeypatch.setenv(
        "TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE",
        "converter --input {input} --output {output} --format {format}",
    )
    command = bic.bioimage_convert_command(Path("in.tif"), Path("out.png"), "png")
    assert command == ["converter", "--input", "in.tif", "--output", "out.png", "--format", "png"]


def test_validate_file_size_rejects_empty_and_oversized(tmp_path):
    empty = tmp_path / "empty.tif"
    empty.write_bytes(b"")
    with pytest.raises(RuntimeError, match="Empty"):
        bic.validate_file_size(empty)

    oversized = tmp_path / "oversized.tif"
    oversized.write_bytes(b"abc")
    with pytest.raises(RuntimeError, match="exceeds"):
        bic.validate_file_size(oversized, max_file_size=2)


def test_cluster_layout_matches_twinspect_ground_truth_parser(tmp_path):
    simprint = tmp_path / "simprint.csv"
    simprint.write_text(
        "id;code;file;size;time\n"
        "0;0000000000000000;0000000/0original.TIF;1;1\n"
        "1;0000000000000000;0000000/1variant_ome-tiff.ome.tiff;1;1\n"
        "2;ffffffffffffffff;distractor.TIF;1;1\n",
        encoding="utf-8",
    )

    df = load_simprints(simprint)
    assert df.loc[0, "cluster"] == "0000000"
    assert bool(df.loc[0, "is_original"]) is True
    assert df.loc[1, "transform"] == "ome-tiff"
    assert df.loc[2, "cluster"] is None
