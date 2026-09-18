from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

REQUIRED_SHEETS = {
    "SoCs_Temp": "visible",
    "PLs_Temp": "veryHidden",
    "MLs_Temp": "veryHidden",
}
EXPECTED_TABLE = {"name": "Table2", "ref": "C22:W90"}
EXPECTED_SOCS_HEADERS = {
    "C21": "Qty",
    "D21": "Content Description / Equipment (Name)",
    "E21": "EQ (nnn)",
    "G21": "Declare As",
    "H21": "PO Number",
    "I21": "PO Pos.Nr.",
    "J21": "Case Dimensions",
    "M21": "Volume (cbm)",
    "N21": "Net Weight (Kg.)",
    "O21": "Gross Weight (Kg.)",
    "R21": "Storage Requirements",
    "S21": "Case Number",
    "T21": "Packaging Material",
    "U21": "Stackability",
}
EXPECTED_VALIDATION_RANGES = {
    "G23:G90",
    "O23:O90",
    "R23:R90",
    "T23:T90",
    "U23:U90",
    "V23:V90",
}


@dataclass(frozen=True)
class TableInfo:
    name: str
    display_name: str
    ref: str
    columns: tuple[str, ...]


@dataclass
class TemplateInspection:
    path: str
    filename: str
    sha256: str
    structural_fingerprint: str
    valid_zip: bool = False
    compatible: bool = False
    has_vba: bool = False
    workbook_type: str = "unknown"
    sheet_count: int = 0
    sheets: dict[str, str] = field(default_factory=dict)
    tables: list[TableInfo] = field(default_factory=list)
    validations: list[dict[str, Any]] = field(default_factory=list)
    socs_headers: dict[str, str | None] = field(default_factory=dict)
    generated_pl_count: int = 0
    generated_ml_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["tables"] = [asdict(item) for item in self.tables]
        return value


def _q(tag: str) -> str:
    return f"{{{MAIN_NS}}}{tag}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    name = "xl/sharedStrings.xml"
    if name not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(name))
    return [
        "".join(node.text or "" for node in item.iter(_q("t")))
        for item in root.findall(_q("si"))
    ]


def _cell_value(cell: ET.Element, shared: list[str]) -> str | None:
    value = cell.find(_q("v"))
    raw = value.text if value is not None else None
    cell_type = cell.attrib.get("t")
    if cell_type == "s" and raw is not None:
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return raw
    if cell_type == "inlineStr":
        inline = cell.find(_q("is"))
        return (
            "".join(node.text or "" for node in inline.iter(_q("t")))
            if inline is not None
            else ""
        )
    return raw


def _normalise_target(target: str) -> str:
    target = target.replace("\\", "/").lstrip("/")
    if target.startswith("xl/"):
        return target
    while target.startswith("../"):
        target = target[3:]
    return "xl/" + target


