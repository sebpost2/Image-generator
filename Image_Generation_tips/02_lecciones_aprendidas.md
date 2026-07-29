# Lecciones aprendidas debuggeando (leer ANTES de generar NSFW nuevo)

Cada una de estas costó horas de prueba y error en la sesión del 2026-07-01. Evitá repetir el mismo camino.

## 1. El bug del "filtro amarillo/arcoíris" en checkpoints SDXL/Illustrious

**Síntoma**: la imagen sale con colores quemados — posterizado amarillo/verde, o arcoíris cian-rojo-magenta. La composición/pose/anatomía sale BIEN, solo el color está roto.

**Causa real (la única que importó de verdad)**: el prompt negativo prohibía `(man:1.6), (male:1.5)` mientras el positivo pedía penetración/sexo — una contradicción directa (pedís el elemento y lo prohibís al mismo tiempo con peso alto). El modelo "pelea" internamente y el resultado es corrupción de color.

**Fix**: para escenas con pareja masculina, NUNCA prohibir `man`/`male` en el negativo. En vez de eso:
- Positivo: nombrá al hombre explícitamente, ej. `"riding a faceless man"`, `"his hands on her hips"`.
- Negativo: solo prohibir `detailed male face, male facial features` (para que no se le vea la cara, no para que no exista).

**Cosas que probé y NO eran la causa real** (para no repetir el camino largo): degradación de sesión/VRAM (descartado — resultado 100% determinístico en sesión limpia), la LoRA `lightingSlider` (ayuda un poco a un sesgo amarillo suave pero no es la causa del quemado grave), VAE en fp16 (probé forzar fp32, sin cambio), el seed específico (probé 3 seeds distintos, todos rotos hasta el fix real), el escenario "moderno" vs fantasía (probé ambos, rotos igual hasta el fix real).

## 2. NoobAI-XL (v-prediction) necesita CFG bajo, no el CFG estándar de 6

Es un modelo v-prediction. A CFG 6 (el estándar que usan los otros checkpoints) se rompe con el mismo patrón de colores quemados. Fix: `ModelSamplingDiscrete(sampling="v_prediction", zsnr=true)` + **CFG 3.5** (no 6). Da un resultado más suave/pictórico a bajo CFG — es esperable, no un bug adicional.

## 3. Brillo/reflejo excesivo en la piel ("wet skin" look)

Tags de negativo que ayudan: `shiny skin, wet skin, oily skin, glossy skin, excessive specular highlight, glistening skin`. En el positivo agregar `matte skin, subtle skin sheen`. Bajar la LoRA de fotorrealismo/lighting si sigue muy marcado.

## 4. Dedos deformados — usar el detector de manos que ya está instalado

Hay un modelo `hand_yolov8s.pt` en `models/ultralytics/bbox/` sin usar. Agregar un segundo nodo `FaceDetailer` (sí, el mismo tipo de nodo sirve para manos) apuntando a un `UltralyticsDetectorProvider` con ese modelo, encadenado después del FaceDetailer de cara. Mejora mucho los dedos sin third-party tools.

## 5. Negativos muy largos y con muchos pesos `(tag:1.6)` confunden más de lo que ayudan en SDXL

Investigación externa confirma: SDXL es menos sensible a negativos que SD1.5, y sobrecargarlo con pesos fuertes puede degradar la imagen en vez de mejorarla. Preferir negativos más cortos y en texto plano.

## 6. Z-Image Turbo: ver `03_zimage_prompting_guide.md` — el bug de "sin genitales" fue por esto

Resumen rápido: Z-Image **ignora negativos por completo**. Si describís "partner out of frame" en vez de describir la acción explícita, el modelo literalmente no la dibuja. Todo tiene que decirse en positivo.

## 7. Antes de asumir que un checkpoint está roto, probar el prompt ORIGINAL que sabés que funciona

Cuando ilustmix/unholyDesire/noobaiXL parecían "rotos" en todas las pruebas, el test decisivo fue correr el prompt de la escena de la taza de té (ya probada en producción) en el mismo pipeline — salió perfecta. Eso confirmó que el pipeline/checkpoint estaban bien y el problema era 100% el prompt nuevo. **Siempre aislar la variable real así antes de descartar un checkpoint.**

## 8. LUSTIFY/Big Lust (SDXL 1.0 puro NSFW-first) siguen texto MUY bien — probar prompt antes de buscar una LoRA

Confirmado con pruebas reales: poses complejas (de pie, pierna levantada), gangbang de 3 personas, y bondage completo (soga + mordaza de bola) salieron correctos **solo con prompt bien escrito, sin ninguna LoRA**. A diferencia de la familia Illustrious/anime (que depende mucho de LoRAs con trigger words), estos checkpoints fotorrealistas responden principalmente al texto. **Antes de salir a buscar una LoRA de pose/escenario específico, probar primero si el prompt solo ya lo resuelve** — probablemente sí.

## 9. Manos de más en escenas de grupo (gangbang) — fix de prompt, no de LoRA

**Síntoma**: en una escena de 3 personas, la mujer sale con 3 manos (una de más, típico error de multi-persona).

**Fix que funcionó**: reforzar tanto negativo como positivo explícitamente:
- Negativo: agregar `extra hands, extra limbs, extra arms` (no solo `bad hands`/`extra fingers` — eso ataca dedos, no manos de más)
- Positivo: ser explícito, ej. `"she has exactly two arms and two hands, one hand holding X, her mouth around Y"`

Con esto, Big Lust generó gangbang de 3 hombres con anatomía perfecta. LUSTIFY con el mismo fix redujo el número de personas a 2 (sin errores, pero no siguió el pedido de 3) — **para escenas de grupo, Big Lust parece manejarse mejor que LUSTIFY** en las pruebas hechas hasta ahora.

## 10. ControlNet de pose NO es una solución mágica — cambia un set de errores por otro

La imagen `final_test_gangbang_controlnet_00001_` (guiada por esqueleto DWPose) arregló la fusión de piernas/dedos de más de la referencia original, PERO introdujo nuevos defectos: mano con agarre antinatural, un hombre sin genitales visibles, lengua sobredimensionada. Forzar una pose rígida via ControlNet parece generar fricción en otras partes (manos, cara) porque el modelo tiene que reconciliar esa pose exacta con el resto de la anatomía. **Conclusión: revisar SIEMPRE cara/manos/genitales por separado en cualquier imagen, incluida las generadas con ControlNet — no asume que resolvió todo.**

## 11. Proceso de revisión de Claude: mirar de cerca, no de lejos

Dos veces en esta sesión se declaró una imagen "perfecta" en una revisión rápida y después aparecieron defectos reales (manos raras, genitales faltantes, ojos/lengua mal) al mirar con más atención. **Antes de dar un veredicto de calidad sobre cualquier imagen generada, revisar explícitamente por separado: (1) cara — ojos simétricos, boca/lengua proporcionada, (2) manos — conteo de dedos y agarre natural, (3) genitales — presentes y con forma correcta, (4) conteo de extremidades/personas.** Una mirada general de la composición no alcanza.

## 13. El fix real para gangbang no fue ControlNet — fue el prompt de iluminación explícita (muestra de 14/14 limpias)

Después de que ControlNet mostrara defectos nuevos en todas las pruebas (lección 10), se armó una muestra real de 14 imágenes de la misma escena de gangbang (3 personas) SIN ControlNet, solo agregando al positivo `"well lit, no shadows hiding genitals"` + `"Bright even lamp lighting from multiple sources"` y al negativo `"missing genitals, hidden genitals, obscured genitals, shadow on genitals"`, además de subir `crop_factor` del Hand Detailer de 1.5 a 2.0 y su `denoise` de 0.4 a 0.45:

- 10 imágenes a 1024x1024: genitales visibles y correctos, manos naturales, caras/ojos bien en las 10.
- 4 imágenes a 1536x1536 (misma config, solo resolución nativa más alta): genitales correctos, manos naturales, caras bien en las 4.

