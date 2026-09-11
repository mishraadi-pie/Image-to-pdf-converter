const input = document.getElementById("images");
const preview = document.getElementById("preview");

input.addEventListener("change", function () {
    preview.innerHTML = "";

    for (const file of input.files) {
        const img = document.createElement("img");

        img.src = URL.createObjectURL(file);
        img.className = "preview-image";

        preview.appendChild(img);
    }
});
