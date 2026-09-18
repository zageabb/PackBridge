from __future__ import annotations

from dataclasses import dataclass

from packbridge.schemas import PackingList
from packbridge.ssd_schemas import SSDContext, SSDPreview
from packbridge.services.ssd_preview import build_ssd_preview


@dataclass(frozen=True)
class AggregationInput:
    job_id: int
    job_title: str
    packing: PackingList


def build_project_preview(
    inputs: list[AggregationInput],
    context: SSDContext | None = None,
) -> SSDPreview:
    """Combine mapped packing-list jobs into one SoCs preview.

    Each source job keeps its own canonical purchase-order context while project-level
    SSD defaults/header values are shared across the resulting workbook preview.
    """
    context = context or SSDContext()
    output = SSDPreview()

    if not inputs:
        output.blocking.append("No mapped packing-list jobs are attached to this SSD project.")
        return output

    total_packages = sum(len(item.packing.packages) for item in inputs)
    if total_packages > 68:
        output.blocking.append(
            f"Current template supports 68 package rows; the project contains {total_packages}."
        )

    seen_cases: dict[str, int] = {}
    global_index = 0

    for input_item in inputs:
        preview = build_ssd_preview(input_item.packing, context)
        if not output.header_cells:
            output.header_cells = preview.header_cells

        # build_ssd_preview emits a per-job 68-row capacity warning; the project owns
        # the aggregate capacity check, so only keep other diagnostics here.
        for message in preview.blocking:
            if not message.startswith("Current template supports 68 package rows;"):
                output.blocking.append(f"{input_item.job_title}: {message}")
        for message in preview.warnings:
            output.warnings.append(f"{input_item.job_title}: {message}")

        for row in preview.rows:
            row.package_index = global_index
            row.excel_row = 23 + global_index if global_index < 68 else None
            row.source_job_id = input_item.job_id
            row.source_job_title = input_item.job_title

            if row.case_number:
                previous_job = seen_cases.get(row.case_number)
                if previous_job is not None:
                    output.blocking.append(
                        f"Case {row.case_number} appears in more than one attached job "
                        f"(jobs {previous_job} and {input_item.job_id})."
                    )
                else:
                    seen_cases[row.case_number] = input_item.job_id

            output.rows.append(row)
            global_index += 1

    # Avoid making repeated shared-header warnings noisy when several jobs use the
    # same project context.
    output.warnings = list(dict.fromkeys(output.warnings))
    output.blocking = list(dict.fromkeys(output.blocking))
    return output
