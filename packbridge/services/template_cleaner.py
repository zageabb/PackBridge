from __future__ import annotations

import io
import os
import re
import tempfile
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

from .ssd_template import (
    MAIN_NS,
    PKG_REL_NS,
    REL_NS,
    REQUIRED_SHEETS,
    _normalise_target,
    inspect_template,
)


CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
HEADER_INPUT_CELLS = {
    "E9",   # currency
    "E12",  # supplier
    "E13",  # pickup address
    "E15",  # supplier contact
    "E16",  # supplier phone/email
    "E17",  # preliminary/final
    "M10",  # supplier reference
    "T6",   # BU details
    "T8",   # contact person and number
    "T9",   # other remarks
    "T12",  # project name
    "T13",  # delivery location
}


class TemplateCleaningError(ValueError):
    pass


def _q(tag: str) -> str:
    return f"{{{MAIN_NS}}}{tag}"


def _parse_xml(payload: bytes) -> ET.Element:
    # Preserve the workbook's namespace prefixes. This matters for mc:Ignorable,
    # whose attribute value names prefixes such as x15/xr rather than namespace URIs.
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


def _cell_row(ref: str) -> int | None:
    match = re.fullmatch(r"[A-Z]+(\d+)", ref)
    return int(match.group(1)) if match else None


def _cell_column(ref: str) -> str | None:
    match = re.fullmatch(r"([A-Z]+)\d+", ref)
    return match.group(1) if match else None


def _column_number(column: str) -> int:
    value = 0
    for character in column:
        value = value * 26 + (ord(character) - 64)
    return value


def _clear_cell_value(cell: ET.Element) -> None:
    if cell.find(_q("f")) is not None:
        return
    for child_name in ("v", "is"):
        child = cell.find(_q(child_name))
        if child is not None:
            cell.remove(child)
    cell.attrib.pop("t", None)


def _clean_socs_xml(
    payload: bytes,
    *,
    data_start_row: int,
    data_end_row: int,
) -> bytes:
    root = _parse_xml(payload)
    for cell in root.findall(".//" + _q("c")):
        ref = cell.attrib.get("r", "")
        if ref in HEADER_INPUT_CELLS:
            _clear_cell_value(cell)
            continue

        row = _cell_row(ref)
        column = _cell_column(ref)
        if row is None or column is None:
            continue
        column_number = _column_number(column)
        if data_start_row <= row <= data_end_row and 3 <= column_number <= 24:  # C:X
            _clear_cell_value(cell)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _relationship_map(root: ET.Element) -> dict[str, ET.Element]:
    return {
        item.attrib.get("Id", ""): item
        for item in root.findall(f"{{{PKG_REL_NS}}}Relationship")
    }


def _remove_content_type_overrides(
    payload: bytes,
    removed_parts: set[str],
    *,
    remove_calc_chain: bool,
) -> bytes:
    root = _parse_xml(payload)
    for node in list(root):
        part_name = node.attrib.get("PartName", "").lstrip("/")
        if part_name in removed_parts or (remove_calc_chain and part_name == "xl/calcChain.xml"):
            root.remove(node)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def create_clean_generation_template(
    source: str | Path,
    destination: str | Path,
) -> dict:
    """Create a clean XLSM/XLSX generation template from a populated compatible workbook.

    This is intentionally narrower than a general workbook editor. It retains only the
    three verified template worksheets, removes generated PL/ML sheets, clears user/
    package values from SoCs_Temp while retaining formulas/styles/validations, removes
    stale defined names and calc-chain data, and then re-inspects the result.
    """

    source = Path(source)
    destination = Path(destination)
    before = inspect_template(source)
    if not before.compatible:
        raise TemplateCleaningError(
            "Source workbook is not structurally compatible: "
            + "; ".join(before.errors[:8])
        )

    with zipfile.ZipFile(source, "r") as archive:
        names = set(archive.namelist())
        workbook_root = _parse_xml(archive.read("xl/workbook.xml"))
        rels_root = _parse_xml(archive.read("xl/_rels/workbook.xml.rels"))
        rel_by_id = _relationship_map(rels_root)

        sheets_node = workbook_root.find(_q("sheets"))
        if sheets_node is None:
            raise TemplateCleaningError("Workbook contains no sheets collection.")

        rel_key = f"{{{REL_NS}}}id"
        original_sheets = list(sheets_node)
        retained_old_to_new: dict[int, int] = {}
        removed_names: set[str] = set()
        removed_rids: set[str] = set()
        removed_parts: set[str] = set()
        retained_paths: dict[str, str] = {}

        new_index = 0
        for old_index, sheet in enumerate(original_sheets):
            name = sheet.attrib.get("name", "")
            rid = sheet.attrib.get(rel_key, "")
            relationship = rel_by_id.get(rid)
            target = relationship.attrib.get("Target", "") if relationship is not None else ""
            part = _normalise_target(target) if target else ""

            if name in REQUIRED_SHEETS:
                retained_old_to_new[old_index] = new_index
                new_index += 1
                retained_paths[name] = part
                continue

            removed_names.add(name)
            removed_rids.add(rid)
            if part:
                removed_parts.add(part)
            sheets_node.remove(sheet)

        missing = set(REQUIRED_SHEETS) - set(retained_paths)
        if missing:
            raise TemplateCleaningError(
                "Cannot build clean template; required worksheets are missing: "
                + ", ".join(sorted(missing))
            )

        # Reset active selection to SoCs_Temp so activeTab never points at a removed sheet.
        book_views = workbook_root.find(_q("bookViews"))
        if book_views is not None:
            for view in list(book_views):
                view.attrib["activeTab"] = "0"
                view.attrib["firstSheet"] = "0"

        # Remove/renumber sheet-local defined names. Global names explicitly pointing to
        # removed generated sheets are also removed.
        defined_names = workbook_root.find(_q("definedNames"))
        if defined_names is not None:
            for defined_name in list(defined_names):
                local = defined_name.attrib.get("localSheetId")
                remove = False
                if local is not None:
                    try:
                        old_index = int(local)
                    except ValueError:
                        remove = True
                    else:
                        if old_index not in retained_old_to_new:
                            remove = True
                        else:
                            defined_name.attrib["localSheetId"] = str(
                                retained_old_to_new[old_index]
                            )

                text = defined_name.text or ""
                if not remove and removed_names:
                    # Generated names are numeric and safe to search literally.
                    remove = any(
                        f"'{sheet_name}'!" in text or f"{sheet_name}!" in text
                        for sheet_name in removed_names
                    )
                if remove:
                    defined_names.remove(defined_name)

        # Force Excel to recalculate after stale calc-chain removal.
        calc_pr = workbook_root.find(_q("calcPr"))
        if calc_pr is None:
            calc_pr = ET.SubElement(workbook_root, _q("calcPr"))
        calc_pr.attrib["forceFullCalc"] = "1"
        calc_pr.attrib["fullCalcOnLoad"] = "1"
        calc_pr.attrib["calcMode"] = "auto"

        # Remove workbook relationships to generated sheets and calcChain.
        remove_calc_chain = "xl/calcChain.xml" in names
        for relationship in list(rels_root):
            rid = relationship.attrib.get("Id", "")
            rel_type = relationship.attrib.get("Type", "")
            target = relationship.attrib.get("Target", "")
            if rid in removed_rids or rel_type.endswith("/calcChain") or target.endswith("calcChain.xml"):
                rels_root.remove(relationship)

        workbook_xml = ET.tostring(
            workbook_root, encoding="utf-8", xml_declaration=True
        )
        workbook_rels_xml = ET.tostring(
            rels_root, encoding="utf-8", xml_declaration=True
        )
        socs_path = retained_paths["SoCs_Temp"]
        cleaned_socs = _clean_socs_xml(
            archive.read(socs_path),
            data_start_row=before.data_start_row or 23,
            data_end_row=before.data_end_row or 90,
        )

        # Remove sheet-specific rel files for generated sheets as well.
        removed_sheet_rel_parts = {
            "xl/worksheets/_rels/" + Path(part).name + ".rels"
            for part in removed_parts
            if part.startswith("xl/worksheets/")
        }
        skip_parts = set(removed_parts) | removed_sheet_rel_parts
        if remove_calc_chain:
            skip_parts.add("xl/calcChain.xml")

        content_types = _remove_content_type_overrides(
            archive.read("[Content_Types].xml"),
            removed_parts,
            remove_calc_chain=remove_calc_chain,
        )

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            suffix=destination.suffix,
            dir=destination.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)

        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as output:
                for item in archive.infolist():
                    name = item.filename
                    if name in skip_parts:
                        continue
                    if name == "xl/workbook.xml":
                        output.writestr(item, workbook_xml)
                    elif name == "xl/_rels/workbook.xml.rels":
                        output.writestr(item, workbook_rels_xml)
                    elif name == socs_path:
                        output.writestr(item, cleaned_socs)
                    elif name == "[Content_Types].xml":
                        output.writestr(item, content_types)
                    else:
                        output.writestr(item, archive.read(name))

            after = inspect_template(temporary)
            if not after.compatible:
                raise TemplateCleaningError(
                    "Cleaned template failed structural validation: "
                    + "; ".join(after.errors[:8])
                )
            if not after.generation_ready:
                raise TemplateCleaningError(
                    "Cleaned template is structurally compatible but is not generation-ready: "
                    + "; ".join(after.warnings[:8])
                )

            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    return {
        "source": before.to_dict(),
        "cleaned": inspect_template(destination).to_dict(),
        "destination": str(destination),
        "removed_sheet_count": before.generated_pl_count + before.generated_ml_count,
    }
