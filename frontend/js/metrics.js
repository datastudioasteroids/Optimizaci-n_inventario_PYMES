// metrics.js: solicita métricas al backend y las muestra en pantalla.

document.addEventListener('DOMContentLoaded', () => {
  const metricsContainer = document.getElementById('metrics-container');

  fetch('http://localhost:8000/metrics')
    .then(response => response.json())
    .then(data => {
      const metrics = data.metrics;
      metricsContainer.innerHTML = '';
      for (const [key, value] of Object.entries(metrics)) {
        const div = document.createElement('div');
        div.className = 'metric-item';
        div.innerHTML = `<strong>${key.toUpperCase()}:</strong> ${value.toFixed(key === 'r2' ? 4 : 2)}`;
        metricsContainer.appendChild(div);
      }
    })
    .catch(err => {
      metricsContainer.innerHTML = '<p>No se pudieron cargar las métricas.</p>';
      console.error(err);
    });
});