import zipfile

from packbridge.services.ssd_template import inspect_template


MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def inline_cell(ref, text):
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def make_template(path, *, wrong_header=False, with_vba=True):
    headers = {
        "C21": "Qty",
        "D21": "Wrong" if wrong_header else "Content Description / Equipment (Name)",
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
    cells = "".join(inline_cell(ref, value) for ref, value in headers.items())
    validations = "".join(
        f'<dataValidation type="list" sqref="{ref}"><formula1>"x"</formula1></dataValidation>'
        for ref in ("G23:G90", "R23:R90", "T23:T90", "U23:U90", "V23:V90")
    )
    validations += '<dataValidation type="decimal" operator="greaterThanOrEqual" sqref="O23:O90"><formula1>N23</formula1></dataValidation>'

    workbook = f'''<?xml version="1.0" encoding="UTF-8"?>
    <workbook xmlns="{MAIN}" xmlns:r="{REL}">
      <sheets>
        <sheet name="SoCs_Temp" sheetId="1" r:id="rId1"/>
        <sheet name="PLs_Temp" sheetId="2" state="veryHidden" r:id="rId2"/>
        <sheet name="MLs_Temp" sheetId="3" state="veryHidden" r:id="rId3"/>
      </sheets>
    </workbook>'''
    rels = f'''<?xml version="1.0" encoding="UTF-8"?>
    <Relationships xmlns="{PKG}">
      <Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>
      <Relationship Id="rId2" Type="worksheet" Target="worksheets/sheet2.xml"/>
      <Relationship Id="rId3" Type="worksheet" Target="worksheets/sheet3.xml"/>
    </Relationships>'''
    sheet1 = f'''<?xml version="1.0" encoding="UTF-8"?>
    <worksheet xmlns="{MAIN}">
      <sheetData><row r="21">{cells}</row></sheetData>
      <dataValidations count="6">{validations}</dataValidations>
    </worksheet>'''
    empty_sheet = f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="{MAIN}"><sheetData/></worksheet>'
    table = f'''<?xml version="1.0" encoding="UTF-8"?>
    <table xmlns="{MAIN}" id="2" name="Table2" displayName="Table2" ref="C22:W90" totalsRowShown="0">
      <tableColumns count="1"><tableColumn id="1" name="(Always 1)"/></tableColumns>
    </table>'''

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet1)
        archive.writestr("xl/worksheets/sheet2.xml", empty_sheet)
        archive.writestr("xl/worksheets/sheet3.xml", empty_sheet)
        archive.writestr("xl/tables/table1.xml", table)
        if with_vba:
            archive.writestr("xl/vbaProject.bin", b"fake-vba")


def test_reference_shape_is_accepted(tmp_path):
    path = tmp_path / "template.xlsm"
    make_template(path)

    result = inspect_template(path)

    assert result.compatible is True
    assert result.has_vba is True
    assert result.workbook_type == "xlsm"
    assert result.sheets["PLs_Temp"] == "veryHidden"
    assert result.structural_fingerprint


def test_wrong_socs_header_is_rejected(tmp_path):
    path = tmp_path / "template.xlsm"
    make_template(path, wrong_header=True)

    result = inspect_template(path)

    assert result.compatible is False
    assert any("D21" in error for error in result.errors)


def test_macro_free_shape_warns_but_can_be_structurally_compatible(tmp_path):
    path = tmp_path / "template.xlsx"
    make_template(path, with_vba=False)

    result = inspect_template(path)

    assert result.compatible is True
    assert result.has_vba is False
    assert any("no VBA" in warning for warning in result.warnings)
