"""Integration tests"""

from constantipy.analysis import analyze_codebase
from constantipy.common import Config
from constantipy.refactor import process_report

from .mock_args import MockArgs


def test_global_extraction_flow(tmp_path):
    """
    End-to-end test:
    1. Analyze two files sharing a string.
    2. Verify analysis finds it.
    3. Refactor (Apply).
    4. Verify constants.py created and files updated.
    """
    d = tmp_path / "src"
    d.mkdir()
    (d / "a.py").write_text('print("Shared String")', encoding="utf-8")
    (d / "b.py").write_text('x = "Shared String"', encoding="utf-8")

    args = MockArgs(path=d, min_count=2)
    config = Config(args)

    report = analyze_codebase(config)

    # Should find 1 shared constant
    assert len(report) == 1
    const_name = list(report.keys())[0]
    assert report[const_name]["value"] == "Shared String"
    assert report[const_name]["scope"] == "global"

    # Apply refactor
    process_report(config, report, apply=True)

    const_file = d / "constants.py"
    assert const_file.exists()
    content = const_file.read_text(encoding="utf-8")
    assert f"{const_name} = 'Shared String'" in content

    # Verify source update
    assert const_name in (d / "a.py").read_text(encoding="utf-8")
    assert const_name in (d / "b.py").read_text(encoding="utf-8")
