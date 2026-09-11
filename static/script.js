const input = document.getElementById("images");
const preview = document.getElementById("preview");

let files = [];
let rotations = [];
let flips = [];
let grayscale = [];

input.addEventListener("change", function() {
    files = Array.from(input.files);
    rotations = files.map(function() { return 0; });
    flips = files.map(function() { return false; });
    grayscale = files.map(function() { return false; });
    showPreview();
});

function showPreview() {
    preview.innerHTML = "";

    files.forEach(function(file, index) {
        const box = document.createElement("div");
        box.className = "preview-item";

        const img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        img.className = "preview-image";
        img.style.transform =
            "rotate(" + rotations[index] + "deg) scaleX(" +
            (flips[index] ? -1 : 1) + ")";

        if (grayscale[index]) {
            img.style.filter = "grayscale(100%)";
        }

        const number = document.createElement("span");
        number.className = "image-number";
        number.textContent = index + 1;

        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "X";
        remove.className = "remove-btn";
        remove.onclick = function() {
            files.splice(index, 1);
            rotations.splice(index, 1);
            flips.splice(index, 1);
            grayscale.splice(index, 1);
            showPreview();
        };

        const rotate = document.createElement("button");
        rotate.type = "button";
        rotate.textContent = "↻";
        rotate.className = "rotate-btn";
        rotate.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            rotations[index] = (rotations[index] + 90) % 360;
            showPreview();
        };

        const flip = document.createElement("button");
        flip.type = "button";
        flip.textContent = "↔";
        flip.className = "flip-btn";
        flip.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            flips[index] = !flips[index];
            showPreview();
        };

        const gray = document.createElement("button");
        gray.type = "button";
        gray.textContent = "G";
        gray.className = "gray-btn";
        gray.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            grayscale[index] = !grayscale[index];
            showPreview();
        };

        box.appendChild(number);
        box.appendChild(img);
        box.appendChild(remove);
        box.appendChild(flip);
        box.appendChild(rotate);
        box.appendChild(gray);

        preview.appendChild(box);
    });

    updateInput();
}

function updateInput() {
    const dt = new DataTransfer();

    files.forEach(function(file) {
        dt.items.add(file);
    });

    input.files = dt.files;

    const rotationInput = document.getElementById("rotations");
    if (rotationInput) {
        rotationInput.value = JSON.stringify(rotations);
    }
}
