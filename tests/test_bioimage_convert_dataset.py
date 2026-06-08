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


def test_build_cluster_keeps_original_first_and_adds_identity_and_similarity_variants(
    monkeypatch, tmp_path
):
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

    pixel_variant_calls = []

    def fake_apply_pixel_variant(input_path, output_path, variant_name):
        pixel_variant_calls.append((input_path.name, output_path.name, variant_name))
        output_path.write_bytes(variant_name.encode("utf-8"))
        return output_path

    monkeypatch.setattr(bic, "extract_member", fake_extract_member)
    monkeypatch.setattr(bic, "convert_file", fake_convert_file)
    monkeypatch.setattr(bic, "apply_pixel_variant", fake_apply_pixel_variant)

    cluster = tmp_path / "0000000"
    bic.build_cluster(sample, cluster)

    names = sorted(path.name for path in cluster.iterdir())
    assert names == [
        "0original.TIF",
        "1variant_ome-tiff.ome.tiff",
        "2variant_tiff.tiff",
        "3variant_png.png",
        "4variant_brightness-png.png",
        "5variant_blur-png.png",
    ]
    assert pixel_variant_calls == [
        ("3variant_png.png", "4variant_brightness-png.png", "brightness"),
        ("3variant_png.png", "5variant_blur-png.png", "blur"),
    ]
    bic.validate_cluster(cluster)


def test_apply_pixel_variant_creates_readable_nonempty_png(tmp_path):
    from PIL import Image

    src = tmp_path / "source.tif"
    out = tmp_path / "brightness.png"
    Image.new("L", (32, 32), 128).save(src)

    result = bic.apply_pixel_variant(src, out, "brightness")

    assert result == out
    assert out.stat().st_size > 0
    assert Image.open(out).size == (32, 32)


def test_apply_pixel_variants_change_pixels_on_nonuniform_input(tmp_path):
    from PIL import Image, ImageChops

    src = tmp_path / "source.png"
    image = Image.new("L", (32, 32), 0)
    for x in range(8, 24):
        for y in range(8, 24):
            image.putpixel((x, y), 128)
    image.save(src)

    for variant in ("brightness", "blur"):
        out = tmp_path / f"{variant}.png"
        bic.apply_pixel_variant(src, out, variant)
        with Image.open(src) as original, Image.open(out) as changed:
            assert ImageChops.difference(original, changed).getbbox() is not None


def test_bioimage_convert_command_allows_template(monkeypatch):
    monkeypatch.setenv(
        "TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE",
        "converter --input {input} --output {output} --format {format}",
    )
    command = bic.bioimage_convert_command(Path("in.tif"), Path("out.png"), "png")
    assert command == ["converter", "--input", "in.tif", "--output", "out.png", "--format", "png"]


def test_bioformats_tools_archive_is_pinned():
    assert bic.BIOFORMATS_VERSION == "8.5.0"
    assert bic.BFTOOLS_URL.endswith("/bio-formats/8.5.0/artifacts/bftools.zip")
    assert bic.BFTOOLS_SHA256 == "07a3bb1d3de84da3a709655a1008cb2d9b19becc5bad4ae4112633aec9380478"


def test_default_converter_command_uses_pinned_bfconvert(monkeypatch, tmp_path):
    monkeypatch.delenv("TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE", raising=False)
    monkeypatch.delenv("TWINSPECT_BIOIMAGE_CONVERT_BIN", raising=False)
    fake = tmp_path / ("bfconvert.bat" if bic.platform.system() == "Windows" else "bfconvert")
    fake.write_text("", encoding="utf-8")
    monkeypatch.setattr(bic, "ensure_bioformats_tools", lambda cache_dir=None: fake)

    command = bic.bioimage_convert_command(Path("in.tif"), Path("out.ome.tiff"), "ome-tiff")

    assert command == [str(fake), "in.tif", "out.ome.tiff"]


def test_ensure_bioformats_tools_downloads_verifies_and_extracts(monkeypatch, tmp_path):
    archive = tmp_path / "fixture-bftools.zip"
    import hashlib
    from zipfile import ZipFile

    script_name = "bfconvert.bat" if bic.platform.system() == "Windows" else "bfconvert"
    with ZipFile(archive, "w") as zf:
        zf.writestr(f"bftools/{script_name}", "echo bfconvert")
        zf.writestr("bftools/bf.sh", "echo bf")
        zf.writestr("bftools/bioformats_package.jar", "jar")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()

    monkeypatch.setattr(bic, "BFTOOLS_SHA256", digest)
    monkeypatch.setattr(bic, "download_file", lambda url, path: path.write_bytes(archive.read_bytes()))

    bfconvert = bic.ensure_bioformats_tools(tmp_path / "tools")

    assert bfconvert.name == script_name
    assert bfconvert.exists()
    assert (bfconvert.parent / "bioformats_package.jar").exists()
    if bic.platform.system() != "Windows":
        assert bfconvert.stat().st_mode & 0o111
        assert (bfconvert.parent / "bf.sh").stat().st_mode & 0o111


def test_ensure_bioformats_tools_selects_windows_launcher(monkeypatch, tmp_path):
    archive = tmp_path / "fixture-bftools.zip"
    import hashlib
    from zipfile import ZipFile

    with ZipFile(archive, "w") as zf:
        zf.writestr("bftools/bfconvert.bat", "call bf.bat")
        zf.writestr("bftools/bioformats_package.jar", "jar")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()

    monkeypatch.setattr(bic.platform, "system", lambda: "Windows")
    monkeypatch.setattr(bic, "BFTOOLS_SHA256", digest)
    monkeypatch.setattr(bic, "download_file", lambda url, path: path.write_bytes(archive.read_bytes()))

    bfconvert = bic.ensure_bioformats_tools(tmp_path / "tools")

    assert bfconvert.name == "bfconvert.bat"


def test_safe_extract_zip_rejects_path_traversal(tmp_path):
    archive = tmp_path / "evil.zip"
    from zipfile import ZipFile

    with ZipFile(archive, "w") as zf:
        zf.writestr("../evil", "nope")

    with pytest.raises(RuntimeError, match="Unsafe archive"):
        bic.safe_extract_zip(archive, tmp_path / "extract")


def test_ensure_bioformats_tools_rejects_checksum_mismatch(monkeypatch, tmp_path):
    monkeypatch.setattr(bic, "download_file", lambda url, path: path.write_bytes(b"wrong"))
    monkeypatch.setattr(bic, "BFTOOLS_SHA256", "0" * 64)

    with pytest.raises(RuntimeError, match="checksum"):
        bic.ensure_bioformats_tools(tmp_path / "tools")


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
