"""Normalized internal schema shared by all parsers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_pk: bool = False
    is_fk: bool = False
    fk_references: Optional[tuple[str, str]] = None  # (target_table, target_column)


@dataclass
class EntityInfo:
    name: str
    source_name: str
    source_files: list[str] = field(default_factory=list)
    columns: list[ColumnInfo] = field(default_factory=list)
    source_type: str = ""  # "sql", "python", "javascript", "typescript", "java"

    @property
    def pks(self) -> list[str]:
        return [c.name for c in self.columns if c.is_pk]

    @property
    def fks(self) -> list[str]:
        return [c.name for c in self.columns if c.is_fk]


@dataclass
class RelationshipInfo:
    source_entity: str
    target_entity: str
    relationship_type: str = ""
    cardinality: str = ""  # "1:1", "1:N", "N:1", "M:N"
    via_column: str = ""
    source_file: str = ""


@dataclass
class ParsedSchema:
    entities: list[EntityInfo] = field(default_factory=list)
    relationships: list[RelationshipInfo] = field(default_factory=list)

    def merge(self, other: ParsedSchema) -> None:
        """Merge another ParsedSchema into this one, deduplicating entities by name."""
        existing_names = {e.name for e in self.entities}

        for entity in other.entities:
            if entity.name in existing_names:
                existing = next(e for e in self.entities if e.name == entity.name)
                existing.source_files = list(set(existing.source_files + entity.source_files))
                existing_cols = {c.name for c in existing.columns}
                for col in entity.columns:
                    if col.name not in existing_cols:
                        existing.columns.append(col)
            else:
                self.entities.append(entity)
                existing_names.add(entity.name)

        seen_rels = {(r.source_entity, r.target_entity, r.via_column) for r in self.relationships}
        for rel in other.relationships:
            key = (rel.source_entity, rel.target_entity, rel.via_column)
            if key not in seen_rels:
                self.relationships.append(rel)
                seen_rels.add(key)
