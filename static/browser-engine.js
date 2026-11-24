/* Adapt the existing analysis requests to the worker on GitHub Pages. */
(() => {
  'use strict';
  let worker;
  let nextId = 0;
  const pending = new Map();

  function reset(error) {
    worker?.terminate();
    worker = undefined;
    for (const request of pending.values()) request.reject(error);
    pending.clear();
  }

  function connect() {
    worker = new Worker(new URL(window.EASE_BROWSER.worker, location.href), {name:'EASE analysis',type:'module'});
    worker.addEventListener('error', reset, {once:true});
    worker.addEventListener('messageerror', reset, {once:true});
    worker.addEventListener('message', ({data}) => {
      const request = pending.get(data.id);
      if (!request) return;
      if (data.ready) {
        window.dispatchEvent(new Event('ease-browser-ready'));
        return;
      }
      if (data.fatal) {
        reset(new Error('The browser analysis engine stopped'));
        return;
      }
      pending.delete(data.id);
      const body = data.buffer ?? JSON.stringify(data.body);
      const headers = {'content-type': data.type || 'application/json'};
      request.resolve(new Response(body, {status:data.status, headers}));
    });
  }

  window.EASE_BROWSER_FETCH = (path, options = {}) => {
    if (path === '/api/demo') return fetch('./demo/metadata.json');
    const fields = {};
    const files = {};
    for (const [name, value] of options.body ?? []) {
      if (value instanceof File) files[name] = value;
      else fields[name] = value;
    }
    if (!worker) {
      window.dispatchEvent(new Event('ease-browser-starting'));
      connect();
    }
    const id = ++nextId;
    return new Promise((resolve, reject) => {
      pending.set(id, {resolve, reject});
      worker.postMessage({id, path, fields, files});
    });
  };
})();
