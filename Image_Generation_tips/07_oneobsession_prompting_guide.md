# Guía de prompting para oneObsession (anime, Illustrious) — WORKFLOW_ANIME_ONEOBSESSION.json

Complementa `01_checkpoints_disponibles.md` (qué checkpoint usar) y `02_lecciones_aprendidas.md`
(bugs ya encontrados en este workflow puntual: ojos, LoRAs incompatibles, `[CONCAT]`). Este
archivo es específico de **cómo escribir el prompt en sí** para oneObsession, a diferencia de
LUSTIFY (ver `05_lustify_biglust_settings.md`), porque son estilos de prompt fundamentalmente
distintos, no solo un checkpoint distinto.

Fuentes externas consultadas (2026-07-24): [Arctenox's Simple Prompt Guide for Illustrious
(Civitai)](https://civitai.com/articles/23210/arctenoxs-simple-prompt-guide-for-illustrious),
más guías generales de Illustrious/NoobAI/Danbooru-tagging. oneObsession es un fine-tune de
Illustrious (confirmado en `02_lecciones_aprendidas.md`, lección de las LoRAs de ojos), así que
las reglas de Illustrious aplican directamente.

## LUSTIFY vs oneObsession — la diferencia que importa

| | LUSTIFY (fotorrealista) | oneObsession (anime/Illustrious) |
|---|---|---|
| Estilo de prompt | Frases descriptivas, lenguaje natural | Tags separados por coma, estilo Danbooru |
| Prefijo estándar | (ninguno fijo) | `masterpiece, best quality, absurdres` |
| Negativo estándar | descriptivo | `worst quality, low quality, lowres, bad anatomy, ...` |
| Longitud | frase completa | ~248 tokens máx — tags de más al final se diluyen |

**Esto significa que draft_image_prompts.py necesita dos perfiles de few-shot/system-prompt
distintos, no uno solo con instrucciones condicionales** — el LLM redactando tags sueltos y el
LLM redactando prosa son tareas de escritura distintas.

## Reglas concretas para el prompt positivo

- **Tags separados por coma, no prosa.** `1girl, solo, portrait, ornate coat, candlelight` en vez
  de "a girl wearing an ornate coat standing in candlelight".
- **Orden importa: lo más importante primero.** Un tag más lejos en el prompt se diluye más. Tags
  de calidad (`masterpiece, best quality, absurdres`) van primero (ya así en el workflow, nodo 6) o
  al final si el prompt es largo y el personaje/escena es lo prioritario — no hay una única regla
  correcta, pero mantené los tags de personaje/escena concreta cerca del principio.
- **Usá tags tal como existen en Danbooru**, no inventados ni traducidos. Si un tag no existe o
  tiene pocas imágenes de entrenamiento, no va a renderizar bien.
- **248 tokens es el límite práctico** — pasado eso, los tags del final se diluyen. Si una escena
  necesita mucho detalle, priorizar qué tags importan más y cortar el resto.
- **No usar tags de score numérico** (`score_9`, etc.) — eso es convención de Pony, Illustrious lo
  ignora.

## Reglas concretas para el prompt negativo

- Prefijo estándar: `worst quality, low quality, lowres, bad anatomy, bad hands, extra fingers,
  missing fingers, extra hands, extra limbs, extra arms` (ya en el workflow, nodo 7).
- **Trampa ya confirmada en este proyecto** (ver WORKFLOW_ANIME_ONEOBSESSION.json nodo 7): si hay
  una pareja masculina en la escena, **nunca** agregar `man`/`male` al negativo — Illustrious lo
  interpreta mal y puede eliminar al personaje masculino de la imagen.
- `flat color, flat shading, empty eyes, blank eyes` — agregado 2026-07-15 contra un bug conocido
  de la comunidad Illustrious/NoobAI (iris sin detalle); ver `02_lecciones_aprendidas.md`.

## Settings ya validados para este workflow

- CFG 6, euler_ancestral, steps 28 (base) — **no subir CFG arriba de 6**, la guía externa coincide
  en que Illustrious se "quema"/sobre-cocina arriba de ese valor, igual que la lección ya
  documentada acá con `noobaiXLNAIXL_vPred10Version` (aunque ese es v-prediction y oneObsession no).
- Face Detailer denoise 0.55 (confirmado A/B, ver lección 18).

## Qué falta (no cubierto por esta guía)

- Pesos de tag tipo `(tag:1.3)` — no probado todavía en este workflow específico; la guía externa
  lo menciona como válido en Illustrious pero no hay lección propia del proyecto que lo confirme.
- Tags de artista específico (`artist:...`) — no usados hasta ahora en las escenas de NewGame;
  agregar solo si se busca imitar un estilo puntual, verificando antes que el tag exista y tenga
  suficientes imágenes de entrenamiento.
