// app.js
// Archivo principal que orquesta la carga de los módulos frontend.
// Se ejecuta una sola vez al cargar la página y se encarga de inyectar
// dinámicamente upload.js, metrics.js y dashboard.js.
// Además expone initPredictionByFields() para poblar y manejar el formulario.

console.log('Demo Sales Forecasting cargado');

document.addEventListener('DOMContentLoaded', () => {
  const scripts = [
    '/static/js/upload.js',
    '/static/js/metrics.js',
    '/static/js/dashboard.js'
  ];

  // Función para cargar un <script> dinámicamente
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.async = false;       // respetar orden
      s.onload = () => {
        console.log(`Módulo cargado: ${src}`);
        resolve();
      };
      s.onerror = () => reject(new Error(`Error cargando ${src}`));
      document.body.appendChild(s);
    });
  }

  // Cargar todos los scripts en secuencia
  (async () => {
    try {
      for (const src of scripts) {
        await loadScript(src);
      }
      console.log('Todos los módulos frontend han sido cargados.');
      // NOTA: No iniciamos initPredictionByFields aquí,
      // lo llamaremos desde upload.js después de subir el CSV.
    } catch (err) {
      console.error('Error cargando módulos frontend:', err);
    }
  })();
});

// Esta función se debe llamar tras un POST /upload_csv exitoso.
// Por ejemplo, al final de upload.js:
//   if (response.ok) { window.initPredictionByFields(); }
async function initPredictionByFields() {
  const regionSel  = document.getElementById("region");
  const productSel = document.getElementById("product");
  const subcatSel  = document.getElementById("subcat");
  const dateInput  = document.getElementById("date");
  const modelSel   = document.getElementById("model-select");
  const resultDiv  = document.getElementById("prediction-result");
  const errorDiv   = document.getElementById("prediction-error");
  const form       = document.getElementById("prediction-form");

  // Limpiar mensajes previos
  if (errorDiv)   errorDiv.textContent  = "";
  if (resultDiv)  resultDiv.textContent = "";

  // Validar que existan los elementos
  if (!form || !regionSel || !productSel || !subcatSel) {
    console.warn("Elementos de predicción no encontrados en el DOM.");
    return;
  }

  // 1) Cargar metadatos para los dropdowns
  try {
    const [regions, products, subcats] = await Promise.all([
      fetch('/metadata/regions').then(r => r.ok ? r.json() : Promise.reject(r.status)),
      fetch('/metadata/products').then(r => r.ok ? r.json() : Promise.reject(r.status)),
      fetch('/metadata/subcategories').then(r => r.ok ? r.json() : Promise.reject(r.status))
    ]);

    // 2) Poblar selects
    regionSel.innerHTML  = regions.map(r => `<option value="${r}">${r}</option>`).join('');
    productSel.innerHTML = products.map(p => `<option value="${p}">${p}</option>`).join('');
    subcatSel.innerHTML  = subcats.map(s => `<option value="${s}">${s}</option>`).join('');
  } catch (err) {
    console.error('Error cargando metadatos:', err);
    // No mostramos este error al usuario para no confundirlo
    return;
  }

  // 3) Añadir listener al formulario
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    resultDiv.textContent = "Calculando…";
    errorDiv.textContent  = "";

    // 4) Construir payload
    const payload = {
      region:       regionSel.value,
      product_id:   productSel.value,
      sub_category: subcatSel.value,
      order_date:   dateInput.value,
      model:        modelSel.value
    };

    // 5) Llamar al endpoint
    try {
      const resp = await fetch("/predict/by_fields", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload)
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${resp.status}`);
      }
      const { prediction } = await resp.json();
      resultDiv.textContent = `Predicción ${modelSel.value.toUpperCase()}: ${prediction.toFixed(2)}`;
    } catch (err) {
      errorDiv.textContent  = err.message;
      resultDiv.textContent = "";
      console.error('Error en predict/by_fields:', err);
    }
  }, { once: true }); // once para evitar dobles listeners
}

// Exportar para que upload.js pueda invocarla
window.initPredictionByFields = initPredictionByFields;
