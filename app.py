from flask import Flask, render_template, request, send_file
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/convert", methods=["POST"])
def convert():
    files = request.files.getlist("images")

    if not files or files[0].filename == "":
        return "No images selected", 400

    pdf = BytesIO()
    pdf_canvas = canvas.Canvas(pdf, pagesize=A4)

    page_width, page_height = A4
    margin = 30

    for file in files:
        image = Image.open(file.stream).convert("RGB")

        img_width, img_height = image.size

        max_width = page_width - (2 * margin)
        max_height = page_height - (2 * margin)

        scale = min(max_width / img_width, max_height / img_height)

        new_width = img_width * scale
        new_height = img_height * scale

        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2

        image_buffer = BytesIO()
        image.save(image_buffer, format="JPEG")
        image_buffer.seek(0)

        from reportlab.lib.utils import ImageReader
        pdf_canvas.drawImage(
            ImageReader(image_buffer),
            x, y,
            width=new_width,
            height=new_height
        )

        pdf_canvas.showPage()

    pdf_canvas.save()
    pdf.seek(0)

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="images.pdf"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
