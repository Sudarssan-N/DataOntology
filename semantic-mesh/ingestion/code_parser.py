"""Code parser for Python (SQLAlchemy/Pydantic) and JS/TS (Mongoose/Sequelize/TypeORM)."""

from __future__ import annotations

import ast
import re

from .schema_normalizer import ColumnInfo, EntityInfo, ParsedSchema, RelationshipInfo


def parse_python_file(filepath: str, source_code: str) -> ParsedSchema:
    """Parse a Python file for SQLAlchemy/Pydantic models."""
    entities: list[EntityInfo] = []
    relationships: list[RelationshipInfo] = []

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return ParsedSchema()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        columns: list[ColumnInfo] = []
        table_name = ""
        relationships_from_class: list[RelationshipInfo] = []

        # Check if it inherits from Base or has __tablename__
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Base":
                break
            if isinstance(base, ast.Attribute) and base.attr == "Base":
                break
        else:
            # Also check for Pydantic/dataclass models
            has_tablename = any(
                isinstance(item, ast.Assign)
                and hasattr(item, "targets")
                and any(
                    isinstance(t, ast.Name) and t.id == "__tablename__"
                    for t in item.targets
                )
                for item in node.body
            )
            if not has_tablename:
                continue

        class_name = node.name

        for item in node.body:
            # Extract __tablename__
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(item.value, ast.Constant):
                            table_name = item.value.value

            # Extract Column() assignments
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        col_info = _extract_sqlalchemy_column(item)
                        if col_info:
                            columns.append(col_info)
                        else:
                            rel_info = _extract_sqlalchemy_relationship(item, class_name)
                            if rel_info:
                                relationships_from_class.append(rel_info)

        if not table_name:
            table_name = class_name.lower()

        entity = EntityInfo(
            name=_to_pascal_case(class_name),
            source_name=class_name,
            source_files=[filepath],
            columns=columns,
            source_type="python",
        )
        entities.append(entity)
        relationships.extend(relationships_from_class)

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


def _extract_sqlalchemy_column(assign_node: ast.Assign) -> ColumnInfo | None:
    """Extract column info from a SQLAlchemy Column() assignment."""
    if not isinstance(assign_node.value, ast.Call):
        return None

    call = assign_node.value
    func = call.func
    func_name = ""
    if isinstance(func, ast.Name):
        func_name = func.id
    elif isinstance(func, ast.Attribute):
        func_name = func.attr

    if func_name not in ("Column", "Field"):
        return None

    col_name = ""
    for target in assign_node.targets:
        if isinstance(target, ast.Name):
            col_name = target.id

    col_type = "unknown"
    is_pk = False
    is_fk = False
    fk_refs = None

    for arg in call.args:
        if isinstance(arg, ast.Name):
            col_type = _type_name_to_sql(arg.id)
        elif isinstance(arg, ast.Call):
            if isinstance(arg.func, ast.Name):
                col_type = arg.func.id.upper()
            elif isinstance(arg, ast.Attribute):
                col_type = arg.attr.upper()

    for kw in call.keywords:
        if kw.arg == "primary_key" and getattr(kw.value, "value", None) is True:
            is_pk = True
        if kw.arg == "ForeignKey":
            if isinstance(kw.value, ast.Call):
                fk_target = kw.value
            else:
                fk_target = kw.value
            if isinstance(fk_target, ast.Constant):
                parts = fk_target.value.split(".")
                fk_refs = (parts[0], parts[1] if len(parts) > 1 else "id")
                is_fk = True
            elif isinstance(fk_target, ast.Call) and fk_target.args:
                if isinstance(fk_target.args[0], ast.Constant):
                    parts = fk_target.args[0].value.split(".")
                    fk_refs = (parts[0], parts[1] if len(parts) > 1 else "id")
                    is_fk = True
        if kw.arg == "foreign_key":
            is_fk = True
            if isinstance(kw.value, ast.Constant):
                fk_refs = (kw.value.value, "id")

    if not col_name:
        return None

    return ColumnInfo(
        name=col_name,
        data_type=col_type,
        is_pk=is_pk,
        is_fk=is_fk,
        fk_references=fk_refs,
    )


