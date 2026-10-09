const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('upcBridge', {
  launchExternal: () => ipcRenderer.invoke('launch-external')
});