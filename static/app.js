(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const hosting = window.EASE_HOSTING;
  let accessKey = '';
  let accessBusy = false;
  let hostedMessage = '';
  let currentRequest = 0;
  const localEngine = 'http://127.0.0.1:8767';
  let backend;
  let serverOrigin;
  if (hosting?.apiOrigin) {
    const parsed = new URL(hosting.apiOrigin);
    const loopback = ['localhost', '127.0.0.1'].includes(parsed.hostname);
    if (!parsed.username && !parsed.password && (parsed.protocol === 'https:' || (loopback && location.protocol === 'http:'))) {
      serverOrigin = parsed.origin;
    }
  }
  const mib = 1024 * 1024;
  const surveyLimitMB = 100;
  const otherLimitMB = 25;
  const state = {
    lang: localStorage.getItem('ease-language') === 'nl' ? 'nl' : 'en',
    demo: null, files: {survey: null, reference: null, boundary: null},
    result: null, view: 'difference', busy: false, error: null, stale: false,
    demoNoteAuto: false, resultNoteAuto: false, plotWidth: 0,
    verticalScale: 'auto', cameraRevision: 0, bedPatchFocused: false,
    preview: null, previewView: '3d', previewCameraRevision: 0, analysisBounds: null, inspecting: false,
    profileView: '3d'
  };
  const t = key => {
    const value = key.split('.').reduce((o, k) => o?.[k], window.EASE_I18N[state.lang]);
    return typeof value === 'string' ? value : window.EASE_I18N[state.lang].errorGeneric;
  };
  const fmt = (value, digits = 1) => new Intl.NumberFormat(state.lang === 'nl' ? 'nl-NL' : 'en-GB', {maximumFractionDigits: digits}).format(value);
  const safeLink = url => {
    try { const u = new URL(url, window.location.origin); return ['http:', 'https:'].includes(u.protocol) ? u.href : ''; }
    catch { return ''; }
  };
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };

  function hostStatus(key) {
    hostedMessage = key;
    $('hosted-message').textContent = key ? t(key) : '';
  }
  function apiFetch(path, options = {}, key = accessKey, origin = backend) {
    if (!hosting) return fetch(path, options);
    if (!origin || !key) throw new Error('Analysis access required');
    const localOptions = origin === localEngine ? {targetAddressSpace:'loopback'} : {};
    return fetch(origin + path, {
      ...options, ...localOptions, headers: {...options.headers, Authorization: 'Bearer ' + key},
      credentials: 'omit', redirect: 'error'
    });
  }
  function connectionCopy() {
    const local = accessKey ? backend === localEngine : $('hosted-target').value === 'local';
    const privacy = t(local ? 'hostLocalPrivacy' : 'hostPrivacy');
    $('hosted-privacy').textContent = privacy;
    $('run-privacy').textContent = privacy;
    $('hosted-start').hidden = !local || Boolean(accessKey);
  }
  function updateHosting() {
    if (!hosting) return;
    const mode = !accessKey ? 'hostPublic' : backend === localEngine ? 'hostLocal' : 'hostServer';
    $('runtime-badge').textContent = t(mode);
    $('runtime-footer').textContent = t(mode);
    $('hosted-title').textContent = t(accessKey ? 'hostAnalysis' : 'hostPublic');
    $('hosted-lead').textContent = t(accessKey ? 'hostConnectedHint' : 'hostDemoHint');
    $('hosted-demo-controls').hidden = Boolean(accessKey);
    connectionCopy();
    $('hosted-tools').hidden = false;
    document.querySelector('.intro').hidden = true;
    $('hosted-access').hidden = false;
    $('hosted-target-field').hidden = Boolean(accessKey) || !serverOrigin;
    $('hosted-login').hidden = Boolean(accessKey);
    $('hosted-lock').hidden = !accessKey;
    document.querySelector('.setup-panel').hidden = !accessKey;
    document.querySelector('.app-layout').classList.toggle('hosted-public', !accessKey);
    hostStatus(hostedMessage);
  }
  async function unlockHosted(event) {
    event.preventDefault();
    if (accessBusy) return;
    const input = $('hosted-key');
    const candidate = input.value.trim();
    const local = $('hosted-target').value === 'local';
    const origin = local ? localEngine : serverOrigin;
    const unavailable = local ? 'hostLocalOffline' : 'hostOffline';
    if (!candidate || !origin) return;
    input.value = '';
    accessBusy = true;
    const button = event.currentTarget.querySelector('button');
    button.disabled = true;
    $('hosted-target').disabled = true;
    hostStatus(local ? 'hostCheckingLocal' : 'hostChecking');
    try {
      const response = await apiFetch('/api/access', {signal: AbortSignal.timeout(local ? 20000 : 120000)}, candidate, origin);
      if (response.status === 401) return hostStatus('errors.hosted_access');
      if (!response.ok || (await response.json()).status !== 'ok') return hostStatus(unavailable);
      ++currentRequest;
      backend = origin;
      accessKey = candidate;
      state.demo = null;
      resetResults(false);
      hostStatus('hostUnlocked');
      translate();
      $('load-demo').focus();
    } catch {
      hostStatus(unavailable);
    } finally {
      accessBusy = false;
      button.disabled = false;
      $('hosted-target').disabled = false;
    }
  }
  function lockHosted() {
    if (state.busy) return;
    ++currentRequest;
    accessKey = '';
    backend = undefined;
    state.files = {survey:null, reference:null, boundary:null};
    state.demo = null;
    $('analysis-form').reset();
    for (const role of ['survey','reference','boundary']) setFile(role, null);
    clearError();
    clearPreview();
    resetResults(false);
    updateHosting();
    loadPublicDemo();
  }
  async function loadPublicDemo() {
    if (state.busy) return;
    if (accessKey) return lockHosted();
    const request = ++currentRequest;
    const method = $('hosted-method').value === 'kriging' ? 'kriging' : 'tin';
    const button = $('open-public-demo');
    button.disabled = true;
    hostStatus('demoLoading');
    try {
      const response = await fetch('./demo/' + method + '/view.json', {cache:'no-cache'});
      if (!response.ok) throw new Error('Demo assets unavailable');
      const {result, metadata} = await response.json();
      if (request !== currentRequest) return;
      resetResults(false);
      state.stale = false;
      $('stale-note').hidden = true;
      state.demo = metadata;
      state.result = result;
      state.resultNoteAuto = true;
      state.view = method === 'kriging' ? 'uncertainty' : 'bed';
      renderResults();
      setBusy(false);
      const currentUrl = new URL(location.href);
      currentUrl.searchParams.set('demo', method);
      history.replaceState(null, '', currentUrl);
      hostStatus('hostDemoReady');
    } catch {
      if (request === currentRequest) hostStatus('hostDemoError');
    } finally {
      button.disabled = false;
    }
  }
  function setExport(node, url) {
    const remote = typeof url === 'string' && /^\/api\/results\/[a-f0-9]{32}\/[\w.-]+$/.test(url);
    const example = hosting && typeof url === 'string' && /^demo\/(tin|kriging)\/[\w.-]+$/.test(url);
    node.hidden = !(remote || example);
    node.onclick = null;
    if (node.hidden) return;
    node.href = remote && hosting ? backend + url : url;
    if (!remote || !hosting) return;
    node.onclick = async event => {
      event.preventDefault();
      try {
        const response = await apiFetch(url);
        if (response.status === 404) return hostStatus('hostExpired');
        if (!response.ok) return hostStatus('hostDownloadError');
        const blobUrl = URL.createObjectURL(await response.blob());
        const download = el('a');
        download.href = blobUrl;
        download.download = url.split('/').at(-1);
        download.click();
        setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
      } catch {
        hostStatus(backend === localEngine ? 'hostLocalOffline' : 'hostOffline');
      }
    };
  }

  function translate() {
    document.documentElement.lang = state.lang;
    document.title = t('pageTitle');
    document.querySelectorAll('[data-i18n]').forEach(node => node.textContent = t(node.dataset.i18n));
    document.querySelectorAll('[data-i18n-placeholder]').forEach(node => node.placeholder = t(node.dataset.i18nPlaceholder));
    document.querySelectorAll('[data-i18n-aria]').forEach(node => node.setAttribute('aria-label', t(node.dataset.i18nAria)));
    document.querySelectorAll('[data-language]').forEach(node => node.setAttribute('aria-pressed', String(node.dataset.language === state.lang)));
    $('status-text').textContent = t(state.busy ? 'loadingStatus' : state.result ? 'resultsReady' : 'ready');
    updateHosting();
    updateReferenceForm();
    updateSurfaceForm();
    refreshDemoNote();
    renderDemo();
    renderError();
    if (state.preview) renderPreview();
    if (state.result) renderResults();
  }

  function updateReferenceForm() {
    const type = $('reference-type').value;
    $('reference-type-hint').textContent = t(type + 'Hint');
    $('reference-mode').querySelector('[value="constant"]').disabled = type !== 'design';
    $('reference-mode').querySelector('[value="profile"]').disabled = type !== 'design';
    $('reference-required-hint').hidden = type === 'design';
    if(type !== 'design') $('reference-mode').value = 'file';
    const mode = $('reference-mode').value;
    const profile = mode === 'profile';
    const track = profile && $('profile-coverage').value === 'track';
    $('constant-fields').hidden = mode !== 'constant';
    $('reference-file-fields').hidden = mode !== 'file';
    $('profile-fields').hidden = !profile;
    const area = $('profile-coverage').value === 'area';
    $('profile-alignment').querySelector('[value="fitted"]').disabled = area;
    if (area) $('profile-alignment').value = 'endpoints';
    $('profile-endpoints').hidden = $('profile-alignment').value !== 'endpoints';
    $('profile-coverage-hint').textContent = t(area ? 'profileAreaHint' : 'profileTrackHint');
    const preprocess = $('survey-preprocess').checked;
    $('survey-preprocess').disabled = Boolean(state.demo);
    $('survey-sounding-field').hidden = !preprocess;
    $('survey-nap-label').hidden = !(profile || preprocess) || (track && preprocess);
    $('reference-note').required = !profile;
    $('reference-note-hint').textContent = t(profile ? 'profileNoteHint' : 'referenceNoteHint');
    $('volume-settings').hidden = $('volume-settings').disabled = profile && track;
    updateRunLabel();
    updateInspectLabel();
  }

  function updateInspectLabel() {
    $('inspect-survey').textContent = t(state.inspecting ? 'inspectRunning'
      : $('survey-preprocess').checked ? 'preprocessInspect' : 'inspectSurvey');
  }

  function updateRunLabel() {
    $('run-label').textContent = t(state.busy && !state.inspecting ? 'running'
      : $('reference-mode').value === 'profile' ? 'profileRun' : 'run');
  }

  function updateSurfaceForm() {
    $('kriging-fields').hidden = $('surface-method').value !== 'kriging';
    $('kriging-manual').hidden = $('kriging-fit').value !== 'manual';
  }

  function resetResults(stale = true) {
    const existed = Boolean(state.result);
    state.result = null;
    state.resultNoteAuto = false;
    state.stale = state.stale || (existed && stale);
    $('stale-note').hidden = !state.stale;
    $('results').hidden = true;
    $('chart-toolbar').hidden = true;
    $('bed-controls').hidden = true;
    $('uncertainty-controls').hidden = true;
    $('chart-footer').hidden = true;
    $('chart').hidden = true;
    $('profile-result').hidden = true;
    if (window.Plotly && $('profile-chart').data) Plotly.purge($('profile-chart'));
    $('chart-empty').hidden = false;
    $('analysis-chart-card').hidden = Boolean(state.preview);
    $('status-text').textContent = t('ready');
    $('workspace-status').className = 'workspace-status';
    // No old export URL remains exposed after input changes.
    ['bundle','cells','geotiff','summary','points','design','comparison'].forEach(key => $('export-' + key).removeAttribute('href'));
    $('profile-export-bundle').removeAttribute('href');
  }

  function showError(key, params = {}, api = false) {
    state.error = {key, params, api};
    renderError();
  }
  function renderError() {
    const box = $('form-error');
    box.hidden = !state.error;
    box.replaceChildren();
    if (!state.error) return;
    box.append(el('strong', t('errorTitle')));
    const message = state.error.api ? t('errors.' + state.error.key) : t(state.error.key);
    box.append(el('span', message.replace('{limit}', state.error.params.limit_mb ?? otherLimitMB)));
    const fieldLabels={surface_method:'surfaceMethod',kriging_model:'variogramModel',kriging_fit:'fitMode',kriging_nugget:'nugget',kriging_partial_sill:'partialSill',kriging_range:'krigingRange',kriging_radius:'krigingRadius',kriging_neighbors:'krigingNeighbors',kriging_max_se:'maxSE',crs:'crs',vertical_datum:'datum',reference_crs:'crs',reference_vertical_datum:'datum',reference_note:'referenceNote',reference_elevation:'refElevation',cell_size:'cellSize',max_edge:'maxEdge',filter_k:'filterK',filter_floor:'filterFloor',neighbors:'neighbors',sigma_current:'sigmaCurrent',sigma_reference:'sigmaReference',reference_mode:'refMode',reference_type:'refType',z_convention:'zConvention'};
    const fields=(state.error.params.fields || []).filter(key=>fieldLabels[key]).map(key=>t(fieldLabels[key]));
    if(fields.length) box.append(el('p',`${t('checkFields')}: ${fields.join(', ')}.`));
  }
  function clearError() { state.error = null; renderError(); }

  function renderDemo() {
    const source = $('demo-source');
    source.hidden = !state.demo;
    source.replaceChildren();
    if (!state.demo) return;
    source.append(el('span', t('measuredData'), 'source-kicker'));
    source.append(el('strong', state.demo.name?.includes('Amsterdam') ? t('demoName') : state.demo.name));
    source.append(el('div', `${t('publisher')}: ${state.demo.publisher || 'Rijkswaterstaat'}`));
    source.append(el('div', `${t('license')}: ${state.demo.license || '—'}`));
    source.append(el('div', `${state.demo.crs} · ${state.demo.vertical_datum} · m`));
    if (safeLink(state.demo.source_url)) {
      const link = el('a', t('sourceLink'));
      link.href = safeLink(state.demo.source_url); link.target = '_blank'; link.rel = 'noopener noreferrer';
      source.append(link);
    }
    source.append(el('p', t('demoLoaded')));
  }

  function fileAllowed(file, role) {
    return role === 'boundary' ? /\.(geojson|json)$/i.test(file.name) : /\.(csv|txt|xyz|tif|tiff|zip)$/i.test(file.name);
  }
  function setFile(role, file) {
    if (state.busy) return;
    clearError();
    if (role === 'survey') {
      if (state.files.survey) $('survey-sounding').value = '';
      $('survey-nap-confirmed').checked = false;
      clearPreview();
    }
    const limitMB = role === 'survey' ? surveyLimitMB : otherLimitMB;
    const tooLarge = file?.size > limitMB * mib;
    if (file && (!fileAllowed(file, role) || tooLarge)) {
      state.files[role] = null; $(role + '-file').value='';
      if(role==='survey'){state.demo=null;updateReferenceForm();renderDemo();}
      if(role==='boundary'){ $('boundary-name').textContent=t('boundaryUpload');$('boundary-name').dataset.i18n='boundaryUpload';$('remove-boundary').hidden=true; }
      else $(role+'-selection').hidden=true;
      resetResults(); showError(tooLarge ? 'file_too_large' : 'invalidType',{limit_mb:limitMB},tooLarge); return;
    }
    state.files[role] = file;
    if (role === 'survey' && file) {
      if (state.demoNoteAuto) {
        $('reference-mode').value = 'profile';
        $('reference-note').value = '';
      }
      state.demo = null; state.demoNoteAuto = false; updateReferenceForm(); renderDemo();
    }
    if (role === 'boundary') {
      $('boundary-name').textContent = file ? file.name : t('boundaryUpload');
      $('boundary-name').dataset.i18n = file ? '' : 'boundaryUpload';
      if (file) delete $('boundary-name').dataset.i18n;
      $('remove-boundary').hidden = !file;
    } else {
      $(role + '-selection').hidden = !file;
      $(role + '-name').textContent = file?.name || '';
    }
    resetResults();
  }

  async function loadDemo() {
    if (state.busy) return;
    clearError();
    clearPreview();
    $('load-demo').disabled = true;
    $('load-demo').querySelector('span').textContent = t('demoLoading');
    try {
      const response = await apiFetch('/api/demo');
      const data = await response.json();
      if (!response.ok) throw new Error('demo');
      state.demo = data;
      state.files.survey = null;
      $('survey-file').value = ''; $('survey-selection').hidden = true;
      $('survey-preprocess').checked = false;
      $('survey-sounding').value = '';
      $('survey-nap-confirmed').checked = false;
      $('crs').value = data.crs;
      $('vertical-datum').value = data.vertical_datum;
      $('z-convention').value = 'elevation';
      $('reference-crs').value = data.crs;
      $('reference-datum').value = data.vertical_datum;
      $('reference-type').value = 'design';
      $('reference-mode').value = 'constant';
      $('reference-elevation').value = data.reference_elevation;
      $('reference-note').value = demoNote(data);
      state.demoNoteAuto = true;
      const defaultIds = {cell_size: 'cell-size', max_edge: 'max-edge', filter_mode: 'filter-mode', filter_k: 'filter-k', filter_floor: 'filter-floor', neighbors: 'neighbors'};
      for (const [key, id] of Object.entries(defaultIds)) if (data.defaults?.[key] !== undefined) $(id).value = data.defaults[key];
      updateReferenceForm(); renderDemo(); resetResults();
    } catch { showError(hosting ? (backend === localEngine ? 'hostLocalOffline' : 'hostOffline') : 'networkError'); }
    finally { $('load-demo').disabled = false; $('load-demo').querySelector('span').textContent = t('demo'); }
  }
  function demoNote(data) {
    return t('demoNote').replace('{elevation}',String(data.reference_elevation)).replace('{datum}',data.vertical_datum);
  }

  function refreshDemoNote() {
    if (!state.demo || !state.demoNoteAuto) return;
    const value = $('reference-elevation').value;
    $('reference-note').value = value.trim() && Number.isFinite(Number(value))
      ? demoNote({reference_elevation: Number(value), vertical_datum: $('vertical-datum').value.trim()}) : '';
  }

  function getConfig() {
    const n = id => Number($(id).value);
    const config = {
      crs: $('crs').value.trim(), vertical_datum: $('vertical-datum').value.trim(), units: 'm', z_convention: $('z-convention').value,
      survey_nap_confirmed: $('survey-nap-confirmed').checked,
      reference_type: $('reference-type').value, reference_mode: $('reference-mode').value,
      reference_elevation: n('reference-elevation'), reference_note: $('reference-note').value.trim(),
      reference_crs: $('reference-crs').value.trim(), reference_vertical_datum: $('reference-datum').value.trim(), reference_units: 'm', reference_z_convention: $('reference-z-convention').value
    };
    if (state.analysisBounds) config.analysis_bounds = state.analysisBounds;
    if (config.reference_mode === 'profile') {
      config.design_profile = {
        code: $('profile-code').value,
        water_level_m_nap: n('profile-water'),
        water_level_confirmed: $('profile-level-confirmed').checked,
        survey_nap_confirmed: config.survey_nap_confirmed,
        coverage: $('profile-coverage').value
      };
      if ($('profile-alignment').value === 'endpoints') {
        config.design_profile.endpoints = ['x1','y1','x2','y2'].map(key => {
          const field = $('profile-' + key);
          return field.value.trim() ? Number(field.value) : NaN;
        });
      }
      config.reference_note ||= `${t('profileMode')} ${config.design_profile.code}`;
      Object.assign(config, {reference_crs:'EPSG:28992', reference_vertical_datum:'NAP',
        reference_z_convention:'elevation', reference_elevation:0});
      if (config.design_profile.coverage === 'track') return config;
    }
    Object.assign(config, {
      cell_size: n('cell-size'), max_edge: n('max-edge'), filter_mode: $('filter-mode').value,
      filter_k: n('filter-k'), filter_floor: n('filter-floor'), neighbors: n('neighbors')
    });
    ['current','reference'].forEach(role => { if ($('sigma-' + role).value.trim()) config['sigma_' + role] = n('sigma-' + role); });
    config.surface_method = $('surface-method').value;
    if (config.surface_method === 'kriging') {
      config.kriging_model = $('kriging-model').value;
      config.kriging_fit = $('kriging-fit').value;
      for (const key of ['neighbors','radius']) config['kriging_'+key] = n('kriging-'+key);
      if (config.kriging_fit === 'manual') {
        config.kriging_nugget = n('kriging-nugget'); config.kriging_partial_sill = n('kriging-partial-sill'); config.kriging_range = n('kriging-range');
      }
      if ($('kriging-max-se').value.trim()) config.kriging_max_se = n('kriging-max-se');
    }
    return config;
  }

  function clearPreview() {
    state.preview = null; state.analysisBounds = null;
    $('survey-preview').hidden = true;
    $('analysis-chart-card').hidden = false;
    $('clear-preview-area').hidden = true;
    if (window.Plotly) Plotly.purge($('survey-preview-chart'));
  }

  function appendSurveyPreprocessing(form) {
    if (!$('survey-preprocess').checked) return true;
    const sounding = $('survey-sounding').files[0];
    if (!sounding) { showError('preprocessSoundingRequired'); return false; }
    if (sounding.size > otherLimitMB * mib) {
      showError('file_too_large', {limit_mb:otherLimitMB}, true);
      return false;
    }
    form.append('sounding', sounding);
    return true;
  }

  async function inspectSurvey() {
    if (state.busy) return;
    if (!state.files.survey) return showError('inspectFileRequired');
    clearError();
    const form = new FormData();
    form.append('survey', state.files.survey);
    for (const [key,id] of [['crs','crs'],['vertical_datum','vertical-datum'],['z_convention','z-convention']]) form.append(key,$(id).value.trim());
    if (!appendSurveyPreprocessing(form)) return;
    resetResults(false);
    state.inspecting = true; setBusy(true);
    try {
      const response = await apiFetch('/api/inspect',{method:'POST',body:form});
      const data = await response.json();
      if (!response.ok) {showError(data.error?.code || 'processing_failed',data.error?.params || {},true);return;}
      state.preview = data; state.analysisBounds = null;
      state.previewView = '3d';
      state.previewCameraRevision += 1;
      $('preview-vertical-scale').value = 'auto';
      ['area-xmin','area-ymin','area-xmax','area-ymax'].forEach((id,i)=>$(id).value=data.bounds[i].toFixed(3));
      renderPreview();
      const preview = $('survey-preview');
      if (preview.getBoundingClientRect().top >= window.innerHeight) preview.scrollIntoView();
    } catch {showError(hosting ? (backend === localEngine ? 'hostLocalOffline' : 'hostOffline') : 'networkError');}
    finally {state.inspecting=false;setBusy(false);}
  }

  function renderPreview() {
    const p=state.preview;
    if (!p) return;
    $('survey-preview').hidden=false;
    $('analysis-chart-card').hidden=!state.result?.summary;
    const stats = [
      ['inputPoints', fmt(p.height_review?.point_count ?? p.point_count, 0)],
      ['previewZRange', `${fmt(p.z_min_m, 3)} ${t('rangeTo')} ${fmt(p.z_max_m, 3)} m`],
      ['previewAboveZero', fmt(p.positive_z_count, 0)],
      ['heightRef', p.vertical_datum],
      ['coordinateRef', p.crs],
      ['previewDisplayed', fmt(p.points.x.length, 0)]
    ];
    if (p.height_review) {
      stats.splice(1,0,['preprocessRetained',fmt(p.point_count,0)],
        ['preprocessExcluded',fmt(p.height_review.withheld_missing_correction_count,0)]);
    }
    const list=$('preview-stats');list.replaceChildren();
    for(const [key,value] of stats){const item=el('div',undefined,'quality-item');item.append(el('dt',t(key)),el('dd',value));list.append(item);}
    $('preview-height-note').hidden = p.z_min_m >= 0 || p.positive_z_count === 0;
    $('preprocess-preview-note').hidden = !p.height_review;
    renderPreviewPlot();
    renderAreaNote();
  }

  // Look across an elongated survey so its height bands are visible on opening.
  function acrossTrackEye(x, y) {
    const meanX = x.reduce((sum,value) => sum+value,0)/x.length;
    const meanY = y.reduce((sum,value) => sum+value,0)/y.length;
    let xx = 0, yy = 0, xy = 0;
    for (let i = 0; i < x.length; i++) {
      const dx = x[i]-meanX, dy = y[i]-meanY;
      xx += dx*dx; yy += dy*dy; xy += dx*dy;
    }
    const angle = .5*Math.atan2(2*xy,xx-yy) + .58*Math.PI;
    return {x:1.65*Math.cos(angle),y:1.65*Math.sin(angle),z:.8};
  }

  function renderPreviewPlot() {
    const p = state.preview;
    if (!p) return;
    const is3d = state.previewView === '3d';
    document.querySelectorAll('[data-preview-view]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.previewView === state.previewView));
    });
    $('preview-3d-controls').hidden = !is3d;
    $('use-preview-area').hidden = is3d;
    const target=$('survey-preview-chart');
    const unit=key=>`${t(key)} (m)`;
    const base = {paper_bgcolor:'#fff', plot_bgcolor:'#fbfcf9',
      font:{family:'sans-serif',size:11,color:'#536d71'}, separators:state.lang==='nl'?',.':'.,',
      uirevision:`${p.sha256}-${state.previewView}-${state.previewCameraRevision}`};
    const hoverXY = `${unit('xAxis')}: %{x:.3f}<br>${unit('yAxis')}: %{y:.3f}<br>`;
    const options = {responsive:true,displayModeBar:false,scrollZoom:true};
    if (!is3d) {
      $('preview-plot-note').textContent = t('previewZoomHint');
      Plotly.react(target,[{type:'scattergl',mode:'markers',x:p.points.x,y:p.points.y,customdata:p.points.z,
        marker:{size:4,color:p.points.z,colorscale:[[0,'#173d49'],[.7,'#398e8b'],[1,'#c69351']],colorbar:{title:{text:unit('zAxis'),side:'right'},thickness:10,len:.8}},
        hovertemplate:`${hoverXY}${unit('zAxis')}: %{customdata:.3f}<extra></extra>`}],
        {...base,margin:{l:72,r:55,t:12,b:56},dragmode:'zoom',
         xaxis:{title:unit('xAxis'),zeroline:false,constrain:'domain'},yaxis:{title:unit('yAxis'),zeroline:false,scaleanchor:'x',scaleratio:1}},options);
      return;
    }

    const traces = [
      {name:t('previewAtOrBelowZero'), color:'#25767c', size:3.5},
      {name:t('previewAboveZero'), color:'#b26a27', size:4.5}
    ].map(({name,color,size}) => ({
      type:'scatter3d', mode:'markers', name, x:[], y:[], z:[],
      marker:{color,size,opacity:.9},
      hovertemplate:`${hoverXY}${unit('zAxis')}: %{z:.3f}<extra></extra>`
    }));
    for (let i = 0; i < p.points.z.length; i++) {
      const trace = traces[p.points.z[i] > 0 ? 1 : 0];
      trace.x.push(p.points.x[i]); trace.y.push(p.points.y[i]); trace.z.push(p.points.z[i]);
    }

    const [xmin,ymin,xmax,ymax] = p.bounds;
    const horizontalSpan = Math.max(xmax-xmin, ymax-ymin, .1);
    const zSpan = p.z_max_m - p.z_min_m;
    const paddedRange = (min,max,pad) => [min-pad,max+pad];
    const ranges = [
      paddedRange(xmin,xmax,horizontalSpan*.05),
      paddedRange(ymin,ymax,horizontalSpan*.05),
      paddedRange(p.z_min_m,p.z_max_m,Math.max(zSpan*.1,.05))
    ];
    const spans = ranges.map(([min,max]) => max-min);
    const auto = zSpan > 1e-9 ? Math.max(1,Math.min(100,Math.round(.4*horizontalSpan/spans[2]))) : 1;
    const factor = $('preview-vertical-scale').value === 'auto' ? auto : 1;
    const scaleNote = factor === 1 ? t('trueProportions') : t('verticalSummary').replace('{factor}',fmt(factor,0));
    $('preview-plot-note').textContent = `${scaleNote}. ${t('previewOrbitHint')}`;
    const scaledSpans = [spans[0], spans[1], spans[2]*factor];
    const longest = Math.max(...scaledSpans);
    const sceneSize = target.clientWidth < 500 ? 1.25 : 1.7;
    const [x,y,z] = scaledSpans.map(span => sceneSize*span/longest);

    const axes = ranges.map((range,i) => ({
      range, title:{text:i === 2 ? unit('zAxis') : t(['xAxisShort','yAxisShort'][i])},
      tickformat:i === 2 ? '~f' : '~s', nticks:i === 2 ? 6 : 4,
      showbackground:true, backgroundcolor:'#f6f8f5', gridcolor:'#dce5df',
      zeroline:i === 2, zerolinecolor:'#a9b8b6'
    }));
    Plotly.react(target,traces.filter(trace=>trace.z.length),{
      ...base, margin:{l:10,r:10,t:34,b:10}, showlegend:p.positive_z_count > 0,
      legend:{orientation:'h',x:0,y:1,xanchor:'left',yanchor:'bottom'},
      scene:{xaxis:axes[0],yaxis:axes[1],zaxis:axes[2],aspectmode:'manual',aspectratio:{x,y,z},
        camera:{eye:acrossTrackEye(p.points.x,p.points.y),projection:{type:'orthographic'}},
        dragmode:'orbit',bgcolor:'#fff'}
    },options);
  }

  function renderAreaNote() {
    if(!state.preview)return;
    const bounds=state.analysisBounds || state.preview.bounds;
    $('clear-preview-area').hidden=!state.analysisBounds;
    $('preview-area-note').textContent=state.analysisBounds ? `${t('selectedArea')}: ${bounds.map(v=>fmt(v,2)).join(', ')} m` : t('fullExtent');
    const c=Number($('cell-size').value);
    const cells=Number.isFinite(c)&&c>0 ? Math.max(1,Math.ceil(bounds[2]/c)-Math.floor(bounds[0]/c))*Math.max(1,Math.ceil(bounds[3]/c)-Math.floor(bounds[1]/c)) : null;
    const limit=state.preview.max_grid_cells ?? 250_000;
    $('preview-grid-note').textContent=cells===null ? t('invalidNumber') : t('previewGridNote')
      .replace('{cells}',fmt(cells,0)).replace('{size}',fmt(c,2)).replace('{limit}',fmt(limit,0));
    $('preview-grid-note').classList.toggle('area-limit',cells>limit);
  }

  function applyArea(bounds) {
    if(state.busy)return;
    if(!bounds.every(Number.isFinite)||!(bounds[0]<bounds[2]&&bounds[1]<bounds[3]))return showError('invalidArea');
    state.analysisBounds=bounds;
    ['area-xmin','area-ymin','area-xmax','area-ymax'].forEach((id,i)=>$(id).value=bounds[i].toFixed(3));
    clearError();resetResults();renderAreaNote();
  }

  async function runAnalysis(event) {
    event.preventDefault();
    if (state.busy) return;
    clearError();
    const config = getConfig();
    const profile = config.design_profile;
    const track = profile?.coverage === 'track';
    if (!state.demo && !state.files.survey) return showError('surveyRequired');
    if (config.reference_mode === 'file' && !state.files.reference) return showError('referenceRequired');
    if (!config.reference_note) { $('reference-note').focus(); return showError('noteRequired'); }
    if (!config.crs) return showError('invalid_crs', {}, true);
    if (!config.vertical_datum) return showError('missing_vertical_datum', {}, true);
    if ((!track && ['cell_size','max_edge','filter_k','filter_floor','neighbors'].some(k => !Number.isFinite(config[k]) || config[k] <= 0)) || (config.reference_mode === 'constant' && (!$('reference-elevation').value.trim() || !Number.isFinite(config.reference_elevation)))) return showError('invalidNumber');
    if (('sigma_current' in config) !== ('sigma_reference' in config) || ['sigma_current','sigma_reference'].some(k => k in config && (!Number.isFinite(config[k]) || config[k] < 0))) return showError('invalidOptional');
    const preprocess = $('survey-preprocess').checked;
    if (profile) {
      if (!$('profile-water').value.trim() || !Number.isFinite(profile.water_level_m_nap)) return showError('profileEnterWater');
      if (profile.endpoints?.some(n => !Number.isFinite(n))) return showError('profile_endpoints', {}, true);
      if (!preprocess && !profile.survey_nap_confirmed) return showError('profile_heights_required', {}, true);
      if (track && preprocess) profile.survey_nap_confirmed = false;
    }
    const form = new FormData();
    if (state.demo) form.append('demo', 'true'); else form.append('survey', state.files.survey);
    if (config.reference_mode === 'file') form.append('reference', state.files.reference);
    if (!track && state.files.boundary) form.append('boundary', state.files.boundary);
    if (!appendSurveyPreprocessing(form)) return;
    if (preprocess && !track && !config.survey_nap_confirmed) return showError('preprocess_volume_heights', {}, true);
    form.append('config', JSON.stringify(config));
    resetResults(false); setBusy(true);
    try {
      const response = await apiFetch('/api/analyze', {method: 'POST', body: form});
      let data;
      try { data = await response.json(); } catch { throw new Error('response'); }
      if (!response.ok) {
        const apiError = data.error || data.detail?.error || data.detail;
        showError(apiError?.code || 'processing_failed', apiError?.params || {}, true);
        return;
      }
      state.result = data;
      state.bedPatchFocused = false;
      state.resultNoteAuto = Boolean(state.demo && state.demoNoteAuto && config.reference_mode === 'constant');
      state.stale = false;
      $('stale-note').hidden = true;
      state.view = 'difference';
      state.profileView = '3d';
      renderResults();
      if (data.profile && $('profile-result').getBoundingClientRect().top >= window.innerHeight) $('profile-result').scrollIntoView();
    } catch { showError(hosting ? (backend === localEngine ? 'hostLocalOffline' : 'hostOffline') : 'networkError'); }
    finally { setBusy(false); }
  }

  function setBusy(busy) {
    state.busy = busy;
    $('setup-fields').disabled = busy;
    $('run-analysis').disabled = busy;
    $('hosted-lock').disabled = busy;
    $('open-public-demo').disabled = busy;
    updateRunLabel();
    updateInspectLabel();
    $('processing-overlay').querySelector('strong').textContent=t(state.inspecting ? 'inspectRunning' : 'running');
    for(const id of ['use-preview-area','apply-preview-area','clear-preview-area'])$(id).disabled=busy;
    $('run-icon').textContent = busy ? '◌' : '↗';
    $('processing-overlay').hidden = !busy;
    $('workspace-status').className = 'workspace-status' + (busy ? ' processing' : state.result ? ' complete' : '');
    $('status-text').textContent = t(busy ? 'loadingStatus' : state.result ? 'resultsReady' : 'ready');
    $('analysis-form').setAttribute('aria-busy', String(busy));
  }

  function renderDesignProfile(result) {
    const m = result.profile.metadata;
    $('profile-result').hidden = false;
    $('profile-result-note').textContent = t(m.alignment === 'fitted' ? 'profileFitResult' : 'profileEndpointsResult');
    $('profile-provisional').hidden = !m.provisional;
    const list = $('profile-stats');
    list.replaceChildren();
    const stats = [
      ['profileCode', m.code === 'L8A' ? 'L8a' : m.code],
      ['profileWater', `${fmt(m.water_level_m_nap, 3)}${m.water_level_confirmed ? '' : ` · ${t('profileAssumed')}`}`],
      ['profileBed', `${fmt(m.bed_elevation_m_nap, 3)} m NAP`],
      ['profileReachLength', `${fmt(m.length_m)} m`],
      ['profileCompared', fmt(m.compared_count, 0)],
      ['profileWithheld', fmt(m.withheld_count, 0)]
    ];
    if (m.outside_design_count) stats.push(['profileOutside', fmt(m.outside_design_count, 0)]);
    for (const [key, value] of stats) {
      const item = el('div', undefined, 'quality-item');
      item.append(el('dt', t(key)), el('dd', value));
      list.append(item);
    }
    for (const [id, key] of [['export-design','design'], ['export-comparison','comparison'], ['profile-export-bundle','bundle']]) {
      const url = result.exports?.[key];
      setExport($(id), url);
    }
    renderDesignChart(result);
  }

  function renderDesignChart(result) {
    if (!result?.profile || !window.Plotly) return;
    const {metadata: m, geometry: g, points: p} = result.profile;
    const chart = $('profile-chart');
    const along = state.profileView === 'along';
    document.querySelectorAll('[data-profile-view]').forEach(button =>
      button.setAttribute('aria-pressed', String(button.dataset.profileView === state.profileView)));
    const base = {
      paper_bgcolor:'#fff', plot_bgcolor:'#fbfcf9',
      margin:{l:along ? 65 : 0,r:along ? 20 : 0,t:10,b:along ? 55 : 10},
      font:{family:'Inter, system-ui, sans-serif',size:10,color:'#536d71'},
      legend:{orientation:'h',y:along ? 1.12 : 0},
      separators:state.lang === 'nl' ? ',.' : '.,',
      uirevision:result.id + state.profileView,
    };
    const pointHover = `%{y:.2f} m NAP<br>ΔZ %{customdata:+.2f} m<extra>${t('profileObservations')}</extra>`;
    const pointColor = '#173d49';
    if (along) {
      const fitted = m.alignment === 'fitted';
      const reference = fitted
        ? {x:g.station,y:g.station.map(() => m.bed_elevation_m_nap),mode:'lines',line:{color:'#b58240',dash:'dash'}}
        : {x:p.station,y:p.design,mode:'markers',marker:{color:'#b58240',size:5}};
      $('profile-scale-note').textContent = '';
      Plotly.react(chart, [
        {type:'scatter',...reference,name:t(fitted ? 'profileBed' : 'profilePointDesign')},
        {type:'scatter',mode:'markers',x:p.station,y:p.z,name:t('profileObservations'),
          marker:{size:4,color:pointColor},customdata:p.z.map((z,i)=>z-p.design[i]),hovertemplate:pointHover}
      ], {...base,xaxis:{title:{text:t('profileDistance')}},yaxis:{title:{text:t('profileHeight')}}}, {responsive:true,displaylogo:false});
      return;
    }
    const traces = [{
      type:'surface',x:g.offset.map(() => g.station),y:g.offset.map(o => [o,o]),z:g.elevation.map(z => [z,z]),
      opacity:.44,showscale:false,showlegend:true,colorscale:[[0,'#c59862'],[1,'#c59862']],
      lighting:{ambient:1,diffuse:0},name:t('refTrace'),hovertemplate:'%{z:.2f} m NAP<extra></extra>'
    }];
    const mesh = result.bed_mesh;
    const samples = result.bed_samples;
    if (mesh || samples) {
      const bed = mesh || samples;
      const [x0,y0] = m.start_xy;
      const [dx,dy] = m.direction_xy;
      const x = bed.x.map((x,i) => (x-x0)*dx+(bed.y[i]-y0)*dy);
      const y = bed.x.map((x,i) => (bed.y[i]-y0)*dx-(x-x0)*dy);
      if (mesh) {
        const i = Array.from({length:x.length/3}, (_,face)=>3*face);
        traces.push({type:'mesh3d',x,y,z:bed.bed,i,j:i.map(v=>v+1),k:i.map(v=>v+2),
          color:'#36877e',opacity:.83,lighting:{ambient:1,diffuse:0},showlegend:true,name:t('bedTrace')});
      } else {
        traces.push({type:'scatter3d',mode:'markers',x,y,z:bed.bed,
          marker:{color:'#36877e',size:4},name:t('bedSamples')});
      }
    }
    traces.push({type:'scatter3d',mode:'markers',x:p.station,y:p.offset,z:p.z,
      marker:{size:2.5,color:pointColor},name:t('profileObservations'),
      customdata:p.x.map((x,i)=>[x,p.y[i],p.z[i]-p.design[i]]),
      hovertemplate:'%{z:.2f} m NAP<br>RD %{customdata[0]:.2f}, %{customdata[1]:.2f}<br>ΔZ %{customdata[2]:+.2f} m<extra></extra>'});
    const halfWidth = m.waterline_width_m/2;
    const zRange = [Math.min(m.bed_elevation_m_nap,...p.z) - .1, Math.max(m.water_level_m_nap,...p.z) + .1];
    for (const z of (mesh || samples)?.bed || []) {
      zRange[0] = Math.min(zRange[0],z);
      zRange[1] = Math.max(zRange[1],z);
    }
    const spans = [m.length_m,2*halfWidth,zRange[1]-zRange[0]];
    const longest = Math.max(...spans);
    const across = Math.max(1, .30*longest/spans[1]), up = Math.max(1,.30*longest/spans[2]);
    const broad = across * spans[1] / longest > .6;
    $('profile-scale-note').textContent = t('profileScale').replace('{across}',fmt(across)).replace('{up}',fmt(up));
    Plotly.react(chart, traces, {...base, scene:{
      xaxis:{title:{text:t('profileAlongAxis')},nticks:5,range:[0,m.length_m]},
      yaxis:{title:{text:t('profileOffset')},nticks:4,range:[-halfWidth,halfWidth]},
      zaxis:{title:{text:t('profileHeight')},nticks:4,range:zRange},
      aspectmode:'manual',aspectratio:{x:spans[0]/longest,y:across*spans[1]/longest,z:up*spans[2]/longest},
      camera:{eye:broad ? {x:.62,y:-1.55,z:.72} : {x:.38,y:chart.clientWidth < 500 ? -1.22 : -1.02,z:.54}}
    }}, {responsive:true,displaylogo:false});
  }

  function renderResults() {
    const r = state.result;
    if (!r) return;
    if (r.profile) renderDesignProfile(r);
    const s = r.summary;
    if (!s) { $('analysis-chart-card').hidden = true; return; }
    const isKriging = s.surface_method === 'kriging';
    $('uncertainty-view').hidden = !isKriging;
    if (!isKriging && state.view === 'uncertainty') state.view = 'difference';
    const hasReferenceSE = r.provenance.surface_generation.reference.method === 'ordinary_kriging';
    $('reference-uncertainty-option').hidden = !hasReferenceSE;
    if (!hasReferenceSE) $('uncertainty-role').value = 'bed';
    $('resolved-method').textContent = ['bed','reference'].map(role => {
      const m = r.provenance.surface_generation[role];
      return t(role === 'bed' ? 'stepData' : 'stepReference') + ': ' + (m.method === 'ordinary_kriging'
        ? `${t('krigingMethod')} · ${t(m.variogram_model)} · ${t('resolvedParameters')}: ${t('nugget')} ${fmt(m.nugget_m2,5)}, ${t('partialSill')} ${fmt(m.partial_sill_m2,5)}, ${t('krigingRange')} ${fmt(m.range_m,3)}`
        : t({constant:'constant', design_profile:'profileMode', linear_tin:'tinMethod'}[m.method]));
    }).join(' | ');
    $('results').hidden = false; $('chart-empty').hidden = true;
    $('analysis-chart-card').hidden = false;
    $('chart').hidden = false; $('chart-toolbar').hidden = false; $('chart-footer').hidden = false;
    $('metric-above').textContent = fmt(s.positive_volume_m3);
    $('metric-below').textContent = fmt(Math.abs(s.negative_volume_m3));
    $('metric-area').textContent = fmt(s.valid_area_m2, 0);
    $('metric-coverage').textContent = fmt(s.coverage_percent);
    $('result-interpretation').textContent = t(s.reference_type + 'Result');
    $('result-reference-note').textContent = state.resultNoteAuto
      ? demoNote({reference_elevation: r.provenance.configuration.reference_elevation, vertical_datum: s.vertical_datum})
      : s.reference_note;
    $('chart-crs').textContent = `${s.crs} · ${s.vertical_datum} · m`;
    $('chart-summary').textContent = `${fmt(s.valid_cells, 0)} / ${fmt(s.grid_cells, 0)} ${t('validCells').toLowerCase()}`;
    const quality = [
      ['inputPoints', s.input_points, 'int'], ['acceptedPoints', s.accepted_points, 'int'],
      ['flaggedPoints', s.flagged_points, 'int'], ['duplicatePoints', s.duplicate_points, 'int'],
      ['gridResolution', s.cell_size_m, 'm'], ['meanDifference', s.mean_difference_m, 'm'],
      ['minDifference', s.min_difference_m, 'm'], ['maxDifference', s.max_difference_m, 'm'],
      ['coordinateRef', s.crs, 'text'], ['heightRef', s.vertical_datum, 'text'],
      ['netVolume', s.net_volume_m3, 'm³'], ['lod95', s.lod95_m, 'm']
    ];
    if (isKriging) {
      quality.push(['predictionExcluded',s.prediction_excluded_area_m2,'m²']);
      for (const [reason,area] of Object.entries(s.exclusion_areas_m2 || {})) quality.push(['excluded_'+reason,area,'m²']);
    }
    if (s.outside_analysis_area_points) quality.splice(1,0,['selectedPoints',s.selected_points,'int']);
    if (s.withheld_height_correction_points) quality.splice(1,0,['preprocessExcluded',s.withheld_height_correction_points,'int']);
    if (s.detectable_positive_volume_m3 != null) quality.push(['detectableAbove', s.detectable_positive_volume_m3, 'm³'], ['detectableBelow', Math.abs(s.detectable_negative_volume_m3), 'm³']);
    const list = $('quality-values'); list.replaceChildren();
    for (const [key, value, unit] of quality) {
      const item = el('div', undefined, 'quality-item');
      item.append(el('dt', t(key)));
      const content = value == null ? t('noLod') : unit === 'text' ? String(value) : fmt(value, unit === 'int' ? 0 : 2) + (unit === 'int' ? '' : ' ' + unit);
      item.append(el('dd', content)); list.append(item);
    }
    const warnings = $('warning-list'); warnings.replaceChildren();
    for (const warning of r.warnings || []) warnings.append(el('li', t('warningMessages.' + warning.code)));
    warnings.closest('section').hidden = !(r.warnings?.length);
    for (const [key, url] of Object.entries(r.exports || {})) {
      const node = $('export-' + key);
      if (!node) continue;
      setExport(node, url);
    }
    renderProvenance(r);
    document.querySelectorAll('[data-view]').forEach(node => node.setAttribute('aria-pressed', String(node.dataset.view === state.view)));
    renderChart();
  }

  function renderProvenance(r) {
    const box = $('result-source'); box.replaceChildren();
    const meta = r.provenance || {};
    const source = meta.source || meta.dataset || state.demo;
    box.append(el('span', t(state.demo ? 'realData' : 'userData')));
    if (source && typeof source === 'object') {
      const url = source.source_url || source.url;
      if (source.publisher) box.append(document.createTextNode(` · ${source.publisher}`));
      if (source.license) box.append(document.createTextNode(` · ${source.license}`));
      if (safeLink(url)) { box.append(document.createTextNode(' · ')); const a = el('a', t('sourceLink')); a.href = safeLink(url); a.target = '_blank'; a.rel = 'noopener noreferrer'; box.append(a); }
    }
  }

  function focusBedMesh(mesh, cellSize) {
    const [x,y] = mesh.focus;
    const radius = 2 * cellSize;
    const local = {x:[],y:[],bed:[],reference:[]};
    const keys = Object.keys(local);
    for (let i=0; i<mesh.x.length; i+=3) {
      if (Math.abs(mesh.x[i]-x)>radius || Math.abs(mesh.y[i]-y)>radius) continue;
      for (const key of keys) local[key].push(...mesh[key].slice(i,i+3));
    }
    return local;
  }

  function renderChart() {
    if (!state.result?.summary || !window.Plotly) return;
    const r = state.result, g = r.grid, s = r.summary;
    state.plotWidth=$('chart').clientWidth;
    $('bed-controls').hidden = state.view !== 'bed';
    $('uncertainty-controls').hidden = state.view !== 'uncertainty';
    $('chart').setAttribute('role','img'); $('chart').setAttribute('aria-label',t(state.view));
    $('chart-summary').textContent = `${fmt(s.valid_cells, 0)} / ${fmt(s.grid_cells, 0)} ${t('validCells').toLowerCase()}`;
    delete $('chart-summary').dataset.verticalScale;
    const unitTitle = key => `${t(key)} (m)`;
    const font = {family:'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',size:10,color:'#536d71'};
    const base = {paper_bgcolor:'#fff',plot_bgcolor:'#fbfcf9',font,margin:{l:72,r:58,t:25,b:59},hoverlabel:{bgcolor:'#173d49',font:{color:'#fff',size:11},bordercolor:'#173d49'},separators:state.lang==='nl'?',.':'.,',uirevision:r.id+state.view+state.cameraRevision};
    const axes = {showgrid:true,gridcolor:'#e8eeea',zeroline:false,tickfont:{size:9},automargin:true};
    let data, layout;
    if (state.view === 'bed') {
      const focused = state.bedPatchFocused;
      const mesh = r.bed_mesh && (focused ? focusBedMesh(r.bed_mesh, s.cell_size_m) : r.bed_mesh);
      const samples = r.bed_samples;
      const patches = mesh || samples;
      const focusButton = $('focus-bed-patch');
      focusButton.hidden = !mesh;
      focusButton.textContent = t(focused ? 'bedFullReach' : 'bedFocusPatch');
      const sparseNote = $('bed-sparse-note');
      sparseNote.hidden = !patches;
      if (mesh) sparseNote.textContent = focused ? t('bedFocused')
        : t('bedPatches').replace('{count}',fmt(mesh.cell_count,0));
      else if (samples) sparseNote.textContent = t('bedSparse').replace('{count}',fmt(samples.x.length,0));
      const hover = key => `${unitTitle('xAxis')}: %{x:.2f}<br>${unitTitle('yAxis')}: %{y:.2f}<br>${unitTitle('zAxis')}: %{z:.2f}<extra>${t(key)}</extra>`;
      const extent = values => values.reduce(([min,max],v) => [Math.min(min,v),Math.max(max,v)],[Infinity,-Infinity]);
      const [xMin,xMax]=patches ? extent(patches.x) : [g.x[0],g.x.at(-1)];
      const [yMin,yMax]=patches ? extent(patches.y) : [g.y.at(-1),g.y[0]];
      const xyPadding = patches ? Math.max(xMax-xMin,yMax-yMin,s.cell_size_m)*.04 : 0;
      const xSpan=Math.max(xMax-xMin+2*xyPadding,s.cell_size_m), ySpan=Math.max(yMax-yMin+2*xyPadding,s.cell_size_m);
      let zMin=Infinity,zMax=-Infinity;
      const rows = patches ? [patches.bed,patches.reference] : [...g.bed,...g.reference];
      for(const row of rows) for(const value of row) if(value!==null&&Number.isFinite(value)){zMin=Math.min(zMin,value);zMax=Math.max(zMax,value);}
      const rawZSpan=zMax-zMin;
      const zPadding=Math.max(rawZSpan*.08,.05);
      const zRange=[zMin-zPadding,zMax+zPadding], zSpan=zRange[1]-zRange[0];
      const autoFactor=rawZSpan<=1e-9 ? 1 : Math.max(1,Math.min(100,Math.round(.32*Math.max(xSpan,ySpan)/zSpan)));
      const factor=state.verticalScale==='auto' ? autoFactor : Number(state.verticalScale);
      const scaledZSpan=zSpan*factor;
      const longest=Math.max(xSpan,ySpan,scaledZSpan,1);
      const sceneScale=state.plotWidth<500 ? 1.2 : 1.9;
      $('chart-summary').dataset.verticalScale=String(factor);
      $('chart-summary').textContent=factor===1 ? t('trueProportions') : t('verticalSummary').replace('{factor}',fmt(factor,0));
      $('vertical-scale-note').dataset.factor=String(factor);
      $('vertical-scale-note').textContent=t('verticalScaleNote').replace('{factor}',fmt(factor,0));
      const contourStep=Math.max(.1,Number((Math.max(rawZSpan,.1)/8).toPrecision(1)));
      const colorscale = [[0,'#163e51'],[.35,'#2e7f8a'],[.7,'#8bbfa9'],[1,'#d8dfb3']];
      const colorbar = {title:{text:unitTitle('zAxis'),side:'right',font:{size:10}},thickness:10,len:.7,tickfont:{size:9}};
      if (mesh) {
        const i = Array.from({length:mesh.x.length/3}, (_,face) => 3*face);
        const faces = {type:'mesh3d',x:mesh.x,y:mesh.y,i,j:i.map(v=>v+1),k:i.map(v=>v+2),
          lighting:{ambient:1,diffuse:0,specular:0},showlegend:true,flatshading:true};
        data = [
          {...faces,z:mesh.bed,intensity:mesh.bed,colorscale,colorbar,showscale:true,
           legendgroup:'bed',name:t('bedTrace'),hovertemplate:hover('bedTrace')},
          {...faces,z:mesh.reference,color:'#b58240',opacity:.65,showscale:false,
           legendgroup:'reference',name:t('refTrace'),hovertemplate:hover('refTrace')}
        ];
        if (!focused) {
          // Keep subpixel patches visible without widening the surface itself.
          for (const [role,color] of [['bed','#216e76'],['reference','#b58240']]) {
            const edges = values => i.flatMap(v => [values[v],values[v+1],values[v+2],values[v],null]);
            data.push({type:'scatter3d',mode:'lines',x:edges(mesh.x),y:edges(mesh.y),z:edges(mesh[role]),
              line:{color,width:2},legendgroup:role,showlegend:false,hoverinfo:'skip'});
          }
        }
      } else if (samples) {
        data = [
          {type:'scatter3d',mode:'markers',x:samples.x,y:samples.y,z:samples.bed,name:t('bedSamples'),
           marker:{color:'#216e76',size:4},hovertemplate:hover('bedSamples')},
          {type:'scatter3d',mode:'markers',x:samples.x,y:samples.y,z:samples.reference,name:t('refSamples'),
           marker:{color:'#ac692b',size:3,symbol:'circle-open'},hovertemplate:hover('refSamples')}
        ];
      } else {
        data = [{type:'surface',x:g.x,y:g.y,z:g.bed,name:t('bedTrace'),
          colorscale,colorbar,
          lighting:{ambient:.45,diffuse:.8,specular:.2,roughness:.8},lightposition:{x:100,y:-200,z:1000},
          contours:{z:{show:true,usecolormap:false,color:'rgba(23,61,73,.38)',width:1,start:Math.ceil(zMin/contourStep)*contourStep,end:Math.floor(zMax/contourStep)*contourStep,size:contourStep}},
          hovertemplate:hover('bedTrace'),connectgaps:false},
          {type:'surface',x:g.x,y:g.y,z:g.reference,name:t('refTrace'),opacity:.2,showscale:false,
           colorscale:[[0,'#cd9653'],[1,'#cd9653']],lighting:{ambient:1,diffuse:0},
           hovertemplate:`${unitTitle('zAxis')}: %{z:.2f}<extra>${t('refTrace')}</extra>`,connectgaps:false}];
      }
      const sceneAxis={tickfont:{size:9},gridcolor:'#dce5df',showbackground:true,backgroundcolor:'#f6f8f5',showline:true,linecolor:'#9bada5',zeroline:false};
      layout = {...base,margin:{l:24,r:samples?24:52,t:patches?34:14,b:34},
        showlegend:Boolean(patches),legend:{orientation:'h',x:0,y:1,xanchor:'left',yanchor:'bottom'},
        scene:{
        xaxis:{...sceneAxis,title:{text:state.plotWidth<500?t('xAxisShort'):unitTitle('xAxis'),font:{size:10}},nticks:3,tickformat:'.0f',range:[xMin-xyPadding,xMin-xyPadding+xSpan]},
        yaxis:{...sceneAxis,title:{text:state.plotWidth<500?t('yAxisShort'):unitTitle('yAxis'),font:{size:10}},nticks:4,tickformat:'.0f',range:[yMin-xyPadding,yMin-xyPadding+ySpan]},
        zaxis:{...sceneAxis,title:{text:unitTitle('zAxis'),font:{size:10}},showticklabels:true,nticks:5,tickformat:'.1f',range:zRange},
        aspectmode:'manual',aspectratio:{x:sceneScale*xSpan/longest,y:sceneScale*ySpan/longest,z:sceneScale*scaledZSpan/longest},
        camera:{eye:patches?{...acrossTrackEye(patches.x,patches.y),z:1.2}:{x:1.45,y:-1.65,z:.95},up:{x:0,y:0,z:1},projection:{type:patches?'orthographic':'perspective'}},dragmode:'orbit',bgcolor:'#fff'}};
      // Only the scene aspect changes. Z arrays, hover values and volume remain in metres.
    } else if (state.view === 'uncertainty') {
      const role = $('uncertainty-role').value;
      let seMax = 0.001; for (const row of g[role+'_standard_error']) for (const value of row) if (value !== null && Number.isFinite(value)) seMax = Math.max(seMax,value);
      data = [{type:'heatmap',x:g.x,y:g.y,z:g[role+'_standard_error'],zmin:0,zmax:seMax,zauto:false,
        colorscale:[[0,'#e5f3ed'],[.5,'#539b96'],[1,'#8c5538']],hoverongaps:false,connectgaps:false,
        colorbar:{title:{text:t('standardError')+' (m)',side:'right'},thickness:12},
        hovertemplate:`X: %{x:.2f} m<br>Y: %{y:.2f} m<br>${t('standardError')}: %{z:.3f} m<extra></extra>`}];
      layout = {...base,xaxis:{...axes,title:unitTitle('xAxis'),constrain:'domain'},yaxis:{...axes,title:unitTitle('yAxis'),scaleanchor:'x',scaleratio:1}};
    } else if (state.view === 'map') {
      const p = r.points, flags = p.flagged || [];
      const accepted = {x:[],y:[],z:[]}, marked = {x:[],y:[],z:[]};
      for (let i=0;i<p.x.length;i++) { const target = flags[i] ? marked : accepted; target.x.push(p.x[i]); target.y.push(p.y[i]); target.z.push(p.z[i]); }
      data = [{type:'scattergl',mode:'markers',x:accepted.x,y:accepted.y,customdata:accepted.z,name:t('pointTrace'),marker:{size:4,color:accepted.z,colorscale:[[0,'#183e51'],[.5,'#398e8b'],[1,'#b9d5a9']],opacity:.8,colorbar:{title:{text:unitTitle('zAxis'),side:'right',font:{size:10}},thickness:10,len:.72,tickfont:{size:9}}},hovertemplate:`${unitTitle('xAxis')}: %{x:.2f}<br>${unitTitle('yAxis')}: %{y:.2f}<br>${unitTitle('zAxis')}: %{customdata:.2f}<extra>${t('pointTrace')}</extra>`}];
      if (marked.x.length) data.push({type:'scattergl',mode:'markers',x:marked.x,y:marked.y,customdata:marked.z,name:t('flaggedTrace'),marker:{size:6,color:'#cf8743',symbol:'x'},hovertemplate:`${unitTitle('zAxis')}: %{customdata:.2f}<extra>${t('flaggedTrace')}</extra>`});
      layout = {...base,xaxis:{...axes,title:unitTitle('xAxis'),constrain:'domain'},yaxis:{...axes,title:unitTitle('yAxis'),scaleanchor:'x',scaleratio:1},showlegend:Boolean(marked.x.length),legend:{orientation:'h',y:-.2,x:0,font:{size:9}}};
    } else {
      const limit = Math.max(Math.abs(s.min_difference_m),Math.abs(s.max_difference_m),.01);
      data = [{type:'heatmap',x:g.x,y:g.y,z:g.difference,colorscale:[[0,'#237f93'],[.35,'#91c4c5'],[.5,'#f7f6ef'],[.65,'#e2c38f'],[1,'#bc7437']],zmin:-limit,zmax:limit,zmid:0,hoverongaps:false,connectgaps:false,colorbar:{title:{text:unitTitle('differenceAxis'),side:'right',font:{size:10}},thickness:10,len:.74,tickfont:{size:9}},hovertemplate:`${unitTitle('xAxis')}: %{x:.2f}<br>${unitTitle('yAxis')}: %{y:.2f}<br>${unitTitle('differenceAxis')}: %{z:.3f}<extra></extra>`}];
      layout = {...base,xaxis:{...axes,title:unitTitle('xAxis'),constrain:'domain'},yaxis:{...axes,title:unitTitle('yAxis'),scaleanchor:'x',scaleratio:1},showlegend:false};
    }
    Plotly.react($('chart'),data,layout,{responsive:true,displayModeBar:false,scrollZoom:true,displaylogo:false});
  }

  document.querySelectorAll('[data-language]').forEach(button => button.addEventListener('click', () => {
    state.lang = button.dataset.language;
    localStorage.setItem('ease-language', state.lang);
    translate();
  }));
  document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {
    state.view = button.dataset.view;
    document.querySelectorAll('[data-view]').forEach(node => node.setAttribute('aria-pressed', String(node === button)));
    renderChart();
  }));
  $('uncertainty-role').addEventListener('change',renderChart);
  $('vertical-scale').addEventListener('change', event => {
    state.verticalScale=event.target.value;
    renderChart();
  });
  $('reset-bed-view').addEventListener('click', () => {
    state.cameraRevision+=1;
    renderChart();
  });
  $('focus-bed-patch').addEventListener('click', () => {
    state.bedPatchFocused = !state.bedPatchFocused;
    state.cameraRevision += 1;
    renderChart();
  });
  ['survey','reference'].forEach(role => {
    const zone = $(role + '-drop');
    $(role + '-file').addEventListener('change', event => setFile(role, event.target.files[0] || null));
    for (const name of ['dragenter','dragover']) zone.addEventListener(name, event => { event.preventDefault(); if (!state.busy) zone.classList.add('dragover'); });
    for (const name of ['dragleave','drop']) zone.addEventListener(name, event => { event.preventDefault(); zone.classList.remove('dragover'); });
    zone.addEventListener('drop', event => { if (event.dataTransfer.files.length) setFile(role, event.dataTransfer.files[0]); });
  });
  document.querySelectorAll('[data-remove]').forEach(button => button.addEventListener('click', () => { const role=button.dataset.remove; $(role+'-file').value=''; setFile(role,null); }));
  $('boundary-file').addEventListener('change', event => setFile('boundary',event.target.files[0] || null));
  $('survey-sounding').addEventListener('change', () => {
    $('survey-nap-confirmed').checked = false;
    clearError(); clearPreview(); updateReferenceForm(); resetResults();
  });
  document.querySelectorAll('[data-profile-view]').forEach(button => button.addEventListener('click', () => {
    state.profileView = button.dataset.profileView;
    renderDesignChart(state.result);
  }));
  $('remove-boundary').addEventListener('click', () => { $('boundary-file').value=''; setFile('boundary',null); });
  $('load-demo').addEventListener('click',loadDemo);
  $('inspect-survey').addEventListener('click',inspectSurvey);
  document.querySelectorAll('[data-preview-view]').forEach(button => button.addEventListener('click', () => {
    state.previewView = button.dataset.previewView;
    renderPreviewPlot();
  }));
  $('preview-vertical-scale').addEventListener('change',renderPreviewPlot);
  $('reset-preview-camera').addEventListener('click',() => {
    state.previewCameraRevision += 1;
    renderPreviewPlot();
  });
  $('use-preview-area').addEventListener('click',()=>{
    if (state.previewView !== 'plan') return;
    const layout=$('survey-preview-chart')._fullLayout;
    if(layout?.xaxis && layout?.yaxis)applyArea([Math.min(...layout.xaxis.range),Math.min(...layout.yaxis.range),Math.max(...layout.xaxis.range),Math.max(...layout.yaxis.range)]);
  });
  $('apply-preview-area').addEventListener('click',()=>applyArea(['area-xmin','area-ymin','area-xmax','area-ymax'].map(id=>$(id).value.trim()?Number($(id).value):NaN)));
  $('clear-preview-area').addEventListener('click',()=>{state.analysisBounds=null;resetResults();renderAreaNote();});
  $('analysis-form').addEventListener('submit',runAnalysis);
  $('setup-fields').addEventListener('input', event => {
    if (event.target.type === 'file') return;
    if (['crs','vertical-datum','z-convention','survey-preprocess'].includes(event.target.id)) {
      $('survey-nap-confirmed').checked = false;
      clearPreview();
    }
    if (event.target.id === 'reference-note') state.demoNoteAuto=false;
    if (['reference-type','reference-mode'].includes(event.target.id) && state.demoNoteAuto) { $('reference-note').value=''; state.demoNoteAuto=false; }
    refreshDemoNote();
    clearError(); updateReferenceForm(); updateSurfaceForm(); resetResults();
    renderAreaNote();
  });
  $('setup-fields').addEventListener('change', event => { if (event.target.type !== 'file') { updateReferenceForm(); updateSurfaceForm(); resetResults(); } });
  if (window.ResizeObserver) new ResizeObserver(() => {
    if (!state.result?.summary || !window.Plotly) return;
    if (Math.abs($('chart').clientWidth-state.plotWidth)>1) renderChart();
    else Plotly.Plots.resize($('chart'));
  }).observe($('chart'));
  if (window.ResizeObserver) new ResizeObserver(()=>{if(state.preview&&window.Plotly)Plotly.Plots.resize($('survey-preview-chart'));}).observe($('survey-preview-chart'));
  if (hosting) {
    $('hosted-target').value = serverOrigin ? 'server' : 'local';
    $('hosted-target').addEventListener('change', connectionCopy);
    $('open-public-demo').addEventListener('click', loadPublicDemo);
    $('hosted-method').addEventListener('change', () => { if (!accessKey) loadPublicDemo(); });
    $('hosted-login').addEventListener('submit', unlockHosted);
    $('hosted-lock').addEventListener('click', lockHosted);
    hostStatus('hostDemoReady');
  }
  translate();
  if (hosting) {
    const query = new URLSearchParams(location.search);
    if (query.has('analysis')) $('hosted-access').open = true;
    const demo = query.get('demo');
    if (demo === 'kriging') $('hosted-method').value = 'kriging';
    if (demo !== null) loadPublicDemo();
  }
})();
