from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FilenameMetadata:
    original_filename: str
    application: Optional[str] = None
    issue: Optional[str] = None
    ingredient: Optional[str] = None
    customer: Optional[str] = None
    trial_id: Optional[str] = None
    author: Optional[str] = None


def extract_metadata(blob_name: str) -> FilenameMetadata:
    """
    Parse blob name (e.g., 'app/issue/ingredient/customer/TR01/author.xlsx')
    and map it to the 6 metadata slots when possible.
    """
    filename = Path(blob_name).name
    stem = Path(filename).stem
    parts = stem.split("_")

    fields = ["application", "issue", "ingredient", "customer", "trial_id", "author"]
    values = {field: None for field in fields}

    if len(parts) >= 6:
        for field, value in zip(fields, parts[:6]):
            cleaned = value.strip()
            values[field] = cleaned or None

    return FilenameMetadata(original_filename=filename, **values)
