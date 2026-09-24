from __future__ import annotations

import hashlib
import io
import math
import os
import re
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from packbridge.ssd_schemas import SSDPreview
from packbridge.services.ssd_template import MAIN_NS, _workbook_maps, inspect_template


APPROVED_ROW_COLUMNS = {
    "C", "D", "E", "F", "G", "H", "I",
    "J", "K", "L",
    # M is intentionally excluded: the workbook formula is preserved.
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X",
}
NUMERIC_COLUMNS = {"C", "F", "J", "K", "L", "N", "O"}
APPROVED_HEADER_CELLS = {
    "E9", "E12", "E13", "E15", "E16", "E17",
    "M10", "T6", "T8", "T9", "T12", "T13",
}
EXPECTED_VALIDATION_COLUMNS = {"G", "O", "R", "T", "U", "V"}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
WORKSHEET_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
XLSX_WORKBOOK_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"


class SSDWriterError(ValueError):
    pass


def _q(tag: str) -> str:
    return f"{{{MAIN_NS}}}{tag}"


MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def _normalise_worksheet_ignorable(root: ET.Element) -> None:
    """Keep mc:Ignorable aligned with namespaces that survive XML serialisation.

    Rewriting a worksheet through ElementTree can drop unused namespace declarations
    such as xr2/xr3 while preserving the original mc:Ignorable token list. Excel then
    rejects the worksheet as schema-invalid because mc:Ignorable names undeclared
    prefixes. PackBridge currently retains x14ac and xr metadata on SoCs_Temp.
    """
    key = f"{{{MC_NS}}}Ignorable"
    if key not in root.attrib:
        return

    tokens = str(root.attrib.get(key) or "").split()
    retained = [token for token in tokens if token in {"x14ac", "xr"}]
    if retained:
        root.attrib[key] = " ".join(retained)
    else:
        root.attrib.pop(key, None)


def _parse_xml(payload: bytes) -> ET.Element:
    try:
        for _, namespace in ET.iterparse(io.BytesIO(payload), events=("start-ns",)):
            prefix, uri = namespace
            try:
                ET.register_namespace(prefix or "", uri)
            except ValueError:
                pass
    except ET.ParseError:
        pass
    return ET.fromstring(payload)


def _column_number(column: str) -> int:
    value = 0
    for character in column:
        value = value * 26 + (ord(character) - 64)
    return value


def _ref_column(ref: str) -> str:
    return "".join(character for character in ref if character.isalpha()).upper()


def _ref_row(ref: str) -> int:
    digits = "".join(character for character in ref if character.isdigit())
    if not digits:
        raise SSDWriterError(f"Invalid cell reference: {ref}")
    return int(digits)


def _ensure_cell(root: ET.Element, ref: str) -> ET.Element:
    sheet_data = root.find(_q("sheetData"))
    if sheet_data is None:
        sheet_data = ET.SubElement(root, _q("sheetData"))

    row_number = _ref_row(ref)
    row = next(
        (item for item in sheet_data.findall(_q("row")) if item.attrib.get("r") == str(row_number)),
        None,
    )
    if row is None:
        row = ET.Element(_q("row"), {"r": str(row_number)})
        inserted = False
        for index, existing in enumerate(list(sheet_data)):
            try:
                existing_number = int(existing.attrib.get("r", "0"))
            except ValueError:
                existing_number = 0
            if existing_number > row_number:
                sheet_data.insert(index, row)
                inserted = True
                break
        if not inserted:
            sheet_data.append(row)

    for cell in row.findall(_q("c")):
        if cell.attrib.get("r") == ref:
            return cell

    cell = ET.Element(_q("c"), {"r": ref})
    target_column = _column_number(_ref_column(ref))
    inserted = False
    for index, existing in enumerate(row.findall(_q("c"))):
        existing_ref = existing.attrib.get("r", "")
        if existing_ref and _column_number(_ref_column(existing_ref)) > target_column:
            row.insert(index, cell)
            inserted = True
            break
    if not inserted:
        row.append(cell)
    return cell


