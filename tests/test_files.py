from scripts.utils.filename_parser import extract_metadata


def test_filename_parser_extracts_metadata():
    meta = extract_metadata("app_issue_ingredient_customer_TR01_author.pdf")
    assert meta.original_filename == "app_issue_ingredient_customer_TR01_author.pdf"
    assert meta.application == "app"
    assert meta.issue == "issue"
    assert meta.ingredient == "ingredient"
    assert meta.customer == "customer"
    assert meta.trial_id == "TR01"
    assert meta.author == "author"


def test_filename_parser_handles_short_names():
    meta = extract_metadata("report.pdf")
    assert meta.original_filename == "report.pdf"
    assert meta.application is None
