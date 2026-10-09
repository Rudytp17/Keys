const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

function createWindow() {
  const win = new BrowserWindow({
    width: 1020, height: 720,
    backgroundColor: '#0A0A0D',
    title: 'UPC Quest 2026',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  win.setMenuBarVisibility(false);
  win.loadFile('UPC.html');
}

ipcMain.handle('launch-external', async () => {
  const vbsPath = app.isPackaged
    ? path.join(process.resourcesPath, 'Lanzar_Cody.vbs')
    : path.join(__dirname, 'Lanzar_Cody.vbs');

  if (!fs.existsSync(vbsPath)){
    return { ok: false, message: 'No se encontro: ' + vbsPath };
  }
  try {
    const child = spawn('wscript.exe', [vbsPath], {
      detached: true, stdio: 'ignore',
      cwd: path.dirname(vbsPath),
      windowsHide: true, shell: false
    });
    child.unref();
    return { ok: true, message: 'Cody lanzado (PID ' + child.pid + ')' };
  } catch(err){
    return { ok: false, message: err.message };
  }
});

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });