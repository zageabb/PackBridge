# PackBridge Document Profile Learning

You are preparing a REVIEW-ONLY draft document profile for PackBridge from a packing list that was already processed by the generic local mapper.

Return only the requested structured schema.

Rules:

1. Use source terminology that is explicitly supported by the supplied source excerpts.
2. Map a source term to a canonical field only where the current mapped dataset/evidence supports that relationship.
3. Do not invent supplier defaults, countries, dangerous-goods values, project values, PO values, stackability or other shipment-specific facts.
4. Recognition indicators should be stable headings/labels likely to identify this document family, not shipment-specific numbers or case numbers.
5. Prefer 4–12 useful recognition indicators.
6. Field aliases should represent terminology, not one-off field values.
7. If the source shows that repeated pages with the same case/package identifier are continuation pages, set continuation_key to the appropriate canonical field; otherwise return null.
8. Interpretation notes should explain layout/terminology behaviour only.
9. The result is a proposed Knowledge profile and will require human approval before becoming active.

CURRENT MAPPED DATA:
{{mapped_data}}

SOURCE EXCERPTS:
{{source_text}}
