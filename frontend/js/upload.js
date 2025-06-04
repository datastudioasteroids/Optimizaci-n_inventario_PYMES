// upload.js: gestiona la subida del CSV y muestra las predicciones.

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('upload-form');
  const fileInput = document.getElementById('file-input');
  const errorDiv = document.getElementById('upload-error');
  const resultsBody = document.getElementById('results-body');

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    errorDiv.textContent = '';
    resultsBody.innerHTML = '';

    const file = fileInput.files[0];
    if (!file) {
      errorDiv.textContent = 'Por favor selecciona un archivo CSV.';
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch('http://localhost:8000/predict_csv', {
      method: 'POST',
      body: formData
    })
      .then(response => response.json())
      .then(data => {
        const predictions = data.predictions;
        if (!predictions || predictions.length === 0) {
          errorDiv.textContent = 'No se recibieron predicciones.';
          return;
        }
        predictions.forEach((pred, idx) => {
          const tr = document.createElement('tr');
          const tdIdx = document.createElement('td');
          tdIdx.textContent = idx + 1;
          const tdPred = document.createElement('td');
          tdPred.textContent = pred.toFixed(2);
          tr.appendChild(tdIdx);
          tr.appendChild(tdPred);
          resultsBody.appendChild(tr);
        });
      })
      .catch(err => {
        errorDiv.textContent = 'Error al procesar la predicción.';
        console.error(err);
      });
  });
});