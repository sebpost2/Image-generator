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
