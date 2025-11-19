from scripts.utils.filename_parser import extract_metadata


def test_filename_parser_extracts_tags():
    meta = extract_metadata("2024/finance/report_q1.pdf")
    assert meta.original_filename == "report_q1.pdf"
    assert meta.tags == ["2024", "finance"]


