// PWA cámara de vigilancia: captura periódica y envío al servidor.
// Pensada para máxima retrocompatibilidad (sin frameworks, ES5-ish).

(function () {
  var video = document.getElementById('preview');
  var canvas = document.getElementById('canvas');
  var startBtn = document.getElementById('startBtn');
  var stopBtn = document.getElementById('stopBtn');
  var baselineBtn = document.getElementById('baselineBtn');
  var camInput = document.getElementById('camName');
  var statusText = document.getElementById('statusText');
  var dot = document.getElementById('dot');
  var logEl = document.getElementById('log');

  var stream = null;
  var timer = null;
  var wakeLock = null;
  var sending = false;
  var cfg = { capture_interval_seconds: 3, jpeg_quality: 0.6 };

  // --- Nombre de la cámara: ?cam= en la URL > localStorage > vacío ---
  function urlCam() {
    var m = location.search.match(/[?&]cam=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }
  function getCam() {
    var v = (camInput.value || '').trim();
    return v || 'default';
  }
  camInput.value = urlCam() || localStorage.getItem('cameraName') || '';
  camInput.addEventListener('change', function () {
    localStorage.setItem('cameraName', camInput.value.trim());
  });

  function log(msg) {
    var t = new Date().toLocaleTimeString();
    logEl.innerHTML = '[' + t + '] ' + msg + '<br>' + logEl.innerHTML;
  }

  function setStatus(text, cls) {
    statusText.textContent = text;
    dot.className = 'dot' + (cls ? ' ' + cls : '');
  }

  function loadConfig() {
    return fetch('config').then(function (r) { return r.json(); })
      .then(function (c) { cfg = c; log('Config: cada ' + c.capture_interval_seconds + 's, IA ' + (c.ai_enabled ? 'ON' : 'OFF')); })
      .catch(function () { log('No pude leer /config, uso valores por defecto'); });
  }

  async function requestWakeLock() {
    try {
      if ('wakeLock' in navigator) {
        wakeLock = await navigator.wakeLock.request('screen');
        log('Pantalla bloqueada como activa (wake lock)');
      } else {
        log('Sin Wake Lock API: desactiva el auto-bloqueo manualmente');
      }
    } catch (e) { log('Wake lock no disponible'); }
  }

  function releaseWakeLock() {
    if (wakeLock) { try { wakeLock.release(); } catch (e) {} wakeLock = null; }
  }

  // Re-adquirir el wake lock al volver a primer plano (iOS lo suelta).
  document.addEventListener('visibilitychange', function () {
    if (wakeLock !== null && document.visibilityState === 'visible' && stream) {
      requestWakeLock();
    }
  });

  function startCamera() {
    return navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' }, audio: false
    }).then(function (s) {
      stream = s;
      video.srcObject = s;
    });
  }

  function captureBlob() {
    return new Promise(function (resolve) {
      var w = video.videoWidth, h = video.videoHeight;
      if (!w || !h) { resolve(null); return; }
      canvas.width = w; canvas.height = h;
      canvas.getContext('2d').drawImage(video, 0, 0, w, h);
      canvas.toBlob(function (blob) { resolve(blob); }, 'image/jpeg', cfg.jpeg_quality || 0.6);
    });
  }

  function sendFrame() {
    if (sending) return;
    sending = true;
    captureBlob().then(function (blob) {
      if (!blob) { sending = false; return; }
      var fd = new FormData();
      fd.append('file', blob, 'frame.jpg');
      fd.append('camera', getCam());
      return fetch('upload', { method: 'POST', body: fd })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          if (res.status === 'motion') {
            setStatus('¡Movimiento! ' + Math.round(res.score * 100) + '%', 'motion');
            var extra = res.description ? ' — ' + res.description : '';
            var alertTxt = res.alert && res.alert.sent ? ' (email enviado)'
              : (res.alert && res.alert.skipped_cooldown ? ' (en cooldown)' : '');
            log('Movimiento ' + Math.round(res.score * 100) + '%' + extra + alertTxt);
          } else if (res.status === 'idle') {
            setStatus('Vigilando…', 'on');
          }
        });
    }).catch(function (e) {
      setStatus('Error de red, reintentando…', 'on');
      log('Error envío: ' + e);
    }).then(function () { sending = false; });
  }

  function start() {
    startCamera().then(function () {
      return loadConfig();
    }).then(function () {
      requestWakeLock();
      localStorage.setItem('cameraName', camInput.value.trim());
      lockCam(true);
      startBtn.hidden = true; stopBtn.hidden = false;
      setStatus('Vigilando "' + getCam() + '"…', 'on');
      var ms = (cfg.capture_interval_seconds || 3) * 1000;
      timer = setInterval(sendFrame, ms);
      sendFrame();
    }).catch(function (e) {
      setStatus('No se pudo acceder a la cámara', '');
      log('Error cámara: ' + e + ' (¿estás en HTTPS?)');
    });
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    releaseWakeLock();
    lockCam(false);
    startBtn.hidden = false; stopBtn.hidden = true;
    setStatus('Detenido', '');
  }

  startBtn.addEventListener('click', start);
  stopBtn.addEventListener('click', stop);
  baselineBtn.addEventListener('click', function () {
    fetch('baseline?camera=' + encodeURIComponent(getCam()), { method: 'POST' }).then(function () {
      log('Escena de referencia de "' + getCam() + '" se fijará con la próxima foto');
    });
  });

  // Persistir el nombre también al iniciar, y bloquear el campo mientras vigila.
  function lockCam(lock) { camInput.disabled = lock; }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(function () {});
  }
})();