def _extract_sqlalchemy_relationship(assign_node: ast.Assign, source_class: str) -> RelationshipInfo | None:
    """Extract relationship info from SQLAlchemy relationship() call."""
    if not isinstance(assign_node.value, ast.Call):
        return None

    call = assign_node.value
    func = call.func
    if isinstance(func, ast.Name) and func.id == "relationship":
        pass
    elif isinstance(func, ast.Attribute) and func.attr == "relationship":
        pass
    else:
        return None

    target_entity = ""
    back_populates = ""

    if call.args:
        target_entity = call.args[0] if isinstance(call.args[0], str) else ast.unparse(call.args[0])

    for kw in call.keywords:
        if kw.arg == "back_populates" and isinstance(kw.value, ast.Constant):
            back_populates = kw.value.value

    if not target_entity:
        return None

    target_name = target_entity.strip("\"'")

    return RelationshipInfo(
        source_entity=_to_pascal_case(source_class),
        target_entity=_to_pascal_case(target_name),
        relationship_type=back_populates.upper() if back_populates else "RELATES_TO",
        cardinality="1:N",
        via_column="",
        source_file="",
    )


def _type_name_to_sql(py_type: str) -> str:
    mapping = {
        "str": "VARCHAR",
        "int": "INTEGER",
        "float": "DOUBLE",
        "bool": "BOOLEAN",
        "UUID": "UUID",
        "datetime": "TIMESTAMP",
        "date": "DATE",
        "Decimal": "DECIMAL",
        "bytes": "BLOB",
    }
    return mapping.get(py_type, py_type.upper())


# ---- JavaScript / TypeScript parser (regex-based for MVP) ----

_MONGOOSE_SCHEMA_RE = re.compile(
    r"(?:const|let|var)\s+(\w+)\s*=\s*new\s+(?:mongoose\.)?Schema\s*\(\s*\{(.*?)\}\s*\)",
    re.DOTALL,
)
_MONGOOSE_FIELD_RE = re.compile(r"(\w+)\s*:\s*\{?\s*type\s*:\s*(\w+)", re.DOTALL)

_SEQUELIZE_MODEL_RE = re.compile(
    r"(?:sequelize|db)\.define\s*\(\s*['\"](\w+)['\"]\s*,\s*\{(.*?)\}",
    re.DOTALL,
)
_SEQUELIZE_FIELD_RE = re.compile(r"(\w+)\s*:\s*\{?\s*type\s*:\s*(?:DataTypes\.)?(\w+)", re.DOTALL)

_TYPEORM_ENTITY_RE = re.compile(r"@Entity\(\s*\{?\s*(?:name\s*:\s*['\"](\w+)['\"])?", re.DOTALL)
_TYPEORM_COLUMN_RE = re.compile(r"(\w+)\s*:\s*(\w+);", re.DOTALL)
_TYPEORM_CLASS_RE = re.compile(
    r"@Entity\([^)]*\)\s*(?:export\s+)?class\s+(\w+)",
    re.DOTALL,
)


def parse_javascript_file(filepath: str, source_code: str) -> ParsedSchema:
    return _parse_js_ts_common(filepath, source_code, "javascript")


def parse_typescript_file(filepath: str, source_code: str) -> ParsedSchema:
    return _parse_js_ts_common(filepath, source_code, "typescript")