**Resultado: 14/14 limpias con revisión estricta por categoría (cara/ojos, manos, genitales, conteo de extremidades).** La causa real del problema de "genitales faltantes/estirados" en la muestra original no era anatomía imposible de resolver ni necesidad de ControlNet — era que el modelo dibujaba los genitales en sombra/oclusión y el sampler los "perdía". Nombrar explícitamente la iluminación y prohibir la oclusión en el negativo resolvió el problema de raíz, sin la fricción que metía ControlNet en manos/cara/lengua.

**Conclusión práctica**: para escenas de grupo (3+ personas), agregar SIEMPRE al prompt base la línea de iluminación explícita + el negativo de oclusión de genitales de arriba. **No hace falta ControlNet para esto** — guardarlo como último recurso si después de este fix una escena puntual sigue saliendo mal. La resolución 1536 no mostró una mejora clara sobre 1024 en esta muestra (ambas dieron 100% limpio) — no vale la pena el tiempo extra de generación como fix por defecto, salvo que se quiera más detalle general de imagen por otra razón.

## 14. Cuidado con LoRAs "recomendadas" que en realidad son de otro base model

Antes de usar una LoRA de forma regular, verificar el `baseModel` en Civitai (SDXL 1.0 vs Illustrious vs Pony vs SD 1.5 — NO son intercambiables, especialmente SD 1.5 que es arquitectura vieja incompatible). Si el usuario ve una imagen de ejemplo con estilo anime en la página de una LoRA tageada "SDXL 1.0", no asumir que está mal tageada ni que va a arruinar el estilo — **probarla directo y ver el resultado real** antes de descartarla o usarla con confianza.

## 15. "Hombres sin cara" (`faceless man` en positivo + `detailed male face` en negativo) pelea directamente contra pedir "full body, both figures visible, not cropped"

**Síntoma**: en escenas de 2 personas (o más) donde se pide explícitamente que ambas figuras estén visibles de cuerpo completo, el segundo sujeto (el hombre) desaparece del cuadro, o la composición se recorta de forma rara (close-up de cara cuando se pedía "wide shot"), incluso variando el orden gramatical del prompt o bajando la carga de desnudez.

**Causa real**: la convención de este proyecto (NewGame, escenas `bill_events.js`) pedía `faceless man` en el positivo Y tenía `detailed male face` en el negativo de todas las escenas NSFW compartidas (`_base_neg.txt`, `_explicit_neg.txt`, `_explicit_group_neg.txt`). Combinado con "both figures fully visible, full body, not cropped" en el mismo prompt, son dos objetivos en tensión directa: mantener a un personaje en cuadro completo mientras se le oculta activamente la cara empuja al modelo hacia crops cerrados o a sacarlo del cuadro — es más fácil "esconder" una cara recortando la composición que renderizando un cuerpo completo con la cara deliberadamente ausente/borrosa.

**Fix**: si una escena necesita "cuerpo completo, todos visibles, no recortado" Y ese personaje es un hombre que normalmente sería `faceless` por la convención del proyecto, dejar de pedir que sea faceless para esa escena puntual — quitar `faceless` del positivo, agregar "his face clearly visible" en su lugar, y usar una copia del negativo sin `detailed male face` (no editar el negativo compartido, otras escenas siguen usando la convención faceless). Resolvió el problema de recorte/desaparición de personajes en ~6-8 imágenes de una sola sesión, sin necesidad de seguir iterando con reformulaciones de framing.

**Cuándo aplica**: cualquier escena donde "full body / wide shot / not cropped / both fully visible" sea un requisito explícito. Si la escena solo necesita foco en la mujer (composición close-up donde el hombre puede quedar parcial/fuera de cuadro de forma natural), la convención `faceless` sigue funcionando bien y no hace falta este fix — es específicamente el choque con el requisito de "cuerpo completo visible" lo que lo rompe.

## 16. "Brazos enredados / proporciones mal" — el fix de grupo (lección 9/13) también aplica a poses de 2 personas con extremidades entrelazadas (2026-07-09)

**Síntoma reportado**: imágenes de humanos con anatomía enredada — brazos que salen mal, proporciones "trenzadas". No solo en gangbangs: pasa también en escenas íntimas de 2 personas donde las extremidades se cruzan (piernas envueltas alrededor de la cadera, brazos entrelazados, "tangle of limbs"). SDXL pierde de vista de quién es cada brazo cuando dos cuerpos se solapan.

**Diagnóstico** (sin poder generar test acá — GPU no disponible en el entorno; ver qué es validado vs. no abajo):
- El fix de manos de más (lección 9) y el de iluminación + `crop_factor`/`denoise` del Hand Detailer (lección 13) SOLO se estaban aplicando cuando el prompt se escribía como escena de grupo explícita ("gangbang", "two men", etc.). Una pareja entrelazada nunca gatillaba esos chequeos, así que el negativo `extra hands, extra limbs, extra arms` no se agregaba y la anatomía de brazos quedaba sin refuerzo.
- El pipeline hace segunda pasada de refinado solo a CARA y MANOS. Un codo/antebrazo mal formado en la generación base nunca recibe una segunda mirada — no hay detailer a nivel cuerpo/extremidad.

**Cambios aplicados (mínimos, sin costo extra de VRAM)**:
1. `WORKFLOW_MASTER_LUSTIFY.json` — Hand Detailer (nodo 16): `bbox_crop_factor` 1.8 → **2.0**, `denoise` 0.4 → **0.45**. Son los valores YA VALIDADOS de la lección 13 (muestra 14/14 limpia) que nunca se habían bajado al JSON — seguía en 1.8/0.4. Mismo nodo, solo params: cero VRAM/tiempo extra.
2. `prompts/_explicit_neg.txt` (negativo de 2 personas explícito) — agregado `extra hands, extra limbs, extra arms`. Antes solo `_explicit_group_neg.txt` (grupo) los tenía. Son tags planos y defensivos, no contradicen nada.
3. `writer-generator/scripts/draft_image_prompts.py` — el chequeo de "falta negativo de extremidades de más" ahora también gatilla en poses de 2 personas con extremidades entrelazadas (nuevo `_ENTANGLED_POS_RE`: "wrapped around", "intertwined", "legs around", "tangle of limbs", etc.), no solo en grupos literales. Regla 4 del SYSTEM_PROMPT actualizada para pedir conteo exacto de brazos/manos también en esas poses. El `autofix` agrega el negativo automáticamente.

**Qué NO se cambió en este momento, a propósito (disciplina de VRAM / riesgo de BSOD por carga sostenida)**:
- **NO se agregó todavía un detailer de cuerpo/extremidad** al workflow default en esta lección puntual. Motivo doble: (a) no había detector de persona instalado (`models/ultralytics/bbox/` solo tenía `face_yolov8m.pt` y `hand_yolov8s.pt`); (b) un bbox de "persona" cubre casi toda la imagen, así que un detailer ahí es una re-difusión de casi toda la imagen — mucho más pesado que el pass de mano. Quedó documentado como opción polish-tier. **Actualización 2026-07-09 (lección 17): el usuario decidió aceptar el costo extra de tiempo y se agregó de todas formas, con denoise/crop_factor bajos para no acercarse a una segunda generación completa — ver lección 17 para el detalle.**
- **NO se tocó ControlNet/SeedVR2/highres** en el path default — la investigación propia (lecciones 10, 13, doc 04) ya concluyó que son último recurso/polish, no primer intento.

**Estado de validación (importante)**: el cambio 1 (Hand Detailer 2.0/0.45) NO es nuevo — es el número ya validado en la muestra 14/14 de la lección 13, solo que ahora está en el JSON default. Los cambios 2 y 3 (negativo de extremidades en escenas de 2 personas + gatillo del drafter) son **untested** para el caso puntual de "brazos enredados en pareja" — son extrapolación razonable del fix de grupo ya validado, pero conviene batch-testearlos: generar una escena íntima de 2 personas con extremidades entrelazadas, con y sin el negativo `extra arms/limbs/hands`, y revisar brazos por separado (lección 11) antes de confiar en el fix de forma amplia.

## 17. Body/Limb Detailer agregado al workflow default (2026-07-09) — el usuario decidió aceptar más tiempo de generación

Después de la lección 16, el usuario pidió sumar directamente una tercera pasada de detailer a nivel cuerpo/extremidad (no solo cara/manos), aceptando el costo extra de tiempo para ver si reduce más los "brazos enredados". Se agregó, manteniendo la misma disciplina de VRAM que las lecciones anteriores (placa de 8GB, riesgo de BSOD 0x116 bajo carga sostenida).

**Qué se agregó a `WORKFLOW_MASTER_LUSTIFY.json`**:
- Nodo `17d` (`UltralyticsDetectorProvider`) apuntando a `segm/person_yolov8m-seg.pt` — detector de persona/cuerpo completo.
- Nodo `17` (`FaceDetailer`, el mismo truco de siempre — el nodo sirve para cualquier bbox) encadenado DESPUÉS del Hand Detailer (nodo 16) y ANTES de `SaveImage` (nodo 9, que ahora lee de `17` en vez de `16`). Settings deliberadamente livianos: `guide_size`/`max_size` 1024 (no 1536), `steps` 18 (similar al Hand Detailer), `denoise` **0.35** y `bbox_crop_factor` **1.2** — bajos a propósito porque un bbox de "persona" ya cubre casi todo el frame; con crop_factor/denoise altos esto sería casi una segunda generación completa de la imagen, justo el tipo de carga sostenida que hay que evitar en esta placa. Wildcard interno: `"full body, correct anatomy, natural proportions, natural limbs"`, mismo patrón que cara (`14`)/manos (`16d`). Seed propia randomizada, igual que los otros dos detailers.

**REQUIERE INSTALAR UN MODELO NUEVO ANTES DE USAR EL WORKFLOW** — no estaba instalado (`models/ultralytics/` solo tenía `face_yolov8m.pt` y `hand_yolov8s.pt`, sin detector de persona). Sin este archivo el workflow no carga:
- Archivo exacto: **`person_yolov8m-seg.pt`**
- Carpeta destino: `ComfyUI/models/ultralytics/segm/` (es un modelo de segmentación, no bbox — va en la subcarpeta `segm/`, no `bbox/`)
- Cómo conseguirlo: ComfyUI-Manager → "Install Models" → buscar `person_yolov8m-seg`, o bajar a mano de `https://huggingface.co/Bingsu/adetailer/resolve/main/person_yolov8m-seg.pt` (es el mismo modelo que el propio instalador de ComfyUI-Impact-Subpack referencia en su script `install.py`, así que es el estándar del ecosistema Impact Pack, no una elección arbitraria).

**Qué NO se tocó**: ControlNet/SeedVR2/highres siguen fuera del path default, mismo límite que la lección 16.

**Estado de validación — GUESS, no medido**: no se pudo correr ComfyUI en este entorno (sin GPU acá). Estimado a ojo en base a lo hablado antes: como es una pasada de denoise parcial sobre un crop (no una segunda generación completa), el costo extra debería rondar **+15-25% del tiempo de generación actual** — pero esto es una suposición, no un dato medido. **Verificar en la primera corrida real leyendo el log propio de ComfyUI (tiempo por nodo, aparece en consola/terminal al ejecutar), no confiar en este número.** Tampoco hay forma de saber todavía si esta pasada realmente reduce brazos enredados o si el bbox de "persona completa" es demasiado ancho para corregir un defecto puntual de brazo — probar en batch y revisar por categoría (lección 11) antes de asumir que ayuda.

## 18. Ojos deformes en cuerpo completo — el Face Detailer necesitaba mas denoise, no menos (2026-07-14, CONFIRMADO con A/B test)

