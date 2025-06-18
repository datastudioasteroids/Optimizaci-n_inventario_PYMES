// data_utils.js
export function computeKpis(data) {
  const totalSales = data.reduce((sum, r) => sum + r.quantity * r.profit, 0);
  const saleCount  = data.length;
  const avgProfit  = data.reduce((sum, r) => sum + r.profit, 0) / saleCount;
  const avgSales   = totalSales / saleCount;
  return { totalSales, saleCount, avgProfit, avgSales };
}

export function groupAndTrend(data, { groupBy = 'date', dateGranularity = 'month' } = {}) {
  // ejemplo: construye un map para la trend por mes
  const trendMap = new Map();
  data.forEach(r => {
    const key = dateGranularity === 'month'
      ? `${r.date.getFullYear()}-${r.date.getMonth()+1}`
      : r[groupBy];
    const entry = trendMap.get(key) || { qty:0, profit:0 };
    entry.qty    += r.quantity;
    entry.profit += r.profit;
    trendMap.set(key, entry);
  });
  // separar en arrays ordenados
  const labels = Array.from(trendMap.keys()).sort();
  const values = labels.map(l => trendMap.get(l).qty);
  const profits = labels.map(l => trendMap.get(l).profit);
  return { dates: labels, values, labels, profits, sales: values };
}