def _workbook_maps(
    archive: zipfile.ZipFile,
) -> tuple[dict[str, str], dict[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationships = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in rels.findall(f"{{{PKG_REL_NS}}}Relationship")
    }
    sheet_paths: dict[str, str] = {}
    states: dict[str, str] = {}
    sheets = workbook.find(_q("sheets"))
    if sheets is None:
        return sheet_paths, states
    rel_key = f"{{{REL_NS}}}id"
    for sheet in sheets:
        name = sheet.attrib.get("name", "")
        relationship_id = sheet.attrib.get(rel_key, "")
        target = relationships.get(relationship_id)
        if not name or not target:
            continue
        sheet_paths[name] = _normalise_target(target)
        states[name] = sheet.attrib.get("state", "visible")
    return sheet_paths, states


def _tables(archive: zipfile.ZipFile) -> list[TableInfo]:
    result: list[TableInfo] = []
    for name in sorted(
        item for item in archive.namelist() if item.startswith("xl/tables/") and item.endswith(".xml")
    ):
        root = ET.fromstring(archive.read(name))
        columns_node = root.find(_q("tableColumns"))
        columns = tuple(
            item.attrib.get("name", "")
            for item in (columns_node or [])
        )
        result.append(
            TableInfo(
                name=root.attrib.get("name", ""),
                display_name=root.attrib.get("displayName", ""),
                ref=root.attrib.get("ref", ""),
                columns=columns,
            )
        )
    return result


def _sheet_cells(
    archive: zipfile.ZipFile,
    sheet_path: str,
    shared: list[str],
    refs: set[str],
) -> dict[str, str | None]:
    root = ET.fromstring(archive.read(sheet_path))
    output: dict[str, str | None] = {ref: None for ref in refs}
    for cell in root.findall(".//" + _q("c")):
        ref = cell.attrib.get("r")
        if ref in refs:
            output[ref] = _cell_value(cell, shared)
    return output


def _validations(
    archive: zipfile.ZipFile,
    sheet_path: str,
) -> list[dict[str, Any]]:
    root = ET.fromstring(archive.read(sheet_path))
    result = []
    validations = root.find(_q("dataValidations"))
    if validations is None:
        return result
    for node in validations.findall(_q("dataValidation")):
        formula1 = node.find(_q("formula1"))
        formula2 = node.find(_q("formula2"))
        result.append(
            {
                "sqref": node.attrib.get("sqref", ""),
                "type": node.attrib.get("type", ""),
                "operator": node.attrib.get("operator", ""),
                "formula1": formula1.text if formula1 is not None else None,
                "formula2": formula2.text if formula2 is not None else None,
            }
        )
    return result


def _structure_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def inspect_template(path: str | Path) -> TemplateInspection:
    path = Path(path)
    inspection = TemplateInspection(
        path=str(path),
        filename=path.name,
        sha256=_sha256(path) if path.is_file() else "",
        structural_fingerprint="",
    )
    if not path.is_file():
        inspection.errors.append("Template file does not exist.")
        return inspection

    try:
        with zipfile.ZipFile(path) as archive:
            inspection.valid_zip = True
            names = set(archive.namelist())
            inspection.has_vba = "xl/vbaProject.bin" in names
            inspection.workbook_type = "xlsm" if inspection.has_vba else "xlsx"

            if "xl/workbook.xml" not in names or "xl/_rels/workbook.xml.rels" not in names:
                inspection.errors.append("Workbook package is missing workbook metadata.")
                return inspection

            shared = _shared_strings(archive)
            sheet_paths, states = _workbook_maps(archive)
            inspection.sheets = states
            inspection.sheet_count = len(states)
            inspection.generated_pl_count = sum(
                1 for name in states if re.fullmatch(r"PL-.+", name)
            )
            inspection.generated_ml_count = sum(
                1 for name in states if re.fullmatch(r"ML-.+", name)
            )

            for required, expected_state in REQUIRED_SHEETS.items():
                if required not in states:
                    inspection.errors.append(f"Required worksheet is missing: {required}.")
                elif states[required] != expected_state:
                    inspection.warnings.append(
                        f"{required} is {states[required]!r}; expected {expected_state!r}."
                    )

            inspection.tables = _tables(archive)
            table = next(
                (
                    item
                    for item in inspection.tables
                    if item.name == EXPECTED_TABLE["name"]
                    or item.display_name == EXPECTED_TABLE["name"]
                ),
                None,
            )
            if table is None:
                inspection.errors.append("Required SoCs table Table2 was not found.")
            elif table.ref != EXPECTED_TABLE["ref"]:
                inspection.errors.append(
                    f"Table2 uses {table.ref}; expected {EXPECTED_TABLE['ref']}."
                )

            socs_path = sheet_paths.get("SoCs_Temp")
            if socs_path and socs_path in names:
                inspection.socs_headers = _sheet_cells(
                    archive,
                    socs_path,
                    shared,
                    set(EXPECTED_SOCS_HEADERS),
                )
                for ref, expected in EXPECTED_SOCS_HEADERS.items():
                    actual = inspection.socs_headers.get(ref)
                    if actual != expected:
                        inspection.errors.append(
                            f"SoCs_Temp {ref} is {actual!r}; expected {expected!r}."
                        )
                inspection.validations = _validations(archive, socs_path)
                present_ranges = {
                    part
                    for validation in inspection.validations
                    for part in str(validation.get("sqref") or "").split()
                }
                missing_validations = sorted(EXPECTED_VALIDATION_RANGES - present_ranges)
                if missing_validations:
                    inspection.errors.append(
                        "Required SoCs validation ranges are missing: "
                        + ", ".join(missing_validations)
                    )
            elif "SoCs_Temp" in sheet_paths:
                inspection.errors.append("SoCs_Temp worksheet XML is missing.")

            if not inspection.has_vba:
                inspection.warnings.append(
                    "Workbook has no VBA project. This can be valid only after macro-free SAP/output testing."
                )

            structure = {
                "required_sheets": {
                    name: states.get(name) for name in sorted(REQUIRED_SHEETS)
                },
                "table": asdict(table) if table else None,
                "headers": inspection.socs_headers,
                "validations": sorted(
                    (
                        item.get("sqref"),
                        item.get("type"),
                        item.get("operator"),
                        item.get("formula1"),
                    )
                    for item in inspection.validations
                ),
                "has_vba": inspection.has_vba,
            }
            inspection.structural_fingerprint = _structure_fingerprint(structure)
            inspection.compatible = not inspection.errors
    except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError, ValueError) as exc:
        inspection.errors.append(f"Could not inspect SSD template: {exc}")

    return inspection
