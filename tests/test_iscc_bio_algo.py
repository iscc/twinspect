import sys
import types

from twinspect.algos.iscc_bio import bioimage_data_code_iw_64


def test_bioimage_data_code_iw_64_extracts_first_scene_data_code(monkeypatch, tmp_path):
    image = tmp_path / "image.ome.tiff"
    image.write_bytes(b"fake")

    fake_iscc_lib = types.ModuleType("iscc_lib")
    fake_iscc_lib.iscc_decode = lambda code: (
        None,
        None,
        None,
        None,
        bytes.fromhex("0011223344556677"),
    )

    fake_api = types.ModuleType("iscc_bio.api")
    fake_api.biocode = lambda fp, bits, source_type: [
        {"units": ["ISCC:DATA", "ISCC:INSTANCE"]},
        {"units": ["ISCC:OTHER", "ISCC:OTHERINSTANCE"]},
    ]

    fake_pkg = types.ModuleType("iscc_bio")
    fake_pkg.api = fake_api

    monkeypatch.setitem(sys.modules, "iscc_lib", fake_iscc_lib)
    monkeypatch.setitem(sys.modules, "iscc_bio", fake_pkg)
    monkeypatch.setitem(sys.modules, "iscc_bio.api", fake_api)

    assert bioimage_data_code_iw_64(image) == "0011223344556677"


def test_bioimage_data_code_iw_64_returns_none_on_empty_result(monkeypatch, tmp_path):
    image = tmp_path / "image.ome.tiff"
    image.write_bytes(b"fake")

    fake_iscc_lib = types.ModuleType("iscc_lib")
    fake_api = types.ModuleType("iscc_bio.api")
    fake_api.biocode = lambda fp, bits, source_type: []
    fake_pkg = types.ModuleType("iscc_bio")
    fake_pkg.api = fake_api

    monkeypatch.setitem(sys.modules, "iscc_lib", fake_iscc_lib)
    monkeypatch.setitem(sys.modules, "iscc_bio", fake_pkg)
    monkeypatch.setitem(sys.modules, "iscc_bio.api", fake_api)

    assert bioimage_data_code_iw_64(image) is None
