// upload.js
// ===============================
// Módulo para manejar la subida del CSV de entrenamiento.
// Tras un upload exitoso, muestra el dashboard y arranca initDashboard()
// y también initPredictionByFields() para poblar los menús de predicción.

// Esperamos al DOM para vincular eventos
document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('csvFileInput');
  const uploadBtn = document.getElementById('uploadBtn');
  const statusP   = document.getElementById('uploadStatus');
  const actions   = document.getElementById('actions');

  // Cuando el usuario seleccione un archivo, habilitamos el botón
  fileInput.addEventListener('change', () => {
    uploadBtn.disabled   = fileInput.files.length === 0;
    statusP.textContent  = ''; // Limpiar mensaje previo
  });

  // Al hacer click en "Subir CSV"
  uploadBtn.addEventListener('click', async () => {
    if (!fileInput.files.length) return;
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    statusP.textContent  = 'Subiendo CSV...';
    uploadBtn.disabled   = true;

    try {
      const res  = await fetch('/upload_csv', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);

      // Mensaje de éxito
      statusP.textContent = data.detail;

      // Mostrar dashboard
      actions.style.display = 'block';

      // Inicializar dashboard existente
      if (window.initDashboard) {
        window.initDashboard();
      }
      // Y ahora poblar los menús de predicción
      if (window.initPredictionByFields) {
        window.initPredictionByFields();
      }
    } catch (err) {
      console.error('Error al subir CSV:', err);
      statusP.textContent = 'Error: ' + err.message;
    } finally {
      uploadBtn.disabled = false;
    }
  });
});