**Síntoma**: en el workflow de oneObsession (anime, cuerpo completo), los ojos salían mal en casi todas las imágenes de prueba (asimétricos, un ojo bien y el otro deformado en una cuña oscura triangular sin forma de ojo).

**Causa real**: en una composición de cuerpo completo, la cara detectada por `face_yolov8m.pt` es un bbox chico (la cara ocupa una fracción mínima del frame de 632x1024/832x1216). El Face Detailer recorta ese bbox chico y lo sube de resolución hasta `guide_size`/`max_size` (1024) antes de re-difundir — eso es un factor de upscale grande partiendo de muy poca información real de origen. Con `denoise: 0.4` (heredado de LUSTIFY, nunca validado para cuerpo completo) el sampler no tenía suficiente libertad para reconstruir un ojo coherente desde ese crop borroso/upscaleado — el resultado era un ojo mal formado, no una glitch aleatoria.

**Test real (A/B, mismo seed/prompt/composición, único cambio: `denoise` del nodo 15)**:
- `denoise 0.4`: ojo derecho normal, ojo izquierdo deformado (cuña oscura sin forma de ojo).
- `denoise 0.55`: ambos ojos simétricos, iris/pupila bien formados, resto de la composición (pelo, ropa, encuadre) sin cambios.

**Fix aplicado**: `denoise` del Face Detailer (nodo 15) subido de 0.4 a 0.55 en `WORKFLOW_ANIME_ONEOBSESSION.json` (confirmado) y en `WORKFLOW_MASTER_LUSTIFY.json` (mismo nodo/lógica, pero NO retesteado ahí específicamente — LUSTIFY nunca se probó a propósito en cuerpo completo con cara chica en cuadro).

**Cuándo aplica**: cualquier escena donde la cara ocupe una fracción chica del frame (cuerpo completo, planos generales). En primeros planos/bustos (cara grande en cuadro) el crop de origen ya tiene suficiente detalle real y `denoise 0.4` funciona bien — no hace falta subirlo ahí.

**Otros ajustes del mismo día, no probados con A/B tan riguroso pero razonados**: `bbox_threshold` del Face Detailer bajado de 0.5 a 0.35 (ángulos de cabeza extremos dan detección de cara de baja confianza y el nodo se saltea entero si no baja el threshold). `flat color, flat shading, empty eyes, blank eyes` agregado al negativo (ver lección 20). Highres-fix (`LatentUpscaleBy` 1.4x + segundo `KSampler` denoise 0.4) agregado a ambos workflows antes de los detailers, porque ninguno de los dos lo tenía y el doc 04 ya lo marcaba como estándar para cuerpo completo.

## 19. El campo `wildcard` del Face/Hand/Body Detailer REEMPLAZA el prompt real si no lleva el prefijo `[CONCAT]` (2026-07-15, confirmado leyendo el código fuente de Impact Pack)

**Síntoma**: caras deformes en posiciones no frontales — boca en el lugar equivocado, nariz rara — incluso con denoise/threshold ya corregidos (lección 18). Le pasaba a cualquier escena, no solo a las de cuerpo completo raro.

**Causa real**: los 3 nodos `FaceDetailer` (cara, manos, cuerpo) tienen un campo `wildcard` con texto tipo `"portrait, close-up, face, 1girl"`. Confirmado en `ComfyUI/custom_nodes/comfyui-impact-pack/modules/impact/core.py` (función `enhance_detail`, línea ~267): si `wildcard_opt` no está vacío y NO empieza con `[CONCAT]`, la línea `positive = wildcard_positive` **reemplaza por completo** el prompt positivo real conectado al nodo, para ese recorte. O sea: el Face Detailer llevaba TODO este tiempo redibujando cada cara usando solo "portrait, close-up, face, 1girl" como guía — completamente ciego a la expresión real, ángulo de cabeza, o rasgos específicos del prompt de la escena (ej. "gritando", "de perfil", "ojo cibernético"). El modelo terminaba adivinando una cara genérica de frente y pegándola en un recorte que en realidad podía estar boca abajo, de perfil, o con la boca abierta gritando — de ahí rasgos en el lugar equivocado.

