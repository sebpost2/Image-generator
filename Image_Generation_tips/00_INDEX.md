# Índice — Image Generation Tips

Carpeta de referencia para generación de imágenes con ComfyUI. Hacé que Claude lea el archivo relevante cuando necesites generar algo, en vez de repetir explicaciones desde cero.

- `01_checkpoints_disponibles.md` — qué checkpoint usar según el tipo de escena, settings probados
- `02_lecciones_aprendidas.md` — bugs reales encontrados y su fix (leer ANTES de generar NSFW nuevo, evita repetir horas de debug)
- `03_zimage_prompting_guide.md` — reglas específicas de Z-Image Turbo (modelo de lenguaje natural, sin negativos)
- `04_tecnicas_avanzadas_pipeline.md` — ControlNet (control de pose), highres fix, upscaling, inpainting — para escenas complejas/multi-persona
- `05_lustify_biglust_settings.md` — settings específicos para LUSTIFY / Big Lust (confirmados con pruebas reales)
- `06_loras_lustify_biglust.md` — LoRAs instaladas/evaluadas para LUSTIFY/Big Lust y qué buscar (o no) para bondage/grupo/poses

## Estado general (2026-07-01) — WORKSPACE CERRADO PARA EL PROYECTO NSFW REALISTA

- **Checkpoint default: LUSTIFY APEX V8** (`lustifySDXLNSFW_apexV8.safetensors`), workflow `md/WORKFLOW_MASTER_LUSTIFY.json`. Big Lust v1.6 queda instalado como alternativa (mejor en algunos tests de grupo) pero LUSTIFY es el elegido por el usuario.
- **Validado con muestra respetable inicial (14 imágenes, 6 categorías, seeds distintos)**: escenas de pareja, fondos sin gente, poses complejas, bondage (soga+mordaza+cinta), y LoRA de tape gag salieron bien. La categoría gangbang (3 personas) de esa primera muestra en realidad tenía 6/14 defectos reales al revisar con cuidado — ver hallazgo abajo.
- **Gangbang (3 personas) — resuelto (2026-07-01)**: se probó ControlNet de pose primero, pero cambiaba un set de defectos por otro (manos raras, genitales faltantes, lengua sobredimensionada — lección 10). El fix real fue de prompt: agregar iluminación explícita ("well lit, no shadows hiding genitals") + negativo de oclusión de genitales + subir crop_factor/denoise del Hand Detailer. Validado con una segunda muestra de 14 imágenes (10 a 1024x1024 + 4 a 1536x1536), **14/14 limpias** con revisión estricta por categoría. Ver lección 13 en `02_lecciones_aprendidas.md`. La resolución 1536 no mostró ventaja clara sobre 1024 — no usarla como fix por defecto.
- **Conclusión clave**: para este checkpoint, el prompt bien escrito (natural + explícito, incluyendo iluminación) resuelve casi todo — no hace falta LoRA ni ControlNet para poses/grupo/bondage. Ver `02_lecciones_aprendidas.md` puntos 8-9 y 13.
- **LoRAs instaladas**: `badhands.safetensors` (probada, NO usar en escenas con contacto de manos — evita la acción), `MS_Real_XL_Taped_Lite.safetensors` (probada, sin rastro de estilo anime, funciona bien).
- **ControlNet de pose: instalado y probado, queda como último recurso** — no como primer intento para grupo/gangbang (ver arriba). Mejora la coherencia de pose pero introduce fricción en manos/cara. Highres pass/SeedVR siguen sin instalar (no hacían falta).
- **Hallazgo importante (proceso de revisión)**: la revisión rápida ("100% limpias") de la primera muestra de 14 imágenes estaba mal — una revisión más detallada encontró 6 de 14 con defectos reales (fusión de piernas, genitales faltantes/estirados, dedos de más, flotación). Con muestras chicas, revisar cada imagen con cuidado, por categoría separada, antes de dar un veredicto de calidad.
- Familia Illustrious/anime (bismuth, ilustmix, unholyDesireMix, noobaiXL) y Z-Image Turbo siguen disponibles para otros usos (proyecto GameBase / fotorrealismo rápido respectivamente), workflows propios ya documentados.
