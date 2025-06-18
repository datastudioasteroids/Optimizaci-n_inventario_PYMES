// static/js/app.js
console.log('Demo Sales Forecasting cargado');

document.addEventListener('DOMContentLoaded', async () => {
  // 1) Carga dinámica de upload, metrics y dashboard
  const módulos = [
    '/static/js/upload.js',
    '/static/js/metrics.js',
    '/static/js/dashboard.js'
  ];
  for (const src of módulos) {
    await new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = src;
      s.async = false;
      s.onload = res;
      s.onerror = () => rej(new Error(`No cargó ${src}`));
      document.body.appendChild(s);
    });
  }
  console.log('Módulos frontend cargados.');

  // 2) Inicializa YA la parte de predicción
  if (window.initPredictionByFields) {
    window.initPredictionByFields();
  }
});

async function initPredictionByFields() {
  const regionSel   = document.getElementById('pred-region');
  const productSel  = document.getElementById('pred-product');
  const dateInput   = document.getElementById('pred-date');
  const periodSel   = document.getElementById('pred-period');
  const form        = document.getElementById('prediction-form');
  const resDiv      = document.getElementById('prediction-result');
  const errDiv      = document.getElementById('prediction-error');

  // 1) Cargar metadatos
  try {
    const [regs, prods] = await Promise.all([
      fetch('/metadata/regions').then(r => r.ok ? r.json() : Promise.reject()),
      fetch('/metadata/products').then(r => r.ok ? r.json() : Promise.reject())
    ]);
    regionSel.innerHTML  =
      `<option value="">Seleccione región</option>` +
      regs.map(r => `<option value="${r}">${r}</option>`).join('');
    productSel.innerHTML =
      `<option value="">Seleccione producto</option>` +
      prods.map(p => `<option value="${p}">${p}</option>`).join('');
  } catch {
    console.warn('Error cargando regiones/productos');
    errDiv.textContent = '❌ No se pudieron cargar opciones.';
    return;
  }

  // 2) Manejar envío de predicción
  form.addEventListener('submit', async e => {
    e.preventDefault();
    resDiv.textContent = 'Calculando…';
    errDiv.textContent = '';

    const payload = {
      region:  regionSel.value,
      product: productSel.value,
      date:    dateInput.value,
      period:  periodSel.value   // <-- añadimos el período
    };

    try {
      const resp = await fetch('/predict', {
        method:  'POST',
        headers: {'Content-Type':'application/json'},
        body:    JSON.stringify(payload)
      });
      const body = await resp.json();
      if (!resp.ok) throw new Error(body.detail || `Error ${resp.status}`);

      // Elegir título según período
      let titulo;
      switch (body.period) {
        case 'quarter':  titulo = 'Trimestre'; break;
        case 'semester': titulo = 'Semestre';  break;
        case 'year':     titulo = 'Año';       break;
        default:         titulo = 'Día';
      }

      resDiv.innerHTML = `
        <strong>Predicción (${titulo})</strong><br>
        • Cantidad total: ${body.quantity.toFixed(2)}<br>
        • Ganancia total: $${body.profit.toFixed(2)}
      `;
    } catch (err) {
      console.error('Error /predict:', err);
      errDiv.textContent = err.message || '❌ Error al predecir';
      resDiv.textContent = '';
    }
  });
}

window.initPredictionByFields = initPredictionByFields;
