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
  const boton = document.querySelector('#activar')

  chrome.storage.local.get('activa_extension_acc_des_Edouard').then(res => {
    if (res['activa_extension_acc_des_Edouard'] == true) {
      boton.setAttribute('checked','')
    } else if (res['activa_extension_acc_des_Edouard'] == false) {
      boton.removeAttribute('checked')
    } else {
      boton.setAttribute('checked','')
    }
  })
  
  boton.addEventListener('click', (btn) => {
      let checked = btn.target.toggleAttribute('checked')
      chrome.storage.local.set({'activa_extension_acc_des_Edouard':checked})
  })
});