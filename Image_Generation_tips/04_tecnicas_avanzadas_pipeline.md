# Técnicas avanzadas para escenas complejas (poses, grupos, alta resolución)

Ninguna de estas está instalada/probada todavía (2026-07-01) — son investigación para cuando haga falta subir la confiabilidad de poses específicas o escenas de grupo. No instalar nada de esto sin necesidad real, cada pieza agrega VRAM/tiempo.

## Actualización (2026-07-01): ControlNet quedó como último recurso, no primer intento

Se probó el fix real para gangbang (ver abajo) contra una alternativa más simple: agregar iluminación explícita al prompt + negativo de oclusión de genitales, sin ControlNet. Una muestra de 14 imágenes con ese fix de prompt dio **14/14 limpias** (cara, manos, genitales, conteo de extremidades — revisado por separado en cada una). Contra eso, ControlNet en las pruebas anteriores metía defectos nuevos en manos/cara/lengua en la mayoría de intentos. **Conclusión: para escenas de grupo, probar primero el fix de iluminación de prompt (lección 13 en `02_lecciones_aprendidas.md`) antes de instalar/usar ControlNet.** Dejar ControlNet para el caso puntual en que ese fix no alcance.

## ControlNet de pose — INSTALADO Y PROBADO (2026-07-01)

**Confirmado con prueba real**: se tomó una imagen de gangbang con buena composición pero con defectos de anatomía (genitales faltantes, dedos de más), se extrajo su esqueleto de pose con DWPose, y se regeneró la MISMA escena guiada por ese esqueleto. Resultado: los defectos de anatomía desaparecieron (genitales correctos y visibles en ambos hombres, manos sin fusión). El ControlNet no arregla el conteo de personas (si la referencia ya tenía 2 hombres en vez de 3, la nueva imagen también tiene 2), pero sí mejora mucho la coherencia anatómica cuando ya hay una pose grupal decente para copiar.

**Instalado:**
- Custom node `comfyui_controlnet_aux` (en `custom_nodes/`) — da el nodo `DWPreprocessor` (ojo: NO se llama `DWPose_Preprocessor` en el grafo, ese es solo el nombre de la clase interna)
- Modelo `xinsir-controlnet-union-sdxl-1.0-promax.safetensors` en `models/controlnet/` (2.5GB)
- Modelos de DWPose (se bajan solos la primera vez, pero si falla por el mismo bug de SSL de Windows, bajarlos a mano):
  - `custom_nodes/comfyui_controlnet_aux/ckpts/yzd-v/DWPose/yolox_l.onnx` (detector de personas)
  - `custom_nodes/comfyui_controlnet_aux/ckpts/hr16/DWPose-TorchScript-BatchSize5/dw-ll_ucoco_384_bs5.torchscript.pt` (estimador de pose)

**Receta que funcionó** (nodos, en orden):
1. `LoadImage` — la imagen de referencia (puede ser una generación previa con buena pose)
2. `DWPreprocessor` (`detect_hand/body/face: enable`, `scale_stick_for_xinsr_cn: enable` — importante para que funcione bien con el modelo union de xinsir)
3. `ControlNetLoader` (el modelo union) → `SetUnionControlNetType` (`type: openpose`)
4. `ControlNetApplyAdvanced` (`strength: 0.75`, `start_percent: 0`, `end_percent: 0.85`) conectado al positive/negative antes del KSampler
5. Resto del pipeline igual (KSampler + Face/Hand Detailer)

**Cuándo usarlo**: cuando una escena de grupo salió con buena composición pero mala anatomía puntual. No hace falta para escenas de 1-2 personas (ahí el prompt solo ya funciona bien).

## ControlNet de pose — la herramienta correcta para "quiero exactamente esta pose"

Cuando el prompt solo no alcanza para fijar una pose específica (más probable en escenas de grupo con posiciones concretas), ControlNet con un mapa de pose (OpenPose/DWPose) es la solución estándar, no una LoRA de pose.

- Modelo recomendado para SDXL: `thibaud/controlnet-openpose-sdxl-1.0` (Hugging Face)
- Detector de pose: **DWPose** es más preciso que OpenPose clásico, especialmente en manos — usarlo si está disponible.
- Strength recomendado: **0.7-0.9** (no 1.0 — a 0.85 el modelo tiene más libertad creativa mientras respeta la pose general; a 1.0 puede verse rígido/artificial).
- Requiere: descargar el modelo ControlNet (~2.5GB para SDXL) a `models/controlnet/`, más un preprocesador de pose (nodo tipo `DWPose Estimator`, viene en paquetes como comfyui_controlnet_aux).
- Uso típico: generar/conseguir una imagen de referencia con la pose deseada (o dibujarla), extraer el esqueleto con DWPose, y usarlo como condicionamiento junto al prompt normal.

## Highres fix — para nitidez en planos generales/cuerpo completo

Técnica: generar a resolución base (832x1216 o similar) → upscale del latente 1.4-1.5x → segunda pasada de KSampler con denoise bajo (~0.4) para agregar detalle sin cambiar la composición. Estándar en LUSTIFY/Big Lust y la mayoría de checkpoints SDXL realistas.

## SeedVR2 — upscaler/restaurador avanzado (opcional, pensado más para video)

Es un modelo de ByteDance, difusión de un solo paso, muy usado para upscaling de video pero tiene modo imagen. Da mejor detalle que un ESRGAN tradicional pero:
- Necesita sus propios pesos (DiT + VAE) descargados aparte, consume VRAM extra.
- Arquitectura de 4 nodos (modelo DiT, modelo VAE, config de torch.compile, upscaler principal) — más complejo de armar que un upscaler tradicional.
- **Recomendación**: para nuestro caso (8GB VRAM, priorizar velocidad), empezar con un upscaler ESRGAN simple (ej. `4x-UltraSharp`, ~64MB, liviano) antes de meter SeedVR2. Solo vale la pena si el detalle de un ESRGAN normal se queda corto.
- Instalación si se decide usar: `git clone https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler.git` en `custom_nodes/`.

## Inpainting — para corregir errores puntuales sin regenerar toda la imagen

Cuando una imagen sale casi bien pero con un error localizado (mano, cara, un objeto raro), en vez de tirar el seed entero: enmascarar la zona con problema y regenerar solo esa región con denoise bajo-medio (0.4-0.6). Mismo principio que el FaceDetailer/hand detailer que ya usamos, pero manual y para cualquier zona de la imagen (no solo cara/manos).

## Workflow de referencia (bloqueado, no accesible)

Se encontró "APEX FLOW [Highres Fix, SeedVR2, FaceDetailer, ControlNet, Inpainting]" en Civitai, armado específicamente para LUSTIFY V8, con las 4 técnicas de arriba combinadas. El ZIP está bloqueado detrás de cuenta de Civitai (mismo bloqueo que las LoRAs NSFW) — no se pudo descargar ni inspeccionar el grafo real de nodos. Lo de arriba es la reconstrucción por investigación propia de cada pieza por separado. Si en algún momento se consigue acceso a ese ZIP (cuenta de Civitai), vale la pena revisarlo para comparar contra esto.

Nota del creador sobre variantes (de la descripción pública, sin acceso al workflow):
- **NON-DMD2**: más lento, mayor calidad y diversidad — usa todas las técnicas de arriba a fondo.
- **DMD2**: rápido (6-8 steps) pero necesita un nodo extra `ComfyUI-NAG` (github.com/ChenDarYen/ComfyUI-NAG) para que el negativo funcione con el sampler distillado, y tiene su propio look visual con menos diversidad de caras/fondos/texturas.
