const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("ndps", {
  openAxis: () => ipcRenderer.invoke("ndps:open-axis"),
  openTarget: () => ipcRenderer.invoke("ndps:open-target"),
  runSimulation: (payload) => ipcRenderer.invoke("ndps:run", payload),
});