**Por qué manos/cuerpo se veían bien igual**: sus wildcards (`"close-up, hand, fingers"`, `"full body, correct anatomy..."`) son lo bastante genéricos como para que perder el prompt real no importe tanto — la anatomía de manos/cuerpo depende menos del contexto específico de la escena que una cara.

**Fix aplicado**: prefijo `[CONCAT]` agregado a los 3 wildcards en ambos workflows (`WORKFLOW_ANIME_ONEOBSESSION.json` y `WORKFLOW_MASTER_LUSTIFY.json`). Con `[CONCAT]`, el código usa `ConditioningConcat` para sumar el wildcard AL prompt real en vez de reemplazarlo — se mantiene el framing útil ("close-up, face") sin perder el contenido específico de la escena.

**Cuándo aplica**: siempre que se use un `wildcard` en cualquier nodo Detailer de Impact Pack. Si el campo wildcard no lleva `[CONCAT]`, asumir que está reemplazando el prompt real, no complementándolo.

## 20. LoRAs descargadas de Civitai/otras fuentes: verificar base model Y arquitectura antes de confiar, no solo probar y ver (2026-07-15)

**Contexto**: se agregaron dos LoRAs a `WORKFLOW_ANIME_ONEOBSESSION.json` para mejorar ojos (`EyesV1_400.safetensors`) y manos (`Hands zib v1.safetensors`). Los ojos empeoraron notablemente (brillo/glow quemado, textura ruidosa/estática en vez de iris limpio) y las manos empezaron a salir deformes a veces.

**Causa real (Eyes LoRA)**: metadata embebida en el propio `.safetensors` (`ss_base_model_version: sdxl_1.0`) confirma que se entrenó sobre SDXL 1.0 puro, NO sobre Illustrious/NoobAI. `oneObsession` es un fine-tune de Illustrious — mismo "SDXL family" pero espacio latente suficientemente distinto como para que los patrones aprendidos por la LoRA no encajen, y el efecto se nota peor justo donde la LoRA pesa más fuerte (los ojos).

**Causa real (Hands LoRA), peor todavía**: esta LoRA no tenía metadata, pero sus nombres de tensores internos son del tipo `diffusion_model.layers.0.adaLN_modulation...` — convención de arquitectura DiT (tipo Flux/SD3), NO la convención UNet de SDXL (`lora_unet_down_blocks_...`). Es decir, probablemente ni siquiera es una LoRA de SDXL — es de una arquitectura de modelo completamente distinta. La mayoría de sus pesos no corresponden a ninguna capa real del checkpoint.

**Fix aplicado**: ambas LoRAs removidas del workflow (nodos `LoraLoader` eliminados, todo vuelve a conectar directo del checkpoint). Vuelta al estado sin LoRAs, que es el que mejor se veía según el propio usuario.

**Regla general para la próxima vez que se quiera agregar una LoRA**:
1. Abrir el `.safetensors` y leer su metadata (`__metadata__` en el header) antes de usarla en serio — buscar `ss_base_model_version` o similar. Si dice `sdxl_1.0` a secas y el checkpoint destino es Illustrious/NoobAI, es sospechoso (lección 14 ya advertía esto en términos generales).
2. Si no hay metadata, mirar los nombres de los tensores: `lora_unet_...` o `lora_te...` = convención SDXL/kohya (bien). `diffusion_model.layers.N...`, `adaLN_modulation`, `double_blocks`/`single_blocks` = arquitectura DiT (Flux/SD3), incompatible con un checkpoint SDXL/Illustrious.
3. Probar UNA imagen de control antes de asumir que ayuda, y mirar específicamente la zona que la LoRA promete mejorar (ojos, manos) — no la composición general.
4. Preferir LoRAs que digan explícitamente "Illustrious" o "NoobAI" en su página de origen si el checkpoint destino es oneObsession, no "SDXL 1.0" genérico ni sliders/detailers armados para otro checkpoint (ver lección 01_checkpoints_disponibles.md).
