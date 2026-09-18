from packbridge.mapper_schemas import MappedPackage, MappedValue, MapperResult
from packbridge.services.normalise import to_packing_list


def value(raw, unit=None, locator="Page 1"):
    return MappedValue(
        value=raw,
        unit=unit,
        raw=str(raw),
        locator=locator,
        status="CONFIRMED",
    )


def test_mapper_result_becomes_source_and_working_values():
    mapped = MapperResult(
        vendor="Example Vendor",
        packages=[
            MappedPackage(
                case_number=value("CASE-1"),
                gross_weight=value(830, "KG"),
                net_weight=value(643, "KG"),
            )
        ],
    )

    packing = to_packing_list(mapped)

    package = packing.packages[0]
    assert package.case_number.source.value == "CASE-1"
    assert package.case_number.working.value == "CASE-1"
    assert package.gross_weight.source.value == 830
    assert package.gross_weight.working.value == 830
    assert package.gross_weight.working.origin == "source"
    assert package.gross_weight.modified is False
    assert package.gross_weight.source.evidence[0].locator == "Page 1"
