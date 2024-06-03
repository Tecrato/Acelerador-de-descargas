document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('openProgramBtn').addEventListener('click', () => {
        // Aquí puedes definir lo que debe hacer el botón cuando se presiona
        fetch('http://127.0.0.1:5000/open_program', {
          method: 'POST',
        }).then(response => {
          if (response.ok) {
            console.log("Programa abierto exitosamente");
            window.close()
          } else {
            console.error("Error al abrir el programa");
          }
        }).catch(error => console.error('Error:', error));
      });
});