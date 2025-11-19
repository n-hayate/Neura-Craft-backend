from dataclasses import dataclass


@dataclass
class FilenameMetadata:
    original_filename: str
    tags: list[str]


def extract_metadata(blob_name: str) -> FilenameMetadata:
    """
    Parse blob name (e.g., '2024/finance/report_q1.pdf') and return metadata.
    Tags are derived from folder hierarchy.
    """
    parts = blob_name.split("/")
    original_filename = parts[-1]
    tags = [part for part in parts[:-1] if part]
    return FilenameMetadata(original_filename=original_filename, tags=tags)


