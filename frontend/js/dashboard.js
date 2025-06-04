// =================================================================
// dashboard.js
// =================================================================

let barChartInstance = null;
let lineChartInstance = null;
let scatterChartInstance = null;

/**
 * fetchKpis(filters): obtiene los KPI de negocio según filtros
 */
async function fetchKpis({ month, vendor, product }) {
  try {
    const query = new URLSearchParams();
    if (month) query.append("month", month);
    if (vendor) query.append("vendor", vendor);
    if (product) query.append("product", product);

    const resp = await fetch(`http://localhost:8000/kpis?${query.toString()}`);
    if (!resp.ok) throw new Error("Error al obtener KPIs");
    return await resp.json();
  } catch (err) {
    console.error("fetchKpis():", err);
    return null;
  }
}

/**
 * updateKpisDisplay(data): actualiza el DOM con los KPIs
 */
function updateKpisDisplay(data) {
  if (!data) return;
  const fmtCurrency = num =>
    num.toLocaleString("es-AR", { style: "currency", currency: "USD", minimumFractionDigits: 0 });
  const fmtPercent = pct => `${(pct * 100).toFixed(0)}%`;

  document.getElementById("kpi-total-sales").innerText = fmtCurrency(data.total_sales);
  document.getElementById("kpi-avg-profit").innerText = fmtPercent(data.avg_profit_pct);
  document.getElementById("kpi-sale-count").innerText = data.sale_count.toLocaleString();
  document.getElementById("kpi-avg-sales").innerText = fmtCurrency(data.avg_sales);
}

/**
 * fetchGrouped(field, filters): agrupa datos según campo + filtros
 */
async function fetchGrouped(field, { month, vendor, product }) {
  try {
    const query = new URLSearchParams();
    query.append("field", field);
    if (month) query.append("month", month);
    if (vendor) query.append("vendor", vendor);
    if (product) query.append("product", product);

    const resp = await fetch(`http://localhost:8000/grouped?${query.toString()}`);
    if (!resp.ok) throw new Error("Error al obtener datos agrupados");
    const json = await resp.json();
    return json.data;
  } catch (err) {
    console.error("fetchGrouped():", err);
    return [];
  }
}

/**
 * drawBarChart(groupedData): dibuja el gráfico de barras
 */