def _remove_value_nodes(cell: ET.Element) -> None:
    for name in ("v", "is"):
        child = cell.find(_q(name))
        if child is not None:
            cell.remove(child)
    cell.attrib.pop("t", None)


def _set_cell(cell: ET.Element, value: Any, *, numeric: bool = False) -> None:
    if cell.find(_q("f")) is not None:
        raise SSDWriterError(
            f"Refusing to overwrite formula cell {cell.attrib.get('r', '?')}."
        )

    _remove_value_nodes(cell)
    if value in (None, ""):
        return

    if numeric:
        if isinstance(value, bool):
            raise SSDWriterError(
                f"Boolean value is not valid for numeric cell {cell.attrib.get('r', '?')}."
            )
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise SSDWriterError(
                f"Value {value!r} is not numeric for {cell.attrib.get('r', '?')}."
            ) from exc
        if not math.isfinite(number):
            raise SSDWriterError(
                f"Value {value!r} is not finite for {cell.attrib.get('r', '?')}."
            )
        rendered = str(int(number)) if number.is_integer() else format(number, ".15g")
        value_node = ET.SubElement(cell, _q("v"))
        value_node.text = rendered
        return

    cell.attrib["t"] = "inlineStr"
    inline = ET.SubElement(cell, _q("is"))
    text = ET.SubElement(inline, _q("t"))
    rendered = str(value)
    if rendered != rendered.strip():
        text.attrib[XML_SPACE] = "preserve"
    text.text = rendered


def _read_cell(cell: ET.Element) -> Any:
    formula = cell.find(_q("f"))
    if formula is not None:
        return {"formula": formula.text or ""}
    if cell.attrib.get("t") == "inlineStr":
        inline = cell.find(_q("is"))
        if inline is None:
            return ""
        return "".join(node.text or "" for node in inline.iter(_q("t")))
    value = cell.find(_q("v"))
    if value is None or value.text is None:
        return None
    raw = value.text
    try:
        number = float(raw)
    except ValueError:
        return raw
    return int(number) if number.is_integer() else number


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalise_for_compare(value: Any, *, numeric: bool) -> Any:
    if value in (None, ""):
        return None
    if numeric:
        return float(value)
    return str(value)


def _translate_formula_row(formula: str, source_row: int, target_row: int) -> str:
    # Only translate relative row references to the template row. Absolute rows remain fixed.
    pattern = re.compile(rf"(\$?[A-Z]{{1,3}})(?<!\$)({source_row})(?!\d)")
    return pattern.sub(lambda match: f"{match.group(1)}{target_row}", formula)


def _retarget_row(template_row: ET.Element, source_row: int, target_row: int) -> ET.Element:
    row = deepcopy(template_row)
    row.attrib["r"] = str(target_row)
    for cell in row.findall(_q("c")):
        ref = cell.attrib.get("r", "")
        column = _ref_column(ref)
        cell.attrib["r"] = f"{column}{target_row}"
        formula = cell.find(_q("f"))
        if formula is not None and formula.text:
            formula.text = _translate_formula_row(formula.text, source_row, target_row)
        # Cached values must not survive a copied formula row.
        value = cell.find(_q("v"))
        if formula is not None and value is not None:
            cell.remove(value)
        elif formula is None:
            _remove_value_nodes(cell)
    return row


def _shift_footer_rows(root: ET.Element, after_row: int, delta: int) -> None:
    if delta <= 0:
        return
    sheet_data = root.find(_q("sheetData"))
    if sheet_data is None:
        return

    for row in sheet_data.findall(_q("row")):
        raw = row.attrib.get("r", "")
        if not raw.isdigit() or int(raw) <= after_row:
            continue
        old_row = int(raw)
        new_row = old_row + delta
        row.attrib["r"] = str(new_row)
        for cell in row.findall(_q("c")):
            ref = cell.attrib.get("r", "")
            column = _ref_column(ref)
            cell.attrib["r"] = f"{column}{new_row}"

    merge_cells = root.find(_q("mergeCells"))
    if merge_cells is not None:
        for merge in merge_cells.findall(_q("mergeCell")):
            ref = merge.attrib.get("ref", "")
            match = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", ref)
            if not match:
                continue
            c1, r1, c2, r2 = match.group(1), int(match.group(2)), match.group(3), int(match.group(4))
            if r1 > after_row:
                r1 += delta
                r2 += delta
                merge.attrib["ref"] = f"{c1}{r1}:{c2}{r2}"

    dimension = root.find(_q("dimension"))
    if dimension is not None:
        ref = dimension.attrib.get("ref", "")
        match = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", ref)
        if match and int(match.group(4)) > after_row:
            dimension.attrib["ref"] = (
                f"{match.group(1)}{match.group(2)}:{match.group(3)}{int(match.group(4)) + delta}"
            )


