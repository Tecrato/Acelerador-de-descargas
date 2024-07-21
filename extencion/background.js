var valor = true

function activar() {
	chrome.storage.local.get('activa_extension_acc_des_Edouard')
	.then(respuesta => {
		console.log(respuesta);
		valor = respuesta['activa_extension_acc_des_Edouard']
})}

setInterval(() => {
	activar()
}, 1000)

chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
	const regex = /(.whl|.exe|.iso|.cia|.apk|.rar|.zip|.jar|.mp3|.mp4|.mkv|.flv|.avi)$/i
	activar()
	if (regex.test(item.filename) && valor == true) {
		const data = {
		fileUrl: item.url,
		name: item.filename
		}
		fetch('http://127.0.0.1:5000/add_download', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(data)
		})
		chrome.downloads.cancel(item.id)
		chrome.downloads.erase({id:item.id})
		suggest()
	}
	
});
