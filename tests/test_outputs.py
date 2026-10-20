import os, shutil, subprocess, sys


def test_verify_passes_on_committed_results(root):
    out = subprocess.run([sys.executable, "src/verify.py"], capture_output=True, text=True, check=True).stdout
    assert "FAIL" not in out
    assert out.strip().endswith("problems: 0")


def test_build_page_reproduces_index_html(root, tmp_path, monkeypatch):
    for f in ("src/build_page.py", "src/dashboard_template.html", "out/dashboard_data.json", "out/basemap.json"):
        os.makedirs(tmp_path / os.path.dirname(f), exist_ok=True)
        shutil.copy(f, tmp_path / f)
    subprocess.run([sys.executable, "src/build_page.py"], cwd=tmp_path, check=True, capture_output=True)
    assert (tmp_path / "index.html").read_bytes() == open("index.html", "rb").read()