def _extend_validations(root: ET.Element, start_row: int, old_end: int, new_end: int) -> None:
    validations = root.find(_q("dataValidations"))
    if validations is None or new_end <= old_end:
        return
    for validation in validations.findall(_q("dataValidation")):
        parts = []
        for part in str(validation.attrib.get("sqref") or "").split():
            match = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", part.replace("$", ""))
            if (
                match
                and match.group(1) == match.group(3)
                and match.group(1) in EXPECTED_VALIDATION_COLUMNS
                and int(match.group(2)) <= start_row
                and int(match.group(4)) >= old_end
            ):
                parts.append(f"{match.group(1)}{start_row}:{match.group(1)}{new_end}")
            else:
                parts.append(part)
        validation.attrib["sqref"] = " ".join(parts)


def _expand_socs_sheet(
    root: ET.Element,
    *,
    start_row: int,
    old_end: int,
    new_end: int,
) -> None:
    if new_end <= old_end:
        return
    sheet_data = root.find(_q("sheetData"))
    if sheet_data is None:
        raise SSDWriterError("SoCs_Temp has no sheetData to expand.")

    template_row = next(
        (row for row in sheet_data.findall(_q("row")) if row.attrib.get("r") == str(old_end)),
        None,
    )
    if template_row is None:
        template_row = next(
            (row for row in sheet_data.findall(_q("row")) if row.attrib.get("r") == str(start_row)),
            None,
        )
    if template_row is None:
        raise SSDWriterError("SoCs_Temp has no package row available to use as an expansion pattern.")

    delta = new_end - old_end
    _shift_footer_rows(root, old_end, delta)

    for target_row in range(old_end + 1, new_end + 1):
        sheet_data.append(_retarget_row(template_row, old_end, target_row))

    sheet_data[:] = sorted(
        list(sheet_data),
        key=lambda row: int(row.attrib.get("r", "0")) if row.attrib.get("r", "").isdigit() else 0,
    )
    _extend_validations(root, start_row, old_end, new_end)


def _table2_part(archive: zipfile.ZipFile) -> tuple[str, ET.Element]:
    for name in archive.namelist():
        if not name.startswith("xl/tables/") or not name.endswith(".xml"):
            continue
        root = _parse_xml(archive.read(name))
        if root.attrib.get("name") == "Table2" or root.attrib.get("displayName") == "Table2":
            return name, root
    raise SSDWriterError("Required SoCs table Table2 could not be found.")


def _expand_table(table_root: ET.Element, new_end: int) -> None:
    table_root.attrib["ref"] = f"C22:W{new_end}"
    auto_filter = table_root.find(_q("autoFilter"))
    if auto_filter is not None:
        auto_filter.attrib["ref"] = f"C22:W{new_end}"


def _safe_sheet_name(prefix: str, case_number: str, used: set[str]) -> str:
    cleaned = re.sub(r"[\[\]:*?/\\]", "-", str(case_number or "").strip()) or "CASE"
    base = f"{prefix}-{cleaned}"[:31]
    candidate = base
    counter = 2
    while candidate in used:
        suffix = f"~{counter}"
        candidate = base[: 31 - len(suffix)] + suffix
        counter += 1
    used.add(candidate)
    return candidate


