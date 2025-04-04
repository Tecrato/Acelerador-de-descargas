chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
    let extension = item.filename.split('.').pop().toLowerCase();
    chrome.downloads.pause(item.id);
    try {
        // Obtener cookies del dominio de la URL
        chrome.cookies.getAll({ url: new URL(item.url).origin }, (cookies) => {
		    let cookieString = cookies.map(cookie => `${cookie.name}=${cookie.value}`).join('; ');
		    console.log("Cookies obtenidas: ", cookieString);
            
            fetch('http://127.0.0.1:5000/extencion/check/' + extension)
            .then(response => response.json())
            .then(n => {
                console.log('recibió respuesta');
                console.log(n);
                if (n['respuesta'] == true) {
                    fetch('http://127.0.0.1:5000/descargas/add_web', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            'nombre': item.filename,
                            'url': item.url,
                            'cookies': cookieString  // Añadido: cookies
                        })
                    })
                    .then(response2 => response2.json())
                    .then(n2 => {
                        console.log(n2);
                        if (n2['status'] == 'error') {
                            chrome.downloads.resume(item.id);
                            suggest({filename: item.filename, conflictAction: 'uniquify'});
                            console.log('error 1');
                        } else {
                            try {
                                chrome.downloads.cancel(item.id);
                                chrome.downloads.erase(item.id);
                                return true;
                            } catch (e) {
                                return true;
                            }
                        }
                    });
                } else {
                    chrome.downloads.resume(item.id);
                    suggest({filename: item.filename, conflictAction: 'overwrite'});
                    console.log('error 2');
                }
            });
        });
    } catch (e) {
        chrome.downloads.resume(item.id);
        suggest({filename: item.filename, conflictAction: 'overwrite'});
        console.log('error 3');
        console.error(e);
    }
    return true;
});
