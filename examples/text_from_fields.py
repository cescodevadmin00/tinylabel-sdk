"""External, already formatted fields -> text labels -> preview only. No Excel reader."""
from tinylabel_sdk import (Media, TextBlock, TextLabel, TextStyle,
                           format_text, prepare_text_batch)

# Your project reads Excel/database/API and formats strings before this boundary.
# Preserve leading zeros and choose date/decimal/currency formatting there.
rows = [
    {"id": "item-001", "product": "Café molido", "price": "USD 7,82", "lot": "0017"},
    {"id": "item-002", "product": "Arroz integral", "price": "USD 5,83", "lot": "0018"},
]

labels = [
    TextLabel(row["id"], blocks=(
        TextBlock(row["product"], TextStyle(font_size_mm=4, bold=True), gap_after_mm=0.75),
        TextBlock(format_text("{price}\nLote: {lot}", row), TextStyle(font_size_mm=3, align="left")),
    ))
    for row in rows
]
plan = prepare_text_batch(labels, Media(50, 25, 2))
plan.save_previews("preview-text")
print(plan.summary())

# For an authorized print, use the SAME LabelPrinter workflow as image plans:
# printer.confirm_alignment(plan.media, calibration=plan.calibration)
# receipt = await printer.print_batch(plan, job_id=stable_business_job_id)
# Receipt remains transmitted_unconfirmed until the physical output is checked.