def _strip_clone_relationships(root: ET.Element) -> None:
    # Header/footer images and printer settings are presentation-only and would require
    # per-sheet relationship parts. The generated data structure does not depend on them.
    for tag in ("legacyDrawing", "legacyDrawingHF", "drawing"):
        node = root.find(_q(tag))
        if node is not None:
            root.remove(node)
    page_setup = root.find(_q("pageSetup"))
    if page_setup is not None:
        page_setup.attrib.pop(f"{{{REL_NS}}}id", None)

    # A cloned worksheet must not keep the template sheet's internal codeName.
    # Reusing Sheet2/Sheet3 across every PL/ML clone creates duplicate worksheet
    # identities that Excel repairs as corrupt workbook content.
    sheet_pr = root.find(_q("sheetPr"))
    if sheet_pr is not None:
        sheet_pr.attrib.pop("codeName", None)

    # Excel revision UUIDs are also identity-bearing metadata. Cloning them verbatim
    # duplicates the same xr:uid across every generated worksheet (and, for PL sheets,
    # across cloned dataValidation nodes). Strip revision identity metadata entirely;
    # Excel can regenerate it if needed.
    revision_namespaces = (
        "http://schemas.microsoft.com/office/spreadsheetml/2014/revision",
        "http://schemas.microsoft.com/office/spreadsheetml/2015/revision2",
        "http://schemas.microsoft.com/office/spreadsheetml/2016/revision3",
    )
    revision_attr_names = {
        f"{{{namespace}}}uid"
        for namespace in revision_namespaces
    }
    for node in root.iter():
        for attribute in list(node.attrib):
            if attribute in revision_attr_names:
                node.attrib.pop(attribute, None)

    # ElementTree omits unused namespace declarations when serialising. The source
    # template's mc:Ignorable may still mention xr/xr2/xr3 even after those namespaces
    # disappear, which Excel can flag during repair. Retain only x14ac, which is still
    # used by the cloned worksheet formatting metadata.
    mc_ignorable = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Ignorable"
    if mc_ignorable in root.attrib:
        root.attrib[mc_ignorable] = "x14ac"


def _clone_case_sheet(payload: bytes, selector_ref: str, case_number: str) -> bytes:
    root = _parse_xml(payload)
    _strip_clone_relationships(root)
    selector = _ensure_cell(root, selector_ref)
    formula = selector.find(_q("f"))
    if formula is not None:
        selector.remove(formula)
    _set_cell(selector, case_number, numeric=False)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _next_sheet_part_index(names: set[str]) -> int:
    indexes = []
    for name in names:
        match = re.fullmatch(r"xl/worksheets/sheet(\d+)\.xml", name)
        if match:
            indexes.append(int(match.group(1)))
    return max(indexes, default=0) + 1