function drawBarChart(groupedData) {
  const ctx = document.getElementById("bar-chart").getContext("2d");
  if (barChartInstance) barChartInstance.destroy();

  const labels = groupedData.map(o => o.group);
  const values = groupedData.map(o => o.total_sales);

  barChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Ventas",
        data: values,
        backgroundColor: "rgba(0, 150, 255, 0.7)",
        borderRadius: 6,
        barThickness: 20
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `$${ctx.parsed.y.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: "#ccc" },
          grid: { display: false }
        },
        y: {
          ticks: {
            color: "#ccc",
            callback: value => `$${(value / 1000).toFixed(0)}k`
          },
          grid: { color: "rgba(255,255,255,0.1)" }
        }
      }
    }
  });
}

/**
 * initLineChart(selectedVendor): obtiene datos reales de /sales_trend y dibuja el gráfico
 */
async function initLineChart(selectedVendor = "Todos") {
  try {
    // 1) Pedir al backend los datos de ventas mensuales para 2020 y para el vendor seleccionado
    const resp = await fetch(`http://localhost:8000/sales_trend?year=2020&vendor=${encodeURIComponent(selectedVendor)}`);
    if (!resp.ok) throw new Error("Error al obtener datos de ventas reales");
    const json = await resp.json();
    const labels = json.labels;        // ["2020-01", ..., "2020-12"]
    const datasets = json.datasets;    // [ { vendor: "Ana López", values: [ ... ] }, ... ]

    // 2) Construir la configuración de Chart.js
    const ctx = document.getElementById("line-chart").getContext("2d");
    if (lineChartInstance) lineChartInstance.destroy();

    // Creamos un dataset por cada Cliente
    const chartDatasets = datasets.map(ds => {
      // Generar un color pastel aleatorio
      const randomColor = () => {
        const r = Math.floor(Math.random() * 156) + 100;
        const g = Math.floor(Math.random() * 156) + 100;
        const b = Math.floor(Math.random() * 156) + 100;
        return `rgba(${r}, ${g}, ${b}, 0.6)`;
      };
      return {
        label: ds.vendor,
        data: ds.values,
        fill: false,
        borderColor: randomColor(),
        backgroundColor: randomColor(),
        tension: 0.3,
        pointRadius: 4,
        borderWidth: 2
      };
    });

    // 3) Crear el gráfico de líneas
    lineChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: chartDatasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "#eee",
              boxWidth: 12,
              boxHeight: 12
            }
          },
          tooltip: {
            mode: "index",
            intersect: false,
            callbacks: {
              label: ctx => `$${ctx.parsed.y.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
            }
          }
        },
        interaction: { mode: "nearest", axis: "x", intersect: false },
        scales: {
          x: {
            ticks: { color: "#ccc" },
            grid: { display: false }
          },
          y: {
            title: { display: true, text: "Ventas (USD)", color: "#ddd", font: { size: 12 } },
            ticks: {
              color: "#ccc",
              callback: value => `$${(value / 1000).toFixed(0)}k`
            },
            grid: { color: "rgba(255,255,255,0.1)" }
          }
        }
      }
    });
  }
  catch (err) {
    console.error("initLineChart():", err);
  }
}

/**
 * initScatterChart(): gráfico de dispersión (datos de ejemplo)
 */
function initScatterChart() {
  const scatterCtx = document.getElementById("scatter-chart").getContext("2d");
  if (scatterChartInstance) scatterChartInstance.destroy();

  const scatterData = {
    datasets: [
      {
        label: "Productos",
        data: [
          { x: 5000, y: 0.05 },
          { x: 10000, y: 0.10 },
          { x: 8000, y: 0.12 },
          { x: 12000, y: 0.08 },
          { x: 15000, y: 0.06 },
          { x: 9000, y: 0.14 },
          { x: 11000, y: 0.09 },
          { x: 7000, y: 0.04 },
          { x: 13000, y: 0.11 }
        ],
        backgroundColor: "#00E5FF",
        pointRadius: 6
      }
    ]
  };

  const scatterOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: ctx =>
            `Ingresos: $${ctx.parsed.x.toLocaleString()}  Utilidad: ${(ctx.parsed.y * 100).toFixed(1)}%`
        }
      }
    },
    scales: {
      x: {
        title: { display: true, text: "Ingresos (USD)", color: "#ddd", font: { size: 12 } },
        ticks: { color: "#ccc", callback: value => `$${(value / 1000).toFixed(0)}k` },
        grid: { color: "rgba(255,255,255,0.1)" }
      },
      y: {
        title: { display: true, text: "% Utilidad", color: "#ddd", font: { size: 12 } },
        ticks: { color: "#ccc", callback: value => `${(value * 100).toFixed(0)}%` },
        grid: { color: "rgba(255,255,255,0.1)" },
        min: 0.02,
        max: 0.18
      }
    }
  };

  scatterChartInstance = new Chart(scatterCtx, {
    type: "scatter",
    data: scatterData,
    options: scatterOptions
  });
}

/**
 * populateDropdowns(): rellena los <select> de Vendedor y Producto
 */
async function populateDropdowns() {
  try {
    // 1) Vendedores (Customer Name):
    const fieldVendor = encodeURIComponent("Customer Name");
    const respV = await fetch(`http://localhost:8000/grouped?field=${fieldVendor}`);
    if (!respV.ok) {
      console.error(`Error ${respV.status} en /grouped?field=${fieldVendor}`);
    } else {
      const { data } = await respV.json();
      const vendorSelect = document.getElementById("vendor-select");
      vendorSelect.innerHTML = '<option value="Todos">Todos</option>';
      data.forEach(item => {
        if (item.group) {
          const opt = document.createElement("option");
          opt.value = item.group;
          opt.innerText = item.group;
          vendorSelect.appendChild(opt);
        }
      });
    }

    // 2) Productos (Product Name):
    const fieldProduct = encodeURIComponent("Product Name");
    const respP = await fetch(`http://localhost:8000/grouped?field=${fieldProduct}`);
    if (!respP.ok) {
      console.error(`Error ${respP.status} en /grouped?field=${fieldProduct}`);
    } else {
      const { data } = await respP.json();
      const productSelect = document.getElementById("product-select");
      productSelect.innerHTML = '<option value="Todos">Todos</option>';
      data.forEach(item => {
        if (item.group) {
          const opt = document.createElement("option");
          opt.value = item.group;
          opt.innerText = item.group;
          productSelect.appendChild(opt);
        }
      });
    }
  }
  catch (err) {
    console.error("populateDropdowns():", err);
  }
}

