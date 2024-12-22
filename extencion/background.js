var valor = true

try{
	chrome.storage.local.get('activa_extension_acc_des_Edouard')
} catch(e) {
	chrome.storage.local.set({'activa_extension_acc_des_Edouard':true});
}

function activar() {
	chrome.storage.local.get('activa_extension_acc_des_Edouard')
	.then(respuesta => {
		valor = respuesta['activa_extension_acc_des_Edouard']
})}
activar()


chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
	let extension = item.filename.split('.').pop()
	extension = extension.toLowerCase()
	activar();

	fetch('http://127.0.0.1:5000/extencion/check/' + extension)
	.then(response => response.json())
	.then(n => {
	  if (n['respuesta'] == true && valor == true) {
			chrome.downloads.cancel(item.id);
			fetch('http://127.0.0.1:5000/descargas/add_web?url=' + item.url + '&nombre=' + item.filename, {
			method: 'GET',
			headers: {
			'Content-Type': 'application/json'
		  }
		}).then(response => {
			if (response.json()['status'] == 'error'){
				suggest({filename: item.filename, conflictAction: 'uniquify'})
			}	
		})
	  } else {
		suggest({filename: item.filename, conflictAction: 'uniquify'})
		}
	});
	return true
});
