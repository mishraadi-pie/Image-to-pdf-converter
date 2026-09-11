from flask import Flask, render_template, request, send_file
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, LETTER, LEGAL
from reportlab.lib.utils import ImageReader
from io import BytesIO
import json
import os
import uuid

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

PAGE_SIZES = {
    "A4": A4,
    "A3": A3,
    "LETTER": LETTER,
    "LEGAL": LEGAL
}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():

    files = request.files.getlist("images")

    if not files:
        return "No images selected", 400

    settings = json.loads(request.form.get("settings", "{}"))

    page_size_name = settings.get("pageSize", "A4")
    orientation = settings.get("orientation", "portrait")
    fit_mode = settings.get("fit", "fit")
    per_page = int(settings.get("perPage", 1))
    margin = float(settings.get("margin", 30))
    quality = int(settings.get("quality", 85))
    page_numbers = settings.get("pageNumbers", False)
    watermark = settings.get("watermark", "")

    page_width, page_height = PAGE_SIZES.get(
        page_size_name, A4
    )

    if orientation == "landscape":
        page_width, page_height = page_height, page_width

    pdf = BytesIO()

    pdf_canvas = canvas.Canvas(
        pdf,
        pagesize=(page_width, page_height)
    )

    usable_width = page_width - (2 * margin)
    usable_height = page_height - (2 * margin)

    page_count = 0

    for start in range(0, len(files), per_page):

        current_files = files[start:start + per_page]

        for position, file in enumerate(current_files):

            try:
                image = Image.open(file.stream).convert("RGB")
            except Exception:
                continue

            # Image is already edited by frontend.
            # Apply server-side optimization.
            max_dimension = 2500

            if max(image.size) > max_dimension:
                image.thumbnail(
                    (max_dimension, max_dimension),
                    Image.Resampling.LANCZOS
                )

            image_buffer = BytesIO()

            image.save(
                image_buffer,
                format="JPEG",
                quality=quality,
                optimize=True
            )

            image_buffer.seek(0)

            img_width, img_height = image.size

            if fit_mode == "original":
                draw_width = img_width
                draw_height = img_height

                scale = min(
                    usable_width / draw_width,
                    usable_height / draw_height,
                    1
                )

                draw_width *= scale
                draw_height *= scale

            elif fit_mode == "fill":

                scale = max(
                    usable_width / img_width,
                    usable_height / img_height
                )

                draw_width = img_width * scale
                draw_height = img_height * scale

            else:

                scale = min(
                    usable_width / img_width,
                    usable_height / img_height
                )

                draw_width = img_width * scale
                draw_height = img_height * scale

            if per_page == 1:

                x = margin + (
                    usable_width - draw_width
                ) / 2

                y = margin + (
                    usable_height - draw_height
                ) / 2

            else:

                rows = 1 if per_page <= 2 else 2
                cols = 2 if per_page > 1 else 1

                cell_width = usable_width / cols
                cell_height = usable_height / rows

                col = position % cols
                row = position // cols

                cell_x = margin + col * cell_width
                cell_y = page_height - margin - (row + 1) * cell_height

                scale = min(
                    (cell_width - 10) / img_width,
                    (cell_height - 10) / img_height
                )

                draw_width = img_width * scale
                draw_height = img_height * scale

                x = cell_x + (
                    cell_width - draw_width
                ) / 2

                y = cell_y + (
                    cell_height - draw_height
                ) / 2

            pdf_canvas.drawImage(
                ImageReader(image_buffer),
                x,
                y,
                width=draw_width,
                height=draw_height,
                preserveAspectRatio=True,
                mask="auto"
            )

        page_count += 1

        if watermark:
            pdf_canvas.setFont("Helvetica", 20)
            pdf_canvas.setFillAlpha(0.25)
            pdf_canvas.drawCentredString(
                page_width / 2,
                page_height / 2,
                watermark
            )
            pdf_canvas.setFillAlpha(1)

        if page_numbers:
            pdf_canvas.setFont("Helvetica", 9)
            pdf_canvas.drawCentredString(
                page_width / 2,
                15,
                f"Page {page_count}"
            )

        pdf_canvas.showPage()

    pdf_canvas.save()
    pdf.seek(0)

    filename = settings.get(
        "filename",
        "images"
    ).strip()

    if not filename:
        filename = "images"

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )	