/**
 * initPredictionForm(): configura el formulario de predicción
 */
function initPredictionForm() {
  const form = document.getElementById("predict-form");
  const resultDiv = document.getElementById("prediction-result");

  form.addEventListener("submit", async e => {
    e.preventDefault();
    resultDiv.innerText = "🔄 Calculando...";

    // Crear el payload con las columnas exactas
    const payloadObj = {
      "Region": document.getElementById("pred-region").value,
      "Product ID": document.getElementById("pred-productid").value,
      "Category": document.getElementById("pred-category").value,
      "Sub-Category": document.getElementById("pred-subcategory").value,
      "Product Name": document.getElementById("pred-product").value,
      "Quantity": parseInt(document.getElementById("pred-quantity").value) || 0,
      "Discount": parseFloat(document.getElementById("pred-discount").value) || 0,
      "Profit": parseFloat(document.getElementById("pred-profit").value) || 0
    };

    try {
      const resp = await fetch("http://localhost:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify([payloadObj])
      });
      if (!resp.ok) {
        const texto = await resp.text();
        throw new Error(`Error ${resp.status}: ${texto}`);
      }
      const { predictions } = await resp.json();
      const predVal = predictions[0];
      resultDiv.innerText = `🔮 Predicción de Ventas: $${predVal.toFixed(2)}`;
    } catch (err) {
      console.error("Error en predict:", err);
      resultDiv.innerText = "❌ Error al predecir.";
    }
  });
}

/**
 * initDashboard(): función principal que arranca todo
 */
async function initDashboard() {
  // 1) Llenar dropdowns de Vendedor y Producto
  await populateDropdowns();

  // 2) Pedir KPI iniciales sin filtros
  const initialFilters = { month: null, vendor: "Todos", product: "Todos" };
  const kpis = await fetchKpis(initialFilters);
  updateKpisDisplay(kpis);

  // 3) Inicializar los gráficos de líneas y dispersión
  //    Para la línea, por defecto vendor = "Todos"
  await initLineChart("Todos");
  initScatterChart();

  // 4) Dibujar gráfico de barras inicial (agrupado por "Category")
  const groupedInit = await fetchGrouped("Category", initialFilters);
  drawBarChart(groupedInit);

  // 5) Listeners a los selectores
  const monthEl = document.getElementById("month-range");
  const vendorEl = document.getElementById("vendor-select");
  const productEl = document.getElementById("product-select");
  const groupEl = document.getElementById("group-by");

  async function onFilterChange() {
    const filters = {
      month: monthEl.value || null,
      vendor: vendorEl.value,
      product: productEl.value
    };

    // 0) Actualizar el gráfico de líneas según el vendedor seleccionado
    await initLineChart(filters.vendor);

    // 1) Actualizar KPIs con filtros
    const updatedKpis = await fetchKpis(filters);
    updateKpisDisplay(updatedKpis);

    // 2) Actualizar gráfico de barras con agrupamiento
    const grouped = await fetchGrouped(groupEl.value, filters);
    drawBarChart(grouped);
  }

  monthEl.addEventListener("change", onFilterChange);
  vendorEl.addEventListener("change", onFilterChange);
  productEl.addEventListener("change", onFilterChange);
  groupEl.addEventListener("change", onFilterChange);

  // 6) Iniciar formulario de predicción
  initPredictionForm();
}

// Ejecutar cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", initDashboard);
