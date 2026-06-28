# Estructura de post: "Sistema de vigilancia con IA local usando un móvil viejo"

> Plantilla para el artículo + making of. Rellena los bloques `[...]`, recorta lo
> que no quieras y añade capturas donde pongo `📸`.

---

## 1. Título (elige uno)
- "Convertí un iPhone viejo en una cámara de vigilancia con IA local (y sin nube)"
- "Vigilancia casera con IA local: un móvil reciclado, un Mac y Docker"
- "De trasto a alarma inteligente: visión por computador + IA local en local-first"

**Subtítulo:** Un móvil antiguo como cámara, detección de movimiento con OpenCV e
interpretación de la escena con un modelo de visión local (Ollama). Todo en tu red,
sin servicios en la nube. Alertas a Telegram.

---

## 2. Gancho / intro (2-3 párrafos)
- El problema: cámaras de vigilancia comerciales = nube, suscripciones, tus
  imágenes en servidores ajenos.
- La idea: reutilizar un **móvil viejo** (iPhone 11) como cámara y un **Mac mini
  Intel** como cerebro, todo **local-first** (funciona sin internet salvo el aviso).
- El twist: que la IA sea **opcional** → v1.0 (solo movimiento) y v2.0 (con IA).
- 📸 Foto del montaje real / captura de una alerta en Telegram.

---

## 3. La arquitectura (diagrama + explicación)
```
iPhone (PWA) ──foto cada Xs──► Mac (Docker)
                                ├─ FastAPI    : recibe la imagen
                                ├─ OpenCV     : ¿hay movimiento? (resta de imágenes)
                                ├─ Ollama     : ¿qué es? (si cambio ≥5%, en background)
                                └─ Telegram   : 📲 foto + descripción
```
- **Pipeline de dos etapas**: filtro de movimiento barato (OpenCV) y, solo si
  supera umbral, interpretación cara (IA). Clave para CPU sin GPU.
- **Local-first**: todo el núcleo offline; solo la notificación necesita internet.
- Stack: `[FastAPI · OpenCV · Pillow · SQLite · Ollama+moondream · Docker]`.

---

## 4. Decisiones de diseño (el "por qué")
- **PWA en vez de app nativa**: máxima retrocompatibilidad, cero App Store. Trade-off:
  iOS suspende en segundo plano → móvil enchufado, pantalla activa (Wake Lock).
- **Modelo de IA ligero (moondream)**: el Mac es Intel (CPU, sin GPU). Elegir el
  modelo más pequeño que sirviera.
- **IA detrás de un flag** (`AI_ENABLED`): mismo código para v1.0 y v2.0.
- **Docker**: portable a "otros trastos viejos".

---

## 5. 🛠️ El Making Of (la mejor parte: los bugs reales)
> Cuenta el viaje cronológico. Cada tropiezo es una mini-lección.

1. **La cámara web exige HTTPS en la LAN.** `getUserMedia` no va por HTTP salvo en
   localhost → certificado autofirmado generado dentro del contenedor.
2. **Docker en Mac no comparte `/Applications`** (+ un symlink que despistaba a
   Docker). Solución: volúmenes con nombre y certificado generado en el contenedor
   → independiente de dónde viva el proyecto.
3. **"No me sale nada" en el móvil**: no era red, era escribir la URL **sin
   `https://`**. (Anécdota de debugging de red: firewall, ARP, AP isolation…)
4. **OpenCV petaba: "Sizes of input arguments do not match".** El móvil manda fotos
   con orientación/resolución variable → normalizar a tamaño fijo antes de comparar.
5. **moondream devolvía respuesta vacía.** Es un modelo pequeño de subtítulos: con
   prompts largos o en español → vacío. Solución: prompt simple en inglés.
6. **Latencia de ~1 min por inferencia en CPU Intel.** No se arregla por software
   (el cuello es el encoder de visión). Solución de arquitectura: **desacoplar** la
   IA (responder al móvil al instante y procesar la descripción en segundo plano).
7. **La descripción de la IA no llegaba a Telegram.** Doble causa: (a) un único
   cooldown la bloqueaba → **dos cooldowns independientes**; (b) ¡un **comentario en
   línea** en el `.env` que Docker metía como valor! → `ALERT_KEYWORDS` contaminado.
8. **Multi-cámara**: la intuición de "detectar por IP" no servía (Docker enmascara
   todas las IPs como `172.18.0.1`) → cada móvil se identifica con un **nombre**
   guardado en el navegador. Estado, baseline y cooldown **por cámara**.

📸 Pon capturas de los errores/logs aquí — quedan muy bien en un making of.

---

## 6. Cómo funciona por dentro (fragmentos de código)
- El **pipeline de dos etapas** (`/upload` → motion → background AI + notify).
- La **detección de movimiento** con OpenCV (`absdiff` + umbral + ratio de píxeles).
- La **llamada a Ollama** (imagen en base64 → descripción).
- El **multi-cámara** (estado por cámara, cooldown con `kind = "<cam>:motion"`).
> Elige 2-3 fragmentos cortos, no pegues archivos enteros.

---

## 7. Resultados / demo
- 📸 GIF o vídeo: te mueves → llega la alerta a Telegram con foto + "a person…".
- Números reales: tamaño en disco, latencia de movimiento (instantánea) vs IA (~Xs).
- v1.0 vs v2.0: qué aporta cada una.

---

## 8. Limitaciones y próximos pasos
- iOS suspende en segundo plano (móvil dedicado y enchufado).
- IA lenta en CPU Intel (con GPU/Apple Silicon volaría).
- Retención de imágenes solo se purga al reiniciar (mejora pendiente).
- Ideas: panel web multi-cámara, guardar solo el frame que dispara alerta,
  segundo canal de aviso 100% local, lógica "evento nuevo" en vez de cooldown fijo.

---

## 9. Cierre
- Reflexión: reutilizar hardware viejo + IA local = privacidad + cero coste recurrente.
- Llamada a la acción: enlace al repo, invitar a forkear/probar.
- `[enlace al repositorio]` · `[licencia]`

---

## Meta (para SEO / RRSS)
- **Tags**: `self-hosted`, `local-first`, `computer-vision`, `ollama`, `docker`,
  `privacy`, `home-automation`, `opencv`, `pwa`.
- **Tweet/post corto**: "Convertí un iPhone viejo en una cámara de vigilancia con
  IA 100% local: OpenCV detecta el movimiento, un modelo de visión local lo
  interpreta y me avisa por Telegram. Sin nube. Te cuento el making of 🧵👇"
- **Plataformas sugeridas**: blog propio (post largo) + hilo en X/LinkedIn +
  resumen en dev.to.
