// Escucha cuando se crea una descarga
browser.downloads.onCreated.addListener(async (item) => {
  if (item.byExtensionId) {
    return;
  }
  const fileName = item.filename.split('\\').pop().split('/').pop();
  const extension = fileName.split('.').pop().toLowerCase();

  try {
    await browser.downloads.pause(item.id);

    const urlOrigin = new URL(item.url).origin;
    const cookies = await browser.cookies.getAll({ url: urlOrigin });
    const cookieString = cookies.map(cookie => `${cookie.name}=${cookie.value}`).join('; ');
    console.log("Cookies obtenidas:", cookieString);

    const response = await fetch('http://127.0.0.1:5000/extencion/check/' + extension);
    const n = await response.json();
    console.log('Respuesta de la API para la extensión:', n);

    if (n['respuesta'] === true) {
      const response2 = await fetch('http://127.0.0.1:5000/descargas/add_web', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          'nombre': fileName,
          'url': item.url,
          'cookies': cookieString
        })
      });
      const n2 = await response2.json();
      console.log('Respuesta de la API de descarga:', n2);

      if (n2['status'] === 'error') {
        await browser.downloads.resume(item.id);
      } else {
        await browser.downloads.cancel(item.id);
        await browser.downloads.erase(item.id);
      }
    } else {
      await browser.downloads.resume(item.id);
    }
  } catch (e) {
    await browser.downloads.resume(item.id);
  }
});