def _add_case_sheets(
    archive: zipfile.ZipFile,
    replacements: dict[str, bytes],
    preview: SSDPreview,
) -> tuple[int, int]:
    sheet_paths, states = _workbook_maps(archive)
    pl_template = sheet_paths.get("PLs_Temp")
    ml_template = sheet_paths.get("MLs_Temp")
    if not pl_template or not ml_template:
        raise SSDWriterError("PLs_Temp and MLs_Temp are required to create per-case worksheets.")

    workbook = _parse_xml(archive.read("xl/workbook.xml"))
    workbook_rels = _parse_xml(archive.read("xl/_rels/workbook.xml.rels"))
    content_types = _parse_xml(archive.read("[Content_Types].xml"))
    sheets_node = workbook.find(_q("sheets"))
    if sheets_node is None:
        raise SSDWriterError("Workbook has no sheets collection.")

    used_names = set(states)
    existing_rids = {rel.attrib.get("Id", "") for rel in list(workbook_rels)}
    max_sheet_id = max((int(sheet.attrib.get("sheetId", "0")) for sheet in sheets_node), default=0)
    next_part = _next_sheet_part_index(set(archive.namelist()) | set(replacements))
    created_pl = 0
    created_ml = 0

    for row in preview.rows:
        case_number = str(row.case_number or f"CASE-{row.package_index + 1}")
        for prefix, template_part, selector_ref in (
            ("PL", pl_template, "G1"),
            ("ML", ml_template, "C37"),
        ):
            sheet_name = _safe_sheet_name(prefix, case_number, used_names)
            part_name = f"xl/worksheets/sheet{next_part}.xml"
            next_part += 1
            max_sheet_id += 1

            rid_base = f"rIdPackBridge{max_sheet_id}"
            rid = rid_base
            suffix = 2
            while rid in existing_rids:
                rid = f"{rid_base}_{suffix}"
                suffix += 1
            existing_rids.add(rid)

            replacements[part_name] = _clone_case_sheet(
                archive.read(template_part),
                selector_ref,
                case_number,
            )

            sheet = ET.SubElement(
                sheets_node,
                _q("sheet"),
                {
                    "name": sheet_name,
                    "sheetId": str(max_sheet_id),
                    f"{{{REL_NS}}}id": rid,
                },
            )
            ET.SubElement(
                workbook_rels,
                f"{{{PKG_REL_NS}}}Relationship",
                {
                    "Id": rid,
                    "Type": WORKSHEET_REL_TYPE,
                    "Target": f"worksheets/{Path(part_name).name}",
                },
            )
            ET.SubElement(
                content_types,
                f"{{{CONTENT_TYPES_NS}}}Override",
                {
                    "PartName": f"/{part_name}",
                    "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
                },
            )
            if prefix == "PL":
                created_pl += 1
            else:
                created_ml += 1

    replacements["xl/workbook.xml"] = ET.tostring(workbook, encoding="utf-8", xml_declaration=True)
    replacements["xl/_rels/workbook.xml.rels"] = ET.tostring(
        workbook_rels, encoding="utf-8", xml_declaration=True
    )
    replacements["[Content_Types].xml"] = ET.tostring(
        content_types, encoding="utf-8", xml_declaration=True
    )
    return created_pl, created_ml


def _remove_stale_calc_chain(
    archive: zipfile.ZipFile,
    replacements: dict[str, bytes],
) -> set[str]:
    """Drop the template calculation chain after changing formulas/sheets.

    Excel safely rebuilds calcChain.xml. Keeping the source chain after adding rows
    and cloned PL/ML worksheets can leave stale formula references and trigger a
    workbook repair prompt.
    """
    skipped: set[str] = set()
    calc_chain = "xl/calcChain.xml"
    if calc_chain in archive.namelist():
        skipped.add(calc_chain)

    rels_name = "xl/_rels/workbook.xml.rels"
    rels = _parse_xml(replacements.get(rels_name, archive.read(rels_name)))
    changed_rels = False
    for rel in list(rels):
        rel_type = rel.attrib.get("Type", "")
        target = rel.attrib.get("Target", "")
        if rel_type.endswith("/calcChain") or target.endswith("calcChain.xml"):
            rels.remove(rel)
            changed_rels = True
    if changed_rels:
        replacements[rels_name] = ET.tostring(
            rels, encoding="utf-8", xml_declaration=True
        )

    types_name = "[Content_Types].xml"
    content_types = _parse_xml(replacements.get(types_name, archive.read(types_name)))
    changed_types = False
    for node in list(content_types):
        if node.attrib.get("PartName") == "/xl/calcChain.xml":
            content_types.remove(node)
            changed_types = True
    if changed_types:
        replacements[types_name] = ET.tostring(
            content_types, encoding="utf-8", xml_declaration=True
        )

    return skipped


def _make_macro_free(archive: zipfile.ZipFile, replacements: dict[str, bytes]) -> set[str]:
    # Remove VBA and ActiveX controls that cannot be relied on in a clean XLSX output.
    # Core workbook data, formulas, validations, tables and ordinary drawings remain.
    for name in sorted(set(archive.namelist()) | set(replacements)):
        if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
            continue
        payload = replacements[name] if name in replacements else archive.read(name)
        root = _parse_xml(payload)
        changed = False
        for tag in ("controls", "legacyDrawing"):
            node = root.find(_q(tag))
            if node is not None:
                root.remove(node)
                changed = True
        if changed:
            replacements[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    for name in archive.namelist():
        if not name.startswith("xl/worksheets/_rels/") or not name.endswith(".rels"):
            continue
        rels = _parse_xml(replacements.get(name, archive.read(name)))
        changed = False
        for rel in list(rels):
            rel_type = rel.attrib.get("Type", "")
            target = rel.attrib.get("Target", "")
            if "/control" in rel_type or "activeX" in target:
                rels.remove(rel)
                changed = True
        if changed:
            replacements[name] = ET.tostring(rels, encoding="utf-8", xml_declaration=True)

    workbook_rels = _parse_xml(
        replacements.get("xl/_rels/workbook.xml.rels", archive.read("xl/_rels/workbook.xml.rels"))
    )
    for rel in list(workbook_rels):
        rel_type = rel.attrib.get("Type", "")
        target = rel.attrib.get("Target", "")
        if "vbaProject" in rel_type or "vbaProject" in target:
            workbook_rels.remove(rel)
    replacements["xl/_rels/workbook.xml.rels"] = ET.tostring(
        workbook_rels, encoding="utf-8", xml_declaration=True
    )

    content_types = _parse_xml(
        replacements.get("[Content_Types].xml", archive.read("[Content_Types].xml"))
    )
    for node in list(content_types):
        part_name = node.attrib.get("PartName", "")
        if "vbaProject" in part_name or part_name.startswith("/xl/activeX/"):
            content_types.remove(node)
            continue
        if part_name == "/xl/workbook.xml":
            node.attrib["ContentType"] = XLSX_WORKBOOK_CONTENT_TYPE
    replacements["[Content_Types].xml"] = ET.tostring(
        content_types, encoding="utf-8", xml_declaration=True
    )

    return {
        name
        for name in archive.namelist()
        if (
            name.startswith("xl/vbaProject")
            or name.startswith("xl/_rels/vbaProject")
            or name.startswith("xl/activeX/")
        )
    }

def write_socs_preview(
    template: str | Path,
    destination: str | Path,
    preview: SSDPreview,
    *,
    require_vba: bool = True,
    generate_case_sheets: bool = True,
) -> dict:
    """Build a verified SSD workbook, expanding package rows and case sheets as needed.

    The controlled XLSM/XLSX template remains the structural source. PackBridge expands
    Table2 to the required package count, inserts package rows before any footer marker,
    extends the verified validation ranges, and optionally clones PL/ML template sheets
    for each case. When the destination is .xlsx the VBA project is intentionally removed.
    """

    template = Path(template)
    destination = Path(destination)
    inspection = inspect_template(template)

    if not inspection.compatible:
        raise SSDWriterError(
            "SSD template is not structurally compatible: "
            + "; ".join(inspection.errors[:8])
        )
    if not inspection.generation_ready:
        raise SSDWriterError(
            "SSD template is not a clean generation template. "
            "Remove existing SoCs cases and generated PL/ML sheets first."
        )
    macro_free_output = destination.suffix.casefold() == ".xlsx"
    if require_vba and macro_free_output:
        raise SSDWriterError("An XLSX destination cannot be used when VBA is required.")
    if require_vba and not inspection.has_vba:
        raise SSDWriterError("The requested output requires a macro-enabled source template.")
    if preview.blocking:
        raise SSDWriterError(
            "SSD preview contains blocking issues: " + "; ".join(preview.blocking[:8])
        )
    if inspection.data_start_row is None or inspection.data_end_row is None:
        raise SSDWriterError("SSD template does not expose a usable SoCs table range.")

    start_row = inspection.data_start_row
    original_end = inspection.data_end_row
    required_end = max(original_end, start_row + max(len(preview.rows), 1) - 1)

    with zipfile.ZipFile(template, "r") as archive:
        sheet_paths, _ = _workbook_maps(archive)
        socs_path = sheet_paths.get("SoCs_Temp")
        if not socs_path or socs_path not in archive.namelist():
            raise SSDWriterError("SoCs_Temp worksheet part could not be found.")

        replacements: dict[str, bytes] = {}
        root = _parse_xml(archive.read(socs_path))
        _expand_socs_sheet(
            root,
            start_row=start_row,
            old_end=original_end,
            new_end=required_end,
        )

        table_path, table_root = _table2_part(archive)
        _expand_table(table_root, required_end)
        replacements[table_path] = ET.tostring(
            table_root, encoding="utf-8", xml_declaration=True
        )

        expected: dict[str, tuple[Any, bool]] = {}
        for ref, value in preview.header_cells.items():
            if ref not in APPROVED_HEADER_CELLS:
                continue
            cell = _ensure_cell(root, ref)
            _set_cell(cell, value, numeric=False)
            expected[ref] = (value, False)

        for row in preview.rows:
            row.excel_row = start_row + row.package_index
            for column in APPROVED_ROW_COLUMNS:
                ref = f"{column}{row.excel_row}"
                value = row.columns.get(column)
                numeric = column in NUMERIC_COLUMNS
                cell = _ensure_cell(root, ref)
                _set_cell(cell, value, numeric=numeric)
                expected[ref] = (value, numeric)

            formula_cell = _ensure_cell(root, f"M{row.excel_row}")
            formula = formula_cell.find(_q("f"))
            if formula is None:
                formula = ET.SubElement(formula_cell, _q("f"))
                formula.text = f"J{row.excel_row}*K{row.excel_row}*L{row.excel_row}/1000000"

        _normalise_worksheet_ignorable(root)
        replacements[socs_path] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        created_pl = 0
        created_ml = 0
        if generate_case_sheets and preview.rows:
            created_pl, created_ml = _add_case_sheets(archive, replacements, preview)

        # Formula-bearing rows and PL/ML worksheets have changed, so the template's
        # calculation chain is no longer authoritative. Excel will rebuild it.
        skipped_parts: set[str] = _remove_stale_calc_chain(archive, replacements)
        if macro_free_output:
            skipped_parts |= _make_macro_free(archive, replacements)

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            suffix=destination.suffix or template.suffix,
            dir=destination.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)

        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as output:
                written = set()
                for item in archive.infolist():
                    name = item.filename
                    if name in skipped_parts:
                        continue
                    if name in replacements:
                        output.writestr(item, replacements[name])
                        written.add(name)
                    else:
                        output.writestr(item, archive.read(name))
                for name, payload in replacements.items():
                    if name not in written and name not in skipped_parts:
                        output.writestr(name, payload)

            after = inspect_template(temporary)
            if not after.compatible:
                raise SSDWriterError(
                    "Generated workbook failed structural validation: "
                    + "; ".join(after.errors[:8])
                )
            if after.data_end_row is None or after.data_end_row < required_end:
                raise SSDWriterError(
                    f"Generated workbook did not expand Table2 to row {required_end}."
                )
            if require_vba and not after.has_vba:
                raise SSDWriterError("Generated workbook no longer contains the required VBA project.")
            if macro_free_output and after.has_vba:
                raise SSDWriterError("Macro-free XLSX output still contains a VBA project.")

            with zipfile.ZipFile(temporary, "r") as verify_archive:
                verify_root = _parse_xml(verify_archive.read(socs_path))
                actual_cells = {
                    cell.attrib.get("r", ""): cell
                    for cell in verify_root.findall(".//" + _q("c"))
                }
                mismatches = []
                for ref, (expected_value, numeric) in expected.items():
                    cell = actual_cells.get(ref)
                    actual = _read_cell(cell) if cell is not None else None
                    left = _normalise_for_compare(expected_value, numeric=numeric)
                    right = _normalise_for_compare(actual, numeric=numeric)
                    if left != right:
                        mismatches.append(f"{ref}: expected {left!r}, found {right!r}")
                if mismatches:
                    raise SSDWriterError(
                        "Generated workbook value verification failed: "
                        + "; ".join(mismatches[:10])
                    )

            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    final = inspect_template(destination)
    return {
        "path": str(destination),
        "sha256": _sha256(destination),
        "rows_written": len(preview.rows),
        "cells_written": len(expected),
        "original_capacity": inspection.row_capacity,
        "output_capacity": final.row_capacity,
        "rows_added": max(0, required_end - original_end),
        "pl_sheets_created": created_pl,
        "ml_sheets_created": created_ml,
        "structural_fingerprint": final.structural_fingerprint,
        "has_vba": final.has_vba,
        "warnings": list(preview.warnings),
    }
