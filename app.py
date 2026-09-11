from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image, ImageOps, ImageEnhance
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, LETTER, LEGAL
from reportlab.lib.utils import ImageReader
from io import BytesIO
from datetime import datetime
import base64, io, os, re

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

PAGE_SIZES = {
    "A4": A4,
    "A3": A3,
    "Letter": LETTER,
    "Legal": LEGAL,
}

def parse_data_url(data_url):
    if not data_url or "," not in data_url:
        raise ValueError("Invalid image data")
    header, encoded = data_url.split(",", 1)
    raw = base64.b64decode(encoded)
    return Image.open(BytesIO(raw)).convert("RGB")

def fit_rect(img_w, img_h, box_w, box_h, mode):
    if mode == "fill":
        scale = max(box_w / img_w, box_h / img_h)
    elif mode == "original":
        scale = min(1, min(box_w / img_w, box_h / img_h))
    else:
        scale = min(box_w / img_w, box_h / img_h)
    return img_w * scale, img_h * scale, scale

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/convert", methods=["POST"])
def convert():
    try:
        images = request.form.getlist("images")
        if not images:
            return jsonify(error="No images selected"), 400

        page_name = request.form.get("page_size", "A4")
        orientation = request.form.get("orientation", "portrait")
        fit_mode = request.form.get("fit_mode", "fit")
        margin = max(0, min(float(request.form.get("margin", 30)), 150))
        per_page = max(1, min(int(request.form.get("per_page", 1)), 4))
        quality = request.form.get("quality", "medium")
        title = request.form.get("title", "").strip()
        header = request.form.get("header", "").strip()
        footer = request.form.get("footer", "").strip()
        watermark = request.form.get("watermark", "").strip()
        page_numbers = request.form.get("page_numbers") == "1"
        password = request.form.get("password", "")
        filename = request.form.get("filename", "images.pdf").strip()
        filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename) or "images.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        size = PAGE_SIZES.get(page_name, A4)
        if orientation == "landscape":
            page_w, page_h = size[1], size[0]
        else:
            page_w, page_h = size

        if per_page == 1:
            cols, rows = 1, 1
        elif per_page == 2:
            cols, rows = 2, 1
        else:
            cols, rows = 2, 2

        usable_w = page_w - 2 * margin
        usable_h = page_h - 2 * margin
        cell_w = usable_w / cols
        cell_h = usable_h / rows

        pdf = BytesIO()
        pdf_canvas = canvas.Canvas(pdf, pagesize=(page_w, page_h))
        if title:
            pdf_canvas.setTitle(title)
        if password:
            pdf_canvas.setEncrypt(password)

        prepared = []
        for data in images:
            img = parse_data_url(data)
            # Server-side safety cap while preserving aspect ratio.
            max_dim = {"low": 1400, "medium": 2000, "high": 2800}.get(quality, 2000)
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            q = {"low": 55, "medium": 75, "high": 90}.get(quality, 75)
            buf = BytesIO()
            img.save(buf, "JPEG", quality=q, optimize=True)
            buf.seek(0)
            prepared.append((buf, img.size))

        total = len(prepared)
        for index, (buf, dims) in enumerate(prepared):
            slot = index % per_page
            if slot == 0 and index != 0:
                draw_page_extras(pdf_canvas, page_w, page_h, header, footer, index // per_page, watermark)
                pdf_canvas.showPage()

            col = slot % cols
            row = slot // cols
            x0 = margin + col * cell_w
            y0 = page_h - margin - (row + 1) * cell_h

            iw, ih = dims
            dw, dh, scale = fit_rect(iw, ih, cell_w, cell_h, fit_mode)

            if fit_mode == "fill":
                # Center-crop by using a temporary canvas-sized crop.
                img = Image.open(buf).convert("RGB")
                target_ratio = cell_w / cell_h
                ratio = img.width / img.height
                if ratio > target_ratio:
                    new_w = int(img.height * target_ratio)
                    left = (img.width - new_w) // 2
                    img = img.crop((left, 0, left + new_w, img.height))
                else:
                    new_h = int(img.width / target_ratio)
                    top = (img.height - new_h) // 2
                    img = img.crop((0, top, img.width, top + new_h))
                buf2 = BytesIO()
                img.save(buf2, "JPEG", quality={"low":55,"medium":75,"high":90}.get(quality,75), optimize=True)
                buf2.seek(0)
                draw_x, draw_y, draw_w, draw_h = x0, y0, cell_w, cell_h
                pdf_canvas.drawImage(ImageReader(buf2), draw_x, draw_y, width=draw_w, height=draw_h, preserveAspectRatio=False, mask="auto")
            else:
                draw_x = x0 + (cell_w - dw) / 2
                draw_y = y0 + (cell_h - dh) / 2
                pdf_canvas.drawImage(ImageReader(buf), draw_x, draw_y, width=dw, height=dh, preserveAspectRatio=True, mask="auto")

            if per_page > 1:
                pdf_canvas.setFillColorRGB(0.75, 0.75, 0.75)
                pdf_canvas.rect(x0, y0, cell_w, cell_h, stroke=1, fill=0)

        if prepared:
            draw_page_extras(pdf_canvas, page_w, page_h, header, footer, (len(prepared)-1)//per_page + 1, watermark)
            pdf_canvas.showPage()

        pdf_canvas.save()
        pdf.seek(0)
        return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=filename)
    except Exception as exc:
        return jsonify(error=str(exc)), 500

def draw_page_extras(c, page_w, page_h, header, footer, page_number, watermark):
    if header:
        c.setFillColorRGB(0.25, 0.25, 0.25)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(18, page_h - 14, header[:120])
    if watermark:
        c.saveState()
        c.setFillAlpha(0.16)
        c.setFont("Helvetica-Bold", min(52, max(24, page_w / 8)))
        c.translate(page_w / 2, page_h / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, watermark[:40])
        c.restoreState()
    if footer:
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.setFont("Helvetica", 9)
        c.drawCentredString(page_w / 2, 12, footer[:120])
    if page_number:
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.setFont("Helvetica", 9)
        c.drawRightString(page_w - 18, 12, f"Page {page_number}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
