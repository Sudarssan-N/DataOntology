"""SQL DDL parser using sqlglot. Extracts tables, columns, PKs, and FKs."""

from __future__ import annotations

import sqlglot
from sqlglot import exp

from .schema_normalizer import ColumnInfo, EntityInfo, ParsedSchema, RelationshipInfo


def parse_sql_file(filepath: str, source_code: str) -> ParsedSchema:
    """Parse a SQL DDL file and return a ParsedSchema."""
    entities: list[EntityInfo] = []
    relationships: list[RelationshipInfo] = []

    try:
        parsed = sqlglot.parse(source_code, read="postgres")
    except Exception:
        parsed = sqlglot.parse(source_code)

    for statement in parsed:
        if statement is None:
            continue

        create_tables = statement.find_all(exp.Create)
        for ct in create_tables:
            table_exp = ct.find(exp.Table)
            if table_exp is None:
                continue

            table_name = table_exp.name
            if not table_name:
                continue

            columns: list[ColumnInfo] = []
            schema = ct.find(exp.Schema)
            if schema is None:
                continue

            for col_def in schema.expressions:
                if isinstance(col_def, exp.ColumnDef):
                    col = _parse_column(col_def)
                    columns.append(col)
                elif isinstance(col_def, exp.ForeignKey):
                    fk_rel = _parse_inline_fk(col_def, table_name)
                    if fk_rel:
                        relationships.append(fk_rel)
                elif isinstance(col_def, exp.PrimaryKey):
                    # Table-level PK constraint
                    for pk_col in col_def.expressions:
                        col_name = pk_col.name if isinstance(pk_col, exp.Column) else str(pk_col)
                        for c in columns:
                            if c.name == col_name:
                                c.is_pk = True

            entity = EntityInfo(
                name=_to_pascal_case(table_name),
                source_name=table_name,
                source_files=[filepath],
                columns=columns,
                source_type="sql",
            )
            entities.append(entity)

            # Generate relationships from FK columns
            for col in columns:
                if col.is_fk and col.fk_references:
                    rel = RelationshipInfo(
                        source_entity=entity.name,
                        target_entity=_to_pascal_case(col.fk_references[0]),
                        relationship_type="FK_TO",
                        cardinality="N:1",
                        via_column=col.name,
                        source_file=filepath,
                    )
                    relationships.append(rel)

    return ParsedSchema(entities=entities, relationships=relationships)


def _parse_column(col_def: exp.ColumnDef) -> ColumnInfo:
    col_name = col_def.name
    col_type = col_def.kind.sql() if col_def.kind else "unknown"

    is_pk = False
    is_fk = False
    fk_refs = None

    for constraint in col_def.constraints:
        kind_str = str(constraint.kind).upper()
        if "PRIMARY" in kind_str:
            is_pk = True
        if "UNIQUE" in kind_str:
            pass  # Track for cardinality later

    ref = col_def.find(exp.Reference)
    if ref:
        is_fk = True
        fk_table = ref.find(exp.Table)
        if fk_table:
            # The referenced column may be an Identifier or Column node
            identifiers = [n for n in ref.walk() if isinstance(n, exp.Identifier) and n.name != fk_table.name]
            ref_col_name = identifiers[-1].name if identifiers else "id"
            fk_refs = (fk_table.name, ref_col_name)

    return ColumnInfo(
        name=col_name,
        data_type=col_type,
        is_pk=is_pk,
        is_fk=is_fk,
        fk_references=fk_refs,
    )


def _parse_inline_fk(fk: exp.ForeignKey, source_table: str) -> RelationshipInfo | None:
    ref = fk.find(exp.Reference)
    if not ref:
        return None
    ref_table = ref.find(exp.Table)
    if not ref_table:
        return None

    fk_cols = [c.name for c in fk.expressions if isinstance(c, exp.Column)]
    via = fk_cols[0] if fk_cols else "unknown"

    return RelationshipInfo(
        source_entity=_to_pascal_case(source_table),
        target_entity=_to_pascal_case(ref_table.name),
        relationship_type="FK_TO",
        cardinality="N:1",
        via_column=via,
        source_file="",
    )


def _to_pascal_case(name: str) -> str:
    """Convert snake_case or lowercase to PascalCase."""
    parts = name.replace("-", "_").split("_")
    return "".join(p.capitalize() for p in parts if p)
