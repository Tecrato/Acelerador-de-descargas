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
	try {
		fetch('http://127.0.0.1:5000/extencion/check/' + extension)
		.then(response => response.json())
		.then(n => {

			console.log('recibio respuesta')
			console.log(n)
			if (n['respuesta'] == true && valor == true) {

				fetch('http://127.0.0.1:5000/descargas/add_web?url=' + item.url + '&nombre=' + item.filename, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json'
				}})
				.then(response2 => response2.json())
				.then(n2 => {
					console.log(n2)
					if (n2['status'] == 'error'){
						suggest({filename: item.filename, conflictAction: 'uniquify'})
						console.log('error 1')
					} else {
						try{
							chrome.downloads.cancel(item.id);
						} catch(e) {
							valor
						}
					}
				
				})
			} else {
			suggest({filename: item.filename, conflictAction: 'uniquify'})
			console.log('error 2')
			}
		});
	} catch(e) {
		suggest({filename: item.filename, conflictAction: 'uniquify'})
		console.log('error 3')
	}
	return true
});
