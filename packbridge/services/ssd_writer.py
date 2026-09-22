from __future__ import annotations

import hashlib
import io
import math
import os
import tempfile
import zipfile
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
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


class SSDWriterError(ValueError):
    pass


def _q(tag: str) -> str:
    return f"{{{MAIN_NS}}}{tag}"


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


def write_socs_preview(
    template: str | Path,
    destination: str | Path,
    preview: SSDPreview,
    *,
    require_vba: bool = True,
) -> dict:
    """Write an already-reviewed SSD preview into a clean controlled template.

    This writer intentionally touches only the verified SoCs cells. It does not create
    Packing List or Marking Label sheets and never calls VBA. The macro project is
    copied byte-for-byte as part of the OOXML package.
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
    if require_vba and not inspection.has_vba:
        raise SSDWriterError(
            "The first controlled writer requires the macro-enabled template. "
            "Macro-free output has not yet passed SAP acceptance testing."
        )
    if preview.blocking:
        raise SSDWriterError(
            "SSD preview contains blocking issues: " + "; ".join(preview.blocking[:8])
        )
    capacity = inspection.row_capacity
    if capacity <= 0 or inspection.data_start_row is None or inspection.data_end_row is None:
        raise SSDWriterError("SSD template does not expose a usable SoCs table capacity.")
    if len(preview.rows) > capacity:
        raise SSDWriterError(
            f"SSD preview contains {len(preview.rows)} package rows but this template supports {capacity}."
        )

    with zipfile.ZipFile(template, "r") as archive:
        sheet_paths, _ = _workbook_maps(archive)
        socs_path = sheet_paths.get("SoCs_Temp")
        if not socs_path or socs_path not in archive.namelist():
            raise SSDWriterError("SoCs_Temp worksheet part could not be found.")

        root = _parse_xml(archive.read(socs_path))
        expected: dict[str, tuple[Any, bool]] = {}

        for ref, value in preview.header_cells.items():
            if ref not in APPROVED_HEADER_CELLS:
                continue
            cell = _ensure_cell(root, ref)
            _set_cell(cell, value, numeric=False)
            expected[ref] = (value, False)

        for row in preview.rows:
            if row.excel_row is None:
                raise SSDWriterError(
                    f"Case {row.case_number or row.package_index} has no valid SSD row."
                )
            if not inspection.data_start_row <= row.excel_row <= inspection.data_end_row:
                raise SSDWriterError(
                    f"SSD row {row.excel_row} is outside this template's data range "
                    f"C{inspection.data_start_row}:X{inspection.data_end_row}."
                )

            for column in APPROVED_ROW_COLUMNS:
                ref = f"{column}{row.excel_row}"
                value = row.columns.get(column)
                numeric = column in NUMERIC_COLUMNS
                cell = _ensure_cell(root, ref)
                _set_cell(cell, value, numeric=numeric)
                expected[ref] = (value, numeric)

            # Formula column M must exist and remain a formula.
            formula_cell = _ensure_cell(root, f"M{row.excel_row}")
            if formula_cell.find(_q("f")) is None:
                raise SSDWriterError(
                    f"Template formula M{row.excel_row} is missing; refusing to synthesize it."
                )

        updated_socs = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            suffix=destination.suffix or template.suffix,
            dir=destination.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)

        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as output:
                for item in archive.infolist():
                    if item.filename == socs_path:
                        output.writestr(item, updated_socs)
                    else:
                        output.writestr(item, archive.read(item.filename))

            after = inspect_template(temporary)
            if not after.compatible:
                raise SSDWriterError(
                    "Generated workbook failed structural validation: "
                    + "; ".join(after.errors[:8])
                )
            if after.structural_fingerprint != inspection.structural_fingerprint:
                raise SSDWriterError(
                    "Generated workbook structure fingerprint differs from the controlled template."
                )
            if require_vba and not after.has_vba:
                raise SSDWriterError("Generated workbook no longer contains the VBA project.")

            # Re-open the actual output XML and compare every explicitly written cell.
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
        "structural_fingerprint": final.structural_fingerprint,
        "has_vba": final.has_vba,
        "warnings": list(preview.warnings),
    }