def _parse_js_ts_common(filepath: str, source_code: str, source_type: str) -> ParsedSchema:
    entities: list[EntityInfo] = []
    relationships: list[RelationshipInfo] = []

    # Try Mongoose schemas first
    for match in _MONGOOSE_SCHEMA_RE.finditer(source_code):
        schema_name = match.group(1)
        body = match.group(2)
        columns: list[ColumnInfo] = []
        for fm in _MONGOOSE_FIELD_RE.finditer(body):
            fname, ftype = fm.group(1), fm.group(2)
            fk_refs = None
            is_fk = ftype in ("ObjectId", "Schema.Types.ObjectId", "mongoose.Schema.Types.ObjectId")
            if is_fk and fname.endswith("_id"):
                ref_table = fname[:-3]  # strip _id
                fk_refs = (ref_table + "s", "_id")
            columns.append(ColumnInfo(
                name=fname,
                data_type=ftype,
                is_pk=(fname == "_id" or fname == "id"),
                is_fk=is_fk,
                fk_references=fk_refs,
            ))
        entities.append(EntityInfo(
            name=_to_pascal_case(schema_name),
            source_name=schema_name,
            source_files=[filepath],
            columns=columns,
            source_type=source_type,
        ))
        _add_fk_relationships(relationships, _to_pascal_case(schema_name), columns, filepath)

    # Try Sequelize models
    for match in _SEQUELIZE_MODEL_RE.finditer(source_code):
        model_name = match.group(1)
        body = match.group(2)
        columns: list[ColumnInfo] = []
        for fm in _SEQUELIZE_FIELD_RE.finditer(body):
            fname, ftype = fm.group(1), fm.group(2)
            fk_refs = None
            is_fk = False
            if fname.endswith("Id") or fname.endswith("_id"):
                is_fk = True
                ref_table = re.sub(r"(Id|_id)$", "", fname) + "s"
                fk_refs = (ref_table, "id")
            columns.append(ColumnInfo(
                name=fname,
                data_type=ftype,
                is_pk=(fname.lower() == "id"),
                is_fk=is_fk,
                fk_references=fk_refs,
            ))
        entities.append(EntityInfo(
            name=_to_pascal_case(model_name),
            source_name=model_name,
            source_files=[filepath],
            columns=columns,
            source_type=source_type,
        ))
        _add_fk_relationships(relationships, _to_pascal_case(model_name), columns, filepath)

    # Try TypeORM entities (mostly TypeScript)
    for match in _TYPEORM_CLASS_RE.finditer(source_code):
        class_name = match.group(1)
        columns: list[ColumnInfo] = []
        for fm in _TYPEORM_COLUMN_RE.finditer(source_code):
            fname, ftype = fm.group(1), fm.group(2)
            if fname in ("class", "export", "function", "const"):
                continue
            columns.append(ColumnInfo(
                name=fname,
                data_type=ftype,
                is_pk=(fname.lower() == "id"),
                is_fk=fname.lower().endswith("id") and fname.lower() != "id",
                fk_references=(fname[:-2] + "s", "id") if fname.lower().endswith("id") and fname.lower() != "id" else None,
            ))
        if columns:
            entities.append(EntityInfo(
                name=_to_pascal_case(class_name),
                source_name=class_name,
                source_files=[filepath],
                columns=columns,
                source_type=source_type,
            ))
            _add_fk_relationships(relationships, _to_pascal_case(class_name), columns, filepath)

    return ParsedSchema(entities=entities, relationships=relationships)


def _add_fk_relationships(
    relationships: list, entity_name: str, columns: list, filepath: str
) -> None:
    """Generate RelationshipInfo from FK columns."""
    from .schema_normalizer import RelationshipInfo

    for col in columns:
        if col.is_fk and col.fk_references:
            relationships.append(RelationshipInfo(
                source_entity=entity_name,
                target_entity=_to_pascal_case(col.fk_references[0]),
                relationship_type="FK_TO",
                cardinality="N:1",
                via_column=col.name,
                source_file=filepath,
            ))


def _to_pascal_case(name: str) -> str:
    parts = name.replace("-", "_").split("_")
    return "".join(p.capitalize() for p in parts if p)
