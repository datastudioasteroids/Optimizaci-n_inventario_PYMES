// static/js/upload.js

const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("csvFileInput");
const status    = document.getElementById("uploadStatus");
const actions   = document.getElementById("actions");

// Solo habilitamos el botón si hay archivo seleccionado
fileInput.addEventListener("change", () => {
  uploadBtn.disabled = !fileInput.files.length;
});

uploadBtn.addEventListener("click", async () => {
  if (!fileInput.files.length) return;
  status.textContent = "Subiendo CSV…";
  const form = new FormData();
  form.append("file", fileInput.files[0]);

  try {
    // 1) Llamar a upload_csv
    let resp = await fetch("/upload_csv", {
      method: "POST",
      body: form
    });
    if (!resp.ok) {
      throw new Error(`upload_csv: ${resp.status}`);
    }
    status.textContent = "CSV subido. Entrenando modelos…";

    // 2) Llamar a train_xgb
    resp = await fetch("/train_xgb", { method: "POST" });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `train_xgb: ${resp.status}`);
    }

    // 3) Indicar éxito y mostrar el dashboard
    status.innerHTML = "✅ Modelos entrenados.";
    actions.style.display = "";

    // 4) Disparar evento para que app.js/HTML reaccionen
    document.dispatchEvent(new Event("modelsTrained"));

  } catch (err) {
    console.error("Error en upload.js:", err);
    status.textContent = `❌ ${err.message}`;
  }
});
