document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('openProgramBtn').addEventListener('click', () => {
    browser.runtime.sendMessage({ action: "openProgram" })
      .then(() => window.close())
      .catch(error => console.error('Error:', error));
  });
});
