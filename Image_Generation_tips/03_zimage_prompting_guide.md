# Z-Image Turbo — Reglas de prompting (no son opcionales)

Z-Image fue entrenado con captions en lenguaje natural (inglés/chino), no con tags estilo booru. El text encoder es Qwen3-4B, no CLIP tradicional.

## Regla #1 — El modelo IGNORA el prompt negativo por completo

No hay forma de decirle "no dibujes X" y que funcione como negativo real (el nodo `ConditioningZeroOut` que usamos en el workflow reemplaza al negativo, pero no filtra nada — solo es requerido por la arquitectura). **Todo lo que no querés tiene que evitarse describiendo directamente lo que SÍ querés.**

Ejemplo de error real que cometimos: escribir `"partner out of frame"` para una escena de penetración. Resultado: el hombre no tenía genitales, porque el modelo interpretó literalmente "no lo muestres". Fix: describir la acción explícitamente — `"his erect penis penetrating her vagina, visible clearly where their bodies meet"`.

## Regla #2 — Frases en inglés natural, 30-120 palabras, estructuradas. Nunca listas de tags sueltos

Estructura recomendada:
`[sujeto + rasgos distintivos] + [acción/pose explícita] + [entorno] + [iluminación] + [cámara/lente/composición]`

## Regla #3 — Para NSFW, describí la anatomía y el contacto explícitamente

Si la escena involucra penetración, contacto genital, etc., nombralo directamente en el texto (ver ejemplo regla #1). No asumas que "sex scene" o "having sex" alcanza — funciona mejor cuanto más explícito y concreto es el texto.

## Regla #4 — No mezclar estilos contradictorios

No pedir `"photorealistic"` y `"anime style"` en el mismo prompt — el resultado queda en un "uncanny valley" raro. Mantené consistencia de estilo.

## Regla #5 — Rasgos distintivos concretos para consistencia entre generaciones

Si necesitás que el mismo personaje se vea igual entre varias imágenes, usá descripciones muy específicas ("chocolate brown hair with copper highlights, falling to mid-back, slight wave, side-parted") en vez de genéricas ("brown hair"). Z-Image no tiene memoria entre generaciones — cada prompt debe repetir la descripción completa.

## Settings fijos (no tocar, son los oficiales del modelo turbo)

- Steps: 8, CFG: 1, sampler: `res_multistep`, scheduler: `simple`
- `ModelSamplingAuraFlow` shift: 3
- Subir el CFG rompe la imagen — es un modelo distillado a pocos pasos, no está diseñado para CFG alto.

## Prompt de ejemplo que funcionó (confirmado, imagen limpia con genitales/anatomía correcta)

```
A photorealistic scene of a young adult woman with long brown wavy hair straddling and riding
a man in a modern city apartment bedroom at night. She sits on top of him, his erect penis
penetrating her vagina, visible clearly where their bodies meet. She has natural matte skin
with no shine, correct human anatomy, natural hands with five fingers each. The man is a
muscular adult torso, his face out of frame, his hands resting on her hips. Warm intimate lamp
lighting, floor-to-ceiling window showing a city skyline at night, contemporary interior. Shot
on a DSLR camera with a 50mm lens, close-up composition, sharp focus, natural color balance.
```

## Limitación conocida: escenas con 3+ personajes / grupos

Z-Image tiene problemas documentados de consistencia con múltiples personajes en la misma imagen (confusión de a qué cuerpo pertenece cada extremidad). No hay LoRA madura todavía para esto (buscado en 2026-07, no encontrado nada confiable). Para gangbangs/grupos, mejor usar el stack SDXL/Illustrious o LUSTIFY/Big Lust que sí tienen LoRAs específicas de grupo.

## LoRAs recomendadas (pendiente de bajar/confirmar por el usuario)

- **NSFW Master V2** — https://civitai.com/models/667086/nsfw-master?modelVersionId=2904324 — usar en fuerza 0.8 (recomendación del creador)
- **Realistic Snapshot v5** — https://civitai.com/models/2268008/realistic-snapshot-z-image-turbo — detalle de piel/poros/anatomía
