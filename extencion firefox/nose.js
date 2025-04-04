document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('openProgramBtn').addEventListener('click', () => {
    // Aquí puedes definir lo que debe hacer el botón cuando se presiona
    fetch('http://127.0.0.1:5000/open_program', {
      method: 'GET',
    }).then(response => {
      if (response.ok) {
        window.close()
      }
    }).catch(error => console.error('Error:', error));
  });
});