import zipfile
import xml.etree.ElementTree as ET

from packbridge.services.ssd_template import inspect_template
from packbridge.services.template_cleaner import create_clean_generation_template


MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def inline_cell(ref, text):
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def make_populated_template(path):
    headers = {
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
    cells = "".join(inline_cell(ref, value) for ref, value in headers.items())
    cells += inline_cell("E12", "Supplier A")
    cells += inline_cell("D23", "QBANK")
    cells += inline_cell("S23", "CASE-1")
    cells += '<c r="M23"><f>J23*K23*L23/1000000</f><v>1.0</v></c>'

    validations = "".join(
        f'<dataValidation type="list" sqref="{ref}"><formula1>"x"</formula1></dataValidation>'
        for ref in ("G23:G90", "R23:R90", "T23:T90", "U23:U90", "V23:V90")
    )
    validations += '<dataValidation type="decimal" operator="greaterThanOrEqual" sqref="O23:O90"><formula1>N23</formula1></dataValidation>'

    workbook = f'''<?xml version="1.0" encoding="UTF-8"?>
    <workbook xmlns="{MAIN}" xmlns:r="{REL}">
      <bookViews><workbookView activeTab="4"/></bookViews>
      <sheets>
        <sheet name="SoCs_Temp" sheetId="1" r:id="rId1"/>
        <sheet name="PLs_Temp" sheetId="3" state="veryHidden" r:id="rId2"/>
        <sheet name="PL-CASE-1" sheetId="10" r:id="rId3"/>
        <sheet name="MLs_Temp" sheetId="2" state="veryHidden" r:id="rId4"/>
        <sheet name="ML-CASE-1" sheetId="11" r:id="rId5"/>
      </sheets>
      <definedNames>
        <definedName name="_xlnm.Print_Area" localSheetId="2">'PL-CASE-1'!$A$1:$E$20</definedName>
        <definedName name="_xlnm.Print_Area" localSheetId="3">'MLs_Temp'!$A$1:$E$41</definedName>
      </definedNames>
      <calcPr calcId="1"/>
    </workbook>'''
    rels = f'''<?xml version="1.0" encoding="UTF-8"?>
    <Relationships xmlns="{PKG}">
      <Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>
      <Relationship Id="rId2" Type="worksheet" Target="worksheets/sheet2.xml"/>
      <Relationship Id="rId3" Type="worksheet" Target="worksheets/sheet3.xml"/>
      <Relationship Id="rId4" Type="worksheet" Target="worksheets/sheet4.xml"/>
      <Relationship Id="rId5" Type="worksheet" Target="worksheets/sheet5.xml"/>
      <Relationship Id="rIdCalc" Type="calcChain" Target="calcChain.xml"/>
    </Relationships>'''
    sheet1 = f'''<?xml version="1.0" encoding="UTF-8"?>
    <worksheet xmlns="{MAIN}">
      <sheetData><row r="21">{cells}</row></sheetData>
      <dataValidations count="6">{validations}</dataValidations>
    </worksheet>'''
    empty = f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="{MAIN}"><sheetData/></worksheet>'
    table = f'''<?xml version="1.0" encoding="UTF-8"?>
    <table xmlns="{MAIN}" id="2" name="Table2" displayName="Table2" ref="C22:W90" totalsRowShown="0">
      <tableColumns count="1"><tableColumn id="1" name="(Always 1)"/></tableColumns>
    </table>'''
    calc_chain = f'<?xml version="1.0" encoding="UTF-8"?><calcChain xmlns="{MAIN}"><c r="M23" i="1"/></calcChain>'
    content_types = f'''<?xml version="1.0" encoding="UTF-8"?>
    <Types xmlns="{CT}">
      <Default Extension="xml" ContentType="application/xml"/>
      <Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/>
      <Override PartName="/xl/workbook.xml" ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/>
      <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
      <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
      <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
      <Override PartName="/xl/worksheets/sheet4.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
      <Override PartName="/xl/worksheets/sheet5.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
      <Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>
      <Override PartName="/xl/calcChain.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml"/>
    </Types>'''

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet1)
        archive.writestr("xl/worksheets/sheet2.xml", empty)
        archive.writestr("xl/worksheets/sheet3.xml", empty)
        archive.writestr("xl/worksheets/sheet4.xml", empty)
        archive.writestr("xl/worksheets/sheet5.xml", empty)
        archive.writestr("xl/tables/table1.xml", table)
        archive.writestr("xl/calcChain.xml", calc_chain)
        archive.writestr("xl/vbaProject.bin", b"fake-vba")


def test_cleaner_removes_generated_sheets_and_case_values(tmp_path):
    source = tmp_path / "populated.xlsm"
    destination = tmp_path / "clean.xlsm"
    make_populated_template(source)

    before = inspect_template(source)
    assert before.compatible is True
    assert before.generation_ready is False
    assert before.generated_pl_count == 1
    assert before.generated_ml_count == 1
    assert before.existing_case_count == 1

    result = create_clean_generation_template(source, destination)
    after = inspect_template(destination)

    assert result["removed_sheet_count"] == 2
    assert after.compatible is True
    assert after.generation_ready is True
    assert after.generated_pl_count == 0
    assert after.generated_ml_count == 0
    assert after.existing_case_count == 0
    assert after.has_vba is True

    with zipfile.ZipFile(destination) as archive:
        assert "xl/worksheets/sheet3.xml" not in archive.namelist()
        assert "xl/worksheets/sheet5.xml" not in archive.namelist()
        assert "xl/calcChain.xml" not in archive.namelist()

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        ns = {"m": MAIN}
        sheet_names = [
            node.attrib["name"] for node in workbook.find("m:sheets", ns)
        ]
        assert sheet_names == ["SoCs_Temp", "PLs_Temp", "MLs_Temp"]

        defined = workbook.find("m:definedNames", ns)
        names = list(defined) if defined is not None else []
        assert len(names) == 1
        assert names[0].attrib["localSheetId"] == "2"

        socs = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        values = {}
        for cell in socs.findall(".//m:c", ns):
            ref = cell.attrib.get("r")
            inline = cell.find("m:is/m:t", ns)
            formula = cell.find("m:f", ns)
            values[ref] = {
                "inline": inline.text if inline is not None else None,
                "formula": formula.text if formula is not None else None,
            }
        assert values["E12"]["inline"] is None
        assert values["S23"]["inline"] is None
        assert values["M23"]["formula"] == "J23*K23*L23/1000000"
