from packbridge.assistant_schemas import AssistantDataQuery
from packbridge.schemas import (
    FieldValue,
    MappingIssue,
    Package,
    PackingList,
    SourceValue,
    WorkingValue,
)
from packbridge.services.assistant_data import (
    execute_data_queries,
    format_data_results,
)


def field(value, unit=None):
    return FieldValue(
        source=SourceValue(value=value, unit=unit),
        working=WorkingValue(value=value, unit=unit, origin="source"),
    )


def test_filter_packages_is_deterministic_and_unit_aware():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("C-1"),
                gross_weight=field(1600, "KG"),
                net_weight=field(1400, "KG"),
            ),
            Package(
                case_number=field("C-2"),
                gross_weight=field(1200, "KG"),
                net_weight=field(1000, "KG"),
            ),
            Package(
                case_number=field("C-3"),
                gross_weight=field(4000, "LB"),
                net_weight=field(3500, "LB"),
            ),
        ]
    )
    query = AssistantDataQuery(
        operation="filter_packages",
        field="gross_weight",
        comparator="gt",
        value=1500,
        unit="KG",
    )

    result = execute_data_queries(packing, [query])[0]

    assert [item["case_number"] for item in result["matches"]] == ["C-1"]
    assert result["skipped_units"] == ["LB"]
    assert "C-1" in format_data_results([result])


def test_sum_groups_mixed_units_instead_of_converting_or_combining():
    packing = PackingList(
        packages=[
            Package(
                case_number=field("C-1"),
                gross_weight=field(100, "KG"),
                net_weight=field(90, "KG"),
            ),
            Package(
                case_number=field("C-2"),
                gross_weight=field(200, "LB"),
                net_weight=field(180, "LB"),
            ),
        ]
    )

    result = execute_data_queries(
        packing,
        [AssistantDataQuery(operation="sum_package_field", field="gross_weight")],
    )[0]

    assert result["totals_by_unit"] == {"KG": 100.0, "LB": 200.0}


def test_issue_and_modified_field_queries_use_current_working_data():
    changed = field(10, "KG")
    changed.working = WorkingValue(
        value=12,
        unit="KG",
        origin="user_edit",
        modified_by="user",
    )
    changed.modified = True

    packing = PackingList(
        packages=[
            Package(
                case_number=field("C-1"),
                gross_weight=changed,
                net_weight=field(9, "KG"),
            )
        ],
        issues=[
            MappingIssue(
                code="TEST_WARNING",
                severity="WARNING",
                message="Needs review",
                case_number="C-1",
            )
        ],
    )

    results = execute_data_queries(
        packing,
        [
            AssistantDataQuery(operation="list_modified_fields"),
            AssistantDataQuery(operation="list_issues", severity="WARNING"),
        ],
    )

    assert results[0]["fields"][0]["path"] == "packages[0].gross_weight"
    assert results[1]["issues"][0]["code"] == "TEST_WARNING"
