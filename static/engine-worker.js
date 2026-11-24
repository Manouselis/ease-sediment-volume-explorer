/* This worker runs the same Python calculations as the localhost app. */
'use strict';
let engine;
let requests = Promise.resolve();

async function initialize() {
  const indexURL = new URL('engine/__RUNTIME__/', self.location.href);
  const {loadPyodide} = await import(new URL('pyodide.mjs', indexURL).href);
  const python = await loadPyodide({indexURL:indexURL.href});
  await python.loadPackage(__PACKAGES__);
  const archive = new URL('engine/source.zip', self.location.href);
  archive.search = self.location.search;
  const response = await fetch(archive);
  if (!response.ok) throw new Error('Could not download analysis code');
  python.unpackArchive(await response.arrayBuffer(), 'zip', {extractDir:'/ease'});
  python.FS.mkdir('/incoming');
  const dispatch = python.runPython(
    'import sys\nsys.path.insert(0, "/ease")\nfrom ease_volume.browser_api import dispatch\ndispatch'
  );
  return {python, dispatch};
}

async function handle({id, path, fields, files}) {
  try {
    engine ??= initialize();
    const {python, dispatch} = await engine;
    if (Object.values(files).some(file => /\.zip$/i.test(file.name))) await python.loadPackage('fiona');
    self.postMessage({id, ready:true});
    const blobs = Object.entries(files).map(([name, file]) => ({name, data:file}));
    const names = Object.fromEntries(Object.entries(files).map(([role, file]) => [role, file.name]));
    if (blobs.length) python.FS.mount(python.FS.filesystems.WORKERFS, {blobs}, '/incoming');
    try {
      const response = JSON.parse(dispatch(path, JSON.stringify(fields), JSON.stringify(names)));
      if (response.file) {
        const buffer = python.FS.readFile(response.file).buffer;
        self.postMessage({id, status:200, buffer, type:response.type}, [buffer]);
      } else {
        self.postMessage({id, ...response});
      }
    } finally {
      if (blobs.length) python.FS.unmount('/incoming');
    }
  } catch (error) {
    console.error('EASE browser worker', error);
    // A fresh worker can retry an interrupted runtime load.
    self.postMessage({id, fatal:true});
  }
}

self.onmessage = ({data}) => {
  requests = requests.then(() => handle(data));
};
