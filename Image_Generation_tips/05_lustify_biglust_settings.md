# LUSTIFY / Big Lust — settings reales (extraídos del workflow "APEX FLOW" del creador de LUSTIFY)

El usuario consiguió el ZIP real (`apexFLOWHighresFixSeedvr2_nonDMD2.zip`, en `E:\Torrents`, hecho para LUSTIFY V8 Apex). Estos son los settings reales que usa, no una reconstrucción — actualizado 2026-07-01.

## Checkpoints instalados

- `lustifySDXLNSFW_apexV8.safetensors` — SDXL 1.0, NSFW-first
- `bigLust_v16.safetensors` — SDXL 1.0, merge bigASP+LUSTIFY

## Resolución — dato importante que no sabíamos

Lustify V8 (Apex) fue entrenado también en **1536px**, no solo el 1024 estándar de SDXL. Resoluciones 1536 recomendadas por el creador:
- 1536x1536 (cuadrado)
- 1344x1664 / 1664x1344
- 1280x1920 / 1920x1280
- 1152x2048 / 2048x1152

Si 1536 da problemas, volver a 1024 (896x1152, 832x1216, 1024x1024).

## Pipeline completo del creador (8 etapas, la mayoría opcionales)

1. **First Pass** — KSampler: 30 steps, **cfg 3.5**, `dpmpp_2m_sde`, `karras`, denoise 1. ControlNet Union opcional acá (ver abajo).
2. **Highres Pass** — upscale con modelo (`4x_NMKD-Superscale-SP_178000_G.pth`) → downscale a ~2x neto → sharpen (`ImageCASharpening 0.2`) → segundo KSampler: 21 steps, cfg 4, denoise 0.51.
3. Elegir UNA: **2a. Tiled Upscale** (UltimateSDUpscale, 1.25x, cfg 3.5, denoise 0.3 — liviano pero "mucho peor") o **2b. SeedVR Upscale** (mejor calidad, el creador lo prefiere 90% de las veces, pero pesado en VRAM — ver nota abajo).
4. **Face Detailer** — guide/max size 1536, 22 steps, cfg 4, denoise 0.4, feather 5, bbox_dilation 10, crop_factor 1.5, + SAM (`sam_vit_b_01ec64.pth`) para afinar la máscara. Prompt propio: positivo `"portrait, close-up, face, 1girl,"` / negativo `"ugly, blurry"`.
5. **Hand Detailer** (opcional pero recomendado) — mismos parámetros pero crop_factor 1.8, feather 10, denoise 0.4. Prompt propio: `"close-up, hand, fingers,"`.
6. **Skin Enhancement** (opcional) — modelo `1x-ITF-SkinDiffDetail-Lite-v1.pth` (bajar de openmodeldb.info) + `ImageBlend` (blend_factor ajustable).
7. **Post-Processing** (opcional) — `ColorCorrect` + `FilmGrain`.
8. **Inpainting** (situacional, no en cada corrida) — `InpaintCropImproved` → `InpaintModelConditioning` → KSampler (25 steps, cfg 3.5, denoise 0.45) → `InpaintStitchImproved`. Para corregir manualmente una zona puntual sin regenerar toda la imagen.

## ControlNet (opcional, First Pass)

- Modelo: `xinsir-controlnet-union-sdxl-1.0-promax.safetensors` (Union — soporta depth, pose, etc. con un solo modelo)
- En el workflow del creador usa **depth** (`AIO_Preprocessor` con `DepthAnythingPreprocessor`), strength 0.3, activo solo del 0% al 40% de los steps (`ControlNetApplyAdvanced`) — es una guía sutil de composición, no un lock rígido de pose.
- Para pose específica (lo que más nos interesa para "muchas posiciones"), cambiar `SetUnionControlNetType` a `openpose` y usar un preprocesador de pose (DWPose) en vez de depth — mismo modelo union sirve.
- Requiere: nodos de `comfyui_controlnet_aux` (no instalado todavía) + el modelo union (~2.5GB, no descargado todavía).

## SeedVR Upscale — cuidado con la VRAM

El creador usa `seedvr2_ema_7b_fp16.safetensors` (~16GB VRAM — **imposible en nuestra placa de 8GB**). Alternativas para 8GB:
- **3b fp8**: ~3.3GB VRAM
- **3b Q4**: menos todavía
- **7b Q4**: ~4.5GB VRAM (mejor calidad que 3b, todavía entra en 8GB si no hay mucho más cargado en simultáneo)
- Evitar la variante "sharp" (el creador la probó y no es buena pese al nombre)
- **Dato específico para NSFW**: SeedVR tiene un parámetro `shorter_edge` (default 640) que downscalea antes de upscalear para mejor resultado — pero si se downscala demasiado, genitales/pezones pueden perder forma. Si las partes íntimas salen "sucias" en el upscale, subir el valor de `shorter_edge` (se pierde un poco de la magia del upscaler pero se mantienen los detalles limpios).
- Truco del creador: agregar `FilmGrain` (intensidad 0.02) ANTES de SeedVR — ayuda a textura de piel Y SeedVR funciona mejor con imagen ligeramente ruidosa.
- Requiere: custom node `ComfyUI-SeedVR2_VideoUpscaler` (github numz) + modelos DiT+VAE correspondientes (no instalado todavía).

## Qué ya probamos (2026-07-01) — nivel "rápido", sin las etapas pesadas

Armamos una versión reducida: Checkpoint (bare, sin LoRAs todavía) → KSampler (cfg 3.5, dpmpp_2m_sde, karras, 30 steps, 1024x1024) → Face Detailer + Hand Detailer (con SAM, settings del creador de arriba, sin el highres/upscale/skin-enhancement). Esto NO necesitó descargar nada nuevo — `sam_vit_b_01ec64.pth` ya estaba instalado. Resultado: ver carpeta output, prefijo `final_test_lustify_apex` / `final_test_biglust`.

## Plan de 2 niveles (para no perder velocidad de generación)

Dado que el usuario prioriza volumen/velocidad (muchas imágenes, no quiere estar arreglando cosas):

- **Nivel rápido (default para generar en volumen)**: First Pass + Face/Hand Detailer con SAM. Ya funciona, sin descargas extra.
- **Nivel "polish" (opcional, solo para la imagen ganadora de un batch)**: agregar Highres Pass + Tiled/SeedVR Upscale + Skin Enhancement + ControlNet si hace falta pose exacta. Necesita instalar: `comfyui_controlnet_aux`, `ComfyUI-Custom-Scripts` (pysssss), `ComfyUI_essentials` (cubiq), Ultimate SD Upscale, Inpaint-CropAndStitch, SeedVR2 + modelo liviano (3b fp8 o 7b Q4), modelo `4x_NMKD-Superscale-SP_178000_G.pth`, modelo `1x-ITF-SkinDiffDetail-Lite-v1.pth`, modelo ControlNet union SDXL (~2.5GB). Pendiente de decisión con el usuario si vale la pena instalar todo esto ahora o más adelante.

## LoRAs — todavía no instaladas para estos checkpoints

No se instaló ninguna LoRA de pose/grupo para LUSTIFY/Big Lust todavía. Pendiente: buscar LoRAs específicas de SDXL 1.0 (no "Illustrious"/"IL") para pose y escenas de grupo una vez confirmado que el checkpoint base funciona bien solo.
