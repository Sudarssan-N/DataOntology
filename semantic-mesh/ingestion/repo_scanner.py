"""Repository scanner: walks directories, discovers files, routes to parsers, merges results."""

from __future__ import annotations

import os

from .schema_normalizer import ParsedSchema
from .sql_parser import parse_sql_file
from .code_parser import parse_python_file, parse_javascript_file, parse_typescript_file
from .java_parser import parse_java_file

# File extension → (parser_function, source_type)
_EXTENSION_MAP: dict[str, tuple[callable, str]] = {
    ".sql": (parse_sql_file, "sql"),
    ".py": (parse_python_file, "python"),
    ".js": (parse_javascript_file, "javascript"),
    ".ts": (parse_typescript_file, "typescript"),
    ".java": (parse_java_file, "java"),
}


def scan_repository(root_path: str) -> ParsedSchema:
    """Walk a directory tree, parse all supported files, and return a merged ParsedSchema."""
    merged = ParsedSchema()

    if not os.path.isdir(root_path):
        raise ValueError(f"Not a directory: {root_path}")

    for dirpath, _dirnames, filenames in os.walk(root_path):
        # Skip hidden directories and common non-source dirs
        _dirnames[:] = [
            d for d in _dirnames
            if not d.startswith(".")
            and d not in ("node_modules", "__pycache__", "venv", ".venv", "build", "dist", "target", ".git")
        ]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in _EXTENSION_MAP:
                continue

            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    source_code = f.read()
            except Exception:
                continue

            parser, source_type = _EXTENSION_MAP[ext]
            try:
                schema = parser(filepath, source_code)
                # Tag entities with source type if not already set
                for entity in schema.entities:
                    if not entity.source_type:
                        entity.source_type = source_type
                merged.merge(schema)
            except Exception:
                continue

    return merged


def scan_single_file(filepath: str, file_type: str | None = None) -> ParsedSchema:
    """Parse a single file, auto-detecting type from extension if not specified."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        source_code = f.read()

    parser = None

    if file_type:
        parser = _get_parser_for_type(file_type)
    else:
        ext = os.path.splitext(filepath)[1].lower()
        if ext in _EXTENSION_MAP:
            parser = _EXTENSION_MAP[ext][0]

    if parser is None:
        raise ValueError(f"Unsupported file type: {filepath}. Use --type to specify.")

    return parser(filepath, source_code)


def scan_input(input_path: str, file_type: str | None = None) -> ParsedSchema:
    """Scan a file or directory, auto-detecting the approach."""
    if os.path.isdir(input_path):
        return scan_repository(input_path)
    elif os.path.isfile(input_path):
        return scan_single_file(input_path, file_type)
    else:
        raise FileNotFoundError(f"Input not found: {input_path}")


def _get_parser_for_type(file_type: str) -> callable | None:
    type_map = {
        "sql": parse_sql_file,
        "python": parse_python_file,
        "javascript": parse_javascript_file,
        "typescript": parse_typescript_file,
        "java": parse_java_file,
    }
    return type_map.get(file_type.lower())
