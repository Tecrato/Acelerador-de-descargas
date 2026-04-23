browser.downloads.onCreated.addListener(async (downloadItem) => {
  if (downloadItem.byExtensionId && downloadItem.byExtensionId === browser.runtime.id) {
    return;
  }

  const fileName = downloadItem.filename.split('\\').pop().split('/').pop();
  const extension = fileName.split('.').pop().toLowerCase();
  const tamanoBytes = downloadItem.fileSize;
  const tamanoKb = (tamanoBytes && tamanoBytes > 0) ? Math.floor(tamanoBytes / 1024) : -1;

  try {
    console.log('Tamano en bytes:', tamanoBytes);
    console.log('Extension:', extension);
    const checkResponse = await fetch(`http://127.0.0.1:5000/extencion/should_intercept?extension=${extension}&tamano=${tamanoKb}`);
    const checkResult = await checkResponse.json();
    console.log('Respuesta de la API:', checkResult);

    if (checkResult.respuesta === true) {
      const urlOrigin = new URL(downloadItem.url).origin;
      const cookies = await browser.cookies.getAll({ url: urlOrigin });
      const cookieString = cookies.map(cookie => `${cookie.name}=${cookie.value}`).join('; ');

      const response = await fetch('http://127.0.0.1:5000/descargas/add_web', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          'nombre': fileName,
          'url': downloadItem.url,
          'cookies': cookieString
        })
      });
      const result = await response.json();
      console.log('Respuesta de la API de descarga:', result);

      if (result.status !== 'error') {
        await browser.downloads.erase({ id: downloadItem.id });
      }
    }
  } catch (e) {
    console.error("Error en el manejador:", e);
  }
});

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "openProgram") {
    fetch('http://127.0.0.1:5000/open_program', { method: 'GET' })
      .then(() => sendResponse({ success: true }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }
});
