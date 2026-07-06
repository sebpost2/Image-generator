# Checkpoints disponibles y cuándo usar cada uno

## Familia Illustrious/NoobAI (anime/ilustración) — `WORKFLOW_MASTER_REUSABLE.json`

| Checkpoint | Estilo | CFG probado | Notas |
|---|---|---|---|
| `bismuthIllustrious_v80` | Semi-realista, ilustración | 5 | Sin metadata embebida, EPS estándar |
| `ilustmix_v111` | Pictórico/painterly | 6 | El checkpoint "de siempre" del proyecto GameBase |
| `unholyDesireMixSinister_v80` | NSFW-oriented, ilustración | 6 | `modelspec.prediction_type: epsilon` confirmado |
| `noobaiXLNAIXL_vPred10Version` | Anime, más suave/pictórico a bajo CFG | **3.5** (no 6!) | Es v-prediction — necesita `ModelSamplingDiscrete(v_prediction, zsnr=true)` + CFG bajo. A CFG 6 se rompe (colores quemados). A CFG 3.5 sale correcto pero con aspecto más "acuarela" (esperable, no es bug) |

Todos usan el mismo stack de 11 LoRAs (`Power Lora Loader`, ver nodo 11 del workflow) — técnicas (detailer/aqm/Asura/estilo) siempre ON, `elara_vesper` (personaje) apagable si no es esa escena.

## Z-Image Turbo — `WORKFLOW_MASTER_ZIMAGE.json`

- Fotorrealista, 6B params, 8 steps / cfg 1 (fijo, no tocar — es un modelo "turbo" distillado).
- Entiende **lenguaje natural**, no tags. Ver `03_zimage_prompting_guide.md` — es el archivo más importante para no repetir errores.
- Corre en 8GB VRAM con offload parcial (el diffusion model son 11.5GB), tiempos de ~1-2min por imagen.

## LUSTIFY / Big Lust (SDXL 1.0 puro, NSFW-first, fotorrealista) — en instalación

- Base model: `SDXL 1.0` (NO Illustrious) → **las LoRAs actuales (NOOB detailer, aqm_complete, Asura, etc.) NO son compatibles/útiles acá**, están entrenadas para Illustrious. Necesitan su propio stack de LoRAs (pendiente, ver `05_lustify_biglust_settings.md`).
- Pensados específicamente para: fotorrealismo + escenas NSFW variadas (poses, grupos) en un contexto "historia moderna".
- LUSTIFY APEX V8: descargando. Big Lust v1.6: descargando.
- Sampler recomendado (de investigación, sin testear todavía): DPM++ 2M SDE o DPM++ 3M SDE, scheduler Exponential o Karras, 30 steps, CFG 4-7 (V8/V9). Highres fix: upscale 1.4-1.5x, denoise ~0.4 para planos generales/de cuerpo completo.

## Regla general de elección

- **Retrato/escena íntima 1-2 personas, prioridad fotorrealismo** → Z-Image Turbo, o LUSTIFY/Big Lust una vez instalados.
- **Estilo ilustración/pictórico, personaje Eliara (proyecto GameBase)** → familia Illustrious con el LoRA `elara_vesper` prendido.
- **Poses complejas / 3+ personas / gangbang** → LUSTIFY + prompt con línea de iluminación explícita + negativo de oclusión de genitales (ver lección 13 en `02_lecciones_aprendidas.md` — validado 14/14 limpias). No hace falta LoRA de pose ni ControlNet como primer intento; ControlNet queda de último recurso si una escena puntual sigue fallando (ver `04_tecnicas_avanzadas_pipeline.md`).
