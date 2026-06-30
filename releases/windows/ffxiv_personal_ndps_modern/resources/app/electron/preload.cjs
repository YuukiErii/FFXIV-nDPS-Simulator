const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("ndps", {
  openAxis: () => ipcRenderer.invoke("ndps:open-axis"),
  openTarget: () => ipcRenderer.invoke("ndps:open-target"),
  openTrack: () => ipcRenderer.invoke("ndps:open-track"),
  runSimulation: (payload) => ipcRenderer.invoke("ndps:run", payload),
});
