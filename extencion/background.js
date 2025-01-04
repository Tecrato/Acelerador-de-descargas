chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
	let extension = item.filename.split('.').pop()
	extension = extension.toLowerCase()
	chrome.downloads.pause(item.id);
	try {
		fetch('http://127.0.0.1:5000/extencion/check/' + extension)
		.then(response => response.json())
		.then(n => {
			console.log('recibio respuesta')
			console.log(n)
			if (n['respuesta'] == true) {
				fetch('http://127.0.0.1:5000/descargas/add_web', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({'nombre': item.filename, 'url': item.url})
				})
				.then(response2 => response2.json())
				.then(n2 => {
					console.log(n2)
					if (n2['status'] == 'error'){
						chrome.downloads.resume(item.id);
						suggest({filename: item.filename, conflictAction: 'uniquify'})
						console.log('error 1')
					} else {
						try{
							chrome.downloads.cancel(item.id);
							chrome.downloads.erase(item.id);
							return true
						} catch(e) {
							return true
						}
					}
				
				})
			} else {
			chrome.downloads.resume(item.id);
			suggest({filename: item.filename, conflictAction: 'overwrite'})
			console.log('error 2')
			}
		});
	} catch(e) {
		chrome.downloads.resume(item.id);
		suggest({filename: item.filename, conflictAction: 'overwrite'})
		console.log('error 3')
		console.error(e)
	}
	return true
});
