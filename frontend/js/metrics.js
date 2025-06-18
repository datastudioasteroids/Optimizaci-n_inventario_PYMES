// static/js/metrics.js
document.addEventListener('DOMContentLoaded', () => {
  const monthInput  = document.getElementById('month-range');
  const vendorSel   = document.getElementById('vendor-select');
  const productSel  = document.getElementById('product-select');

  async function updateKPIs() {
    const month  = monthInput.value || null;
    const vendor = vendorSel.value;
    const product= productSel.value;

    const params = new URLSearchParams();
    if (month)  params.set('month', month);
    if (vendor && vendor !== 'Todos')  params.set('vendor', vendor);
    if (product && product !== 'Todos') params.set('product', product);

    try {
      const resp = await fetch(`/kpis?${params.toString()}`);
      if (!resp.ok) throw new Error(`Status ${resp.status}`);
      const { total_sales, avg_profit_pct, sale_count, avg_sales } = await resp.json();

      document.getElementById('kpi-total-sales').textContent = total_sales.toFixed(2);
      document.getElementById('kpi-avg-profit').textContent  = (avg_profit_pct * 100).toFixed(1) + '%';
      document.getElementById('kpi-sale-count').textContent = sale_count;
      document.getElementById('kpi-avg-sales').textContent = avg_sales.toFixed(2);
    } catch (err) {
      console.error('Error al actualizar KPIs:', err);
    }
  }

  // Dispara cuando cambian los filtros
  monthInput.addEventListener('change',  updateKPIs);
  vendorSel.addEventListener('change',  updateKPIs);
  productSel.addEventListener('change', updateKPIs);

  // Llamada inicial
  updateKPIs();
});