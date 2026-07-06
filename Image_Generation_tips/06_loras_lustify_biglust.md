# LoRAs para LUSTIFY / Big Lust (SDXL 1.0 puro)

Actualizado 2026-07-01. Recordatorio: NO usar LoRAs tageadas "Illustrious", "Pony" o "SD 1.5" con estos checkpoints sin probarlas primero — son ecosistemas de entrenamiento distintos, la compatibilidad no está garantizada aunque técnicamente todas sean "SDXL".

## Instaladas

| LoRA | Estado | Ruta | Uso |
|---|---|---|---|
| `badhands.safetensors` (BadHands SDXL) | ✅ Instalada, **probada — no usar por default** | https://civitai.com/models/128969/badhands-sdxl-negative-lycorislokr | Ver hallazgo abajo: en la prueba real, evitó el contacto mano-genital en vez de solo arreglar anatomía durante el contacto |
| `MS_Real_XL_Taped_Lite.safetensors` (MS Real XL Lite - Tape Gag) | ⏳ Descarga incompleta (0 bytes + .part de 11.7MB de 162.6MB esperados) | https://civitai.com/models/344309 | Variedad de mordazas/cinta. Tageada SDXL 1.0 puro. El usuario vio una imagen de ejemplo con estilo anime en la página — **sin confirmar todavía si afecta el estilo real**, falta terminar de descargar y testear directo antes de usarla con confianza |

## Conclusión importante de las pruebas de esta sesión

**La mayoría de las escenas NSFW (poses complejas, gangbang, bondage completo con soga+mordaza) salieron perfectas SOLO con prompt bien escrito, sin ninguna LoRA.** Confirmado con pruebas reales, no supuesto. Ver `02_lecciones_aprendidas.md` puntos 8 y 9.

Esto cambia la estrategia recomendada: en vez de salir a buscar una LoRA para cada escena nueva, **primero probar con prompt solo**. Las LoRAs de esta lista son un complemento/red de seguridad, no un requisito.

## Búsquedas hechas sin resultado sólido (para no repetir)

- "Variedad de poses" genérica para SDXL 1.0: sin resultados de calidad — la mayoría son SD 1.5 (incompatible) o Illustrious/Pony (estilo distinto).
- "Sex Box" (UOC): existe en SDXL 1.0 pero es un concepto muy específico (mueble de bondage), no variedad general.
- Bondage/rope general en SDXL 1.0 puro: opciones limitadas, la mayoría de las bien evaluadas son SD 1.5 o Illustrious.

## Hallazgo real: badhands.safetensors probado en gangbang (strength 0.7)

Comparación directa: mismo prompt de gangbang (3 hombres, ella con la mano en un pene y boca en otro), una vez sin LoRA (ya fixeado por prompt/negativo — salió perfecto, ver lección #9) y una vez con `badhands` a fuerza 0.7.

**Resultado con badhands**: las manos quedaron anatómicamente limpias (5 dedos, bien formadas) PERO ella levantó ambas manos en el aire, sin tocar a nadie — el prompt pedía contacto explícito mano-pene y boca-pene, y no se generó. Encima el tercer hombre desapareció (quedaron 2 en vez de 3). Parece que el LoRA empuja el modelo a evitar escenas de contacto directo mano-genital en vez de solo mejorar la forma de la mano cuando SÍ hay contacto.

**Conclusión**: no usar `badhands` por default en escenas con acción de manos (handjob, sujetar, etc.) — ahí es contraproducente. Podría servir en escenas donde las manos NO necesitan tocar nada explícito (ej. manos en la cadera, apoyadas en una superficie), pero no se probó ese caso todavía.

## Pendiente

- Terminar de descargar `MS_Real_XL_Taped_Lite` y testear visualmente antes de confiar en ella.
- Probar `badhands.safetensors` en una escena de grupo (donde más se necesita) y comparar con/sin.
- Si aparece una necesidad muy puntual (prop específico, tipo de cuerpo, etc.) buscar de nuevo con ese término exacto — las búsquedas genéricas no rinden bien acá.
