from pathlib import Path

from src.ecc.infrastructure.storage.utils import compute_checksum


def test_compute_checksum(tmp_path: Path):
    p = tmp_path / "file.bin"
    p.write_bytes(b"hello world")
    chk = compute_checksum(p)
    # Precomputed sha256 of 'hello world'
    assert chk == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
