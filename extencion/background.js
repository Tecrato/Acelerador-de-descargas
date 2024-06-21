
chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {

//     // var newUrl = 'http://localhost:5000/download?url=' + encodeURIComponent(item.url)+'&name=item.filename';
//     // suggest({ filename: item.filename, conflictAction: 'overwrite', url: newUrl });

	const regex = /(.whl|.exe|.iso|.cia|.apk|.rar|.zip|.7z|.jar|.mp3|.mp4|.mkv|.flv|.avi)$/i

	if (regex.test(item.filename)) {
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
		chrome.downloads.erase({id:item.id})
		suggest();
	} else {
		suggest({ filename: item.filename, conflictAction: 'overwrite'});
	}
	
});
