// =================================================================
// dashboard.js (versión completa con sección de Predicción)
// =================================================================

// Guardamos referencias globales a las instancias de los gráficos
let barChartInstance = null;
let lineChartInstance = null;
let scatterChartInstance = null;

/**
 * fetchKpis(filters): obtiene los KPI de negocio según filtros
 */
async function fetchKpis({ month, vendor, product }) {
  try {
    const query = new URLSearchParams();
    if (month)       query.append("month", month);
    if (vendor)      query.append("vendor", vendor);
    if (product)     query.append("product", product);

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
    if (month)    query.append("month", month);
    if (vendor)   query.append("vendor", vendor);
    if (product)  query.append("product", product);

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
 * fetchScatterData(): obtiene datos para el gráfico de dispersión
 * (Utilidad vs Ingresos por Producto).
 */
async function fetchScatterData() {
  try {
    // Llamamos a grouped?field=Product%20Name sin filtros de mes/vendor/product
    const resp = await fetch(`http://localhost:8000/grouped?field=Product%20Name`);
    if (!resp.ok) throw new Error("Error al obtener datos de productos");
    const json = await resp.json();
    return json.data;  // cada objeto: { group: <product_name>, total_sales, total_quantity, avg_discount, total_profit }
  } catch (err) {
    console.error("fetchScatterData():", err);
    return [];
  }
}

/**
 * drawScatterChart(): dibuja el gráfico de dispersión
 * Utilidad (y) vs Ingresos (x) para cada producto.
 */
async function drawScatterChart() {
  const productData = await fetchScatterData();

  const puntos = productData.map(p => {
    const ing = p.total_sales;
    const prof = p.total_profit;
    const pctProfit = ing !== 0 ? prof / ing : 0;
    return {
      x: ing,
      y: pctProfit,
      etiqueta: p.group
    };
  });

  const scatterCtx = document.getElementById("scatter-chart").getContext("2d");
  if (scatterChartInstance) scatterChartInstance.destroy();

  scatterChartInstance = new Chart(scatterCtx, {
    type: "scatter",
    data: {
      datasets: [{
        label: "Productos",
        data: puntos,
        backgroundColor: "#00E5FF",
        pointRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const p = ctx.raw;
              return `${p.etiqueta}: Ingresos $${p.x.toLocaleString()} | Utilidad ${(p.y * 100).toFixed(1)}%`;
            }
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
          min: 0,
          max: 0.5
        }
      }
    }
  });
}

/**
 * initLineChart(selectedVendor, selectedMonth): obtiene datos reales de /sales_trend y dibuja el gráfico
 */
async function initLineChart(selectedVendor = "Todos", selectedMonth = null) {
  try {
    // 1) Ajustar título dinámico
    const titleEl = document.getElementById("line-chart-title");
    if (selectedMonth) {
      const fecha = new Date(selectedMonth + "-01");
      const nombreMes = fecha.toLocaleString("es-ES", { month: "long", year: "numeric" });
      titleEl.innerText = `Ventas diarias de ${nombreMes} por Cliente`;
    } else {
      titleEl.innerText = "Ventas 2020 por Cliente";
    }

    // 2) Construir URL de /sales_trend
    let yearToUse = 2020;
    let url = `http://localhost:8000/sales_trend?year=${yearToUse}&vendor=${encodeURIComponent(selectedVendor)}`;

    if (selectedMonth) {
      const [anioStr] = selectedMonth.split("-");
      yearToUse = parseInt(anioStr, 10);
      url = `http://localhost:8000/sales_trend?year=${yearToUse}&month=${encodeURIComponent(selectedMonth)}&vendor=${encodeURIComponent(selectedVendor)}`;
    }

    const resp = await fetch(url);
    if (!resp.ok) throw new Error("Error al obtener datos de ventas reales");
    const json = await resp.json();

    const labels = json.labels;     // p. ej. ["2018-06-01", ..., "2018-06-30"] o ["2020-01", ..., "2020-12"]
    const datasets = json.datasets; // arreglo de objetos { vendor: "Nombre", values: [ ... ] }

    // 3) Dibujar el chart
    const ctx = document.getElementById("line-chart").getContext("2d");
    if (lineChartInstance) lineChartInstance.destroy();

    const chartDatasets = datasets.map(ds => {
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
 * populateDropdowns(): rellena los <select> de Cliente y Producto
 */
async function populateDropdowns() {
  try {
    // 1) Clientes (Customer Name)
    const fieldVendor = encodeURIComponent("Customer Name");
    const respV = await fetch(`http://localhost:8000/grouped?field=${fieldVendor}`);
    if (respV.ok) {
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
    } else {
      console.error(`Error ${respV.status} en /grouped?field=${fieldVendor}`);
    }

    // 2) Productos (Product Name)
    const fieldProduct = encodeURIComponent("Product Name");
    const respP = await fetch(`http://localhost:8000/grouped?field=${fieldProduct}`);
    if (respP.ok) {
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
    } else {
      console.error(`Error ${respP.status} en /grouped?field=${fieldProduct}`);
    }
  }
  catch (err) {
    console.error("populateDropdowns():", err);
  }
}

/**
 * populatePredictionDropdowns(): rellena los <select> de Region, Product ID, Category, Sub-Category, Product Name
 */
async function populatePredictionDropdowns() {
  // Para cada uno de estos cinco campos hacemos una llamada a /grouped
  const fields = [
    { field: "Region",     selectId: "pred-region",      placeholder: "Ej. West" },
    { field: "Product ID", selectId: "pred-product-id",  placeholder: "Ej. P-1001" },
    { field: "Category",   selectId: "pred-category",    placeholder: "Ej. Technology" },
    { field: "Sub-Category", selectId: "pred-sub-category", placeholder: "Ej. Phones" },
    { field: "Product Name", selectId: "pred-product-name", placeholder: "Ej. iPhone 12" }
  ];

  for (let item of fields) {
    try {
      const resp = await fetch(`http://localhost:8000/grouped?field=${encodeURIComponent(item.field)}`);
      if (!resp.ok) throw new Error(`Falló /grouped?field=${item.field}`);
      const json = await resp.json();
      const selectEl = document.getElementById(item.selectId);
      // Coloco primero la opción en blanco (placeholder)
      selectEl.innerHTML = `<option value="">${item.placeholder}</option>`;
      json.data.forEach(row => {
        if (row.group) {
          const opt = document.createElement("option");
          opt.value = row.group;
          opt.innerText = row.group;
          selectEl.appendChild(opt);
        }
      });
    } catch (err) {
      console.error(`populatePredictionDropdowns(): no pude poblar ${item.field}`, err);
    }
  }
}

/**
 * submitPrediction(): toma los valores del formulario y llama a /predict para obtener la predicción
 */
async function submitPrediction() {
  // 1) Leer valores del formulario
  const region      = document.getElementById("pred-region").value;
  const productId   = document.getElementById("pred-product-id").value;
  const category    = document.getElementById("pred-category").value;
  const subCategory = document.getElementById("pred-sub-category").value;
  const productName = document.getElementById("pred-product-name").value;
  const date        = document.getElementById("pred-date").value;    // si quieres enviar fecha, pero el modelo la ignora
  const quantity    = parseInt(document.getElementById("pred-quantity").value) || 0;
  const discount    = parseFloat(document.getElementById("pred-discount").value) || 0;
  const profit      = parseFloat(document.getElementById("pred-profit").value) || 0;

  // 2) Armar el objeto que tu modelo XGBoost espera
  //    (solo con las columnas usadas durante el entrenamiento)
  const payloadObj = {
    "Region": region,
    "Product ID": productId,
    "Category": category,
    "Sub-Category": subCategory,
    "Product Name": productName,
    "Quantity": quantity,
    "Discount": discount,
    "Profit": profit
    // <Si quisieras enviar la fecha, podrías agregar: "Order Date": date>
    // Pero el modelo actual no la usa, así que la dejamos fuera del payload.
  };

  try {
    // 3) Llamar al endpoint /predict (FastAPI espera una lista de objetos)
    const resp = await fetch("http://localhost:8000/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify([payloadObj])
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(txt);
    }
    const json = await resp.json();
    const pred = json.predictions[0];

    // 4) Mostrar el resultado en la página
    document.getElementById("prediction-result").innerText =
      `🔮 Predicción de Ventas: $${pred.toFixed(2)}`;
  }
  catch (err) {
    console.error("submitPrediction():", err);
    document.getElementById("prediction-result").innerText =
      "❌ Ocurrió un error al predecir.";
  }
}

/**
 * initDashboard(): función principal que arranca todo
 */
async function initDashboard() {
  // 1) Poblar dropdowns de Cliente y Producto (para KPIs, barras, líneas)
  await populateDropdowns();

  // 2) Poblar dropdowns de Region, Product ID, Category, Sub-Category, Product Name (para predicción manual)
  await populatePredictionDropdowns();

  // 3) Pedir KPI iniciales sin filtros
  const initialFilters = { month: null, vendor: "Todos", product: "Todos" };
  const kpis = await fetchKpis(initialFilters);
  updateKpisDisplay(kpis);

  // 4) Inicializar los gráficos de líneas y dispersión
  //    Para la línea: vendor = "Todos", sin month (null)
  await initLineChart("Todos", null);
  await drawScatterChart();

  // 5) Dibujar gráfico de barras inicial (agrupado por "Category")
  const groupedInit = await fetchGrouped("Category", initialFilters);
  drawBarChart(groupedInit);

  // 6) Registrar listeners en los selectores
  const monthEl   = document.getElementById("month-range");
  const vendorEl  = document.getElementById("vendor-select");
  const productEl = document.getElementById("product-select");
  const groupEl   = document.getElementById("group-by");

  async function onFilterChange() {
    const filters = {
      month: monthEl.value || null,       // ejemplo: "2018-06"
      vendor: vendorEl.value,             // ejemplo: "Joe Elijah"
      product: productEl.value            // ejemplo: "Todos"
    };

    // 0) Actualizar el gráfico de líneas
    await initLineChart(filters.vendor, filters.month);

    // 1) Actualizar KPIs
    const updatedKpis = await fetchKpis(filters);
    updateKpisDisplay(updatedKpis);

    // 2) Actualizar gráfico de barras
    const grp = await fetchGrouped(groupEl.value, filters);
    drawBarChart(grp);

    // 3) Actualizar gráfico de dispersión
    await drawScatterChart();
  }

  monthEl.addEventListener("change", onFilterChange);
  vendorEl.addEventListener("change", onFilterChange);
  productEl.addEventListener("change", onFilterChange);
  groupEl.addEventListener("change", onFilterChange);
}

// Ejecutar cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", initDashboard);
