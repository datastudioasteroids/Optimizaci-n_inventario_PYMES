// =================================================================
// dashboard.js (versión completa con sección de Predicción)
// CARGAR ESTE MÓDULO *DESPUÉS* DE upload.js, tras subir y entrenar.
// =================================================================

// Instancias globales de Chart.js
let barChartInstance     = null;
let lineChartInstance    = null;
let scatterChartInstance = null;


/** populateDropdowns(): rellena selects de Región, Cliente y Producto */
async function populateDropdowns() {
  try {
    const [regions, products, vendors] = await Promise.all([
      fetch('/metadata/regions').then(r => r.ok ? r.json() : Promise.reject()),
      fetch('/metadata/products').then(r => r.ok ? r.json() : Promise.reject()),
      fetch('/metadata/vendors').then(r => r.ok ? r.json() : Promise.reject())
    ]);

    // Región (si la tuvieras en el UI)
    const regionSel = document.getElementById("region-select");
    if (regionSel) {
      regionSel.innerHTML = `<option value="">Todas</option>` +
        regions.map(r => `<option value="${r}">${r}</option>`).join("");
    }

    // Cliente (Customer Name)
    const vendorSel = document.getElementById("vendor-select");
    vendorSel.innerHTML = `<option value="Todos">Todos</option>` +
      vendors.map(v => `<option value="${v}">${v}</option>`).join("");

    // Producto (Product Name)
    const prodSel = document.getElementById("product-select");
    prodSel.innerHTML = `<option value="Todos">Todos</option>` +
      products.map(p => `<option value="${p}">${p}</option>`).join("");
  } catch (err) {
    console.error("populateDropdowns():", err);
  }
}

/** populatePredictionDropdowns(): rellena selects de predicción */
async function populatePredictionDropdowns() {
  const specs = [
    { field: "Region",       selectId:"pred-region",  placeholder:"Seleccione región" },
    { field: "Product Name", selectId:"pred-product", placeholder:"Seleccione producto" }
  ];
  for (const { field, selectId, placeholder } of specs) {
    const data = await fetchGrouped(field, {});
    const sel  = document.getElementById(selectId);
    sel.innerHTML = `<option value="">${placeholder}</option>`;
    data.forEach(r => sel.append(new Option(r.group, r.group)));
  }
}

/** submitPrediction(): envía /predict y muestra el resultado */
async function submitPrediction() {
  const region  = document.getElementById("pred-region").value;
  const product = document.getElementById("pred-product").value;
  const date    = document.getElementById("pred-date").value;
  const errDiv  = document.getElementById("prediction-error");
  const resDiv  = document.getElementById("prediction-result");
  errDiv.textContent = "";
  resDiv.textContent = "Calculando…";

  try {
    const resp = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ region, product, date })
    });
    const body = await resp.json();
    if (!resp.ok) throw new Error(body.detail || `Error ${resp.status}`);

    resDiv.innerHTML = `
      • Cantidad predicha: ${body.quantity.toFixed(2)}<br>
      • Ganancia predicha: $${body.profit.toFixed(2)}
    `;
  } catch (err) {
    console.error("submitPrediction():", err);
    errDiv.textContent = err.message || "❌ Error al predecir";
    resDiv.textContent = "";
  }
}

/** initDashboard(): arranca todo tras subir+entrenar */
async function initDashboard() {
  await populateDropdowns();
    // 2) … ahora el resto:
  updateKpisDisplay(await fetchKpis({ month: null, vendor: "Todos", product: "Todos" }));
  await initLineChart("Todos", null);
  drawBarChart(await fetchGrouped("Category", { month: null, vendor: "Todos", product: "Todos" }));
  await drawScatterChart();
  await populatePredictionDropdowns();

  const filters = { month: null, vendor: "Todos", product: "Todos" };
  updateKpisDisplay(await fetchKpis(filters));
  await initLineChart(filters.vendor, filters.month);
  await drawScatterChart(filters);
  drawBarChart(await fetchGrouped("Category", filters));

  // Listeners de filtros
  const monthEl  = document.getElementById("month-range");
  const vendorEl = document.getElementById("vendor-select");
  const prodEl   = document.getElementById("product-select");
  const groupEl  = document.getElementById("group-by");

  const onFilterChange = async () => {
    const f = {
      month:  monthEl.value  || null,
      vendor: vendorEl.value,
      product: prodEl.value
    };
    updateKpisDisplay(await fetchKpis(f));
    await initLineChart(f.vendor, f.month);
    drawBarChart(await fetchGrouped(groupEl.value, f));
    await drawScatterChart(f);
  };

  [monthEl, vendorEl, prodEl, groupEl]
    .forEach(el => el.addEventListener("change", onFilterChange));

  // Listener de predicción
  document.getElementById("prediction-form")
          .addEventListener("submit", e => { e.preventDefault(); submitPrediction(); });
}

// Exportamos para que upload.js lo invoque
window.initDashboard = initDashboard;
