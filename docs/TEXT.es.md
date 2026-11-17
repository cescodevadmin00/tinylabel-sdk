# Etiquetas de texto y campos externos — 0.2.0

[English](TEXT.en.md) · [Manual de usuario](USER_GUIDE.es.md) · [Integración](INTEGRATION.es.md)

## Qué recibe el SDK

La versión 0.2.0 añade etiquetas de texto configurables. Tu aplicación puede obtener valores de Excel, una base de datos, formulario o API, componer el texto externamente y entregarlo al SDK. **El SDK no abre ni importa archivos Excel.** No requiere librerías de hojas de cálculo.

El texto se convierte en ráster a la escala nativa y comparte con las imágenes el lienzo físico, márgenes, calibración, umbral, empaquetado de filas, paso, sesión y registro. No se envían comandos de fuentes nativas de la impresora sin verificar. Textos e imágenes pueden compartir un lote y sesión continuos.

Se mantienen la compatibilidad U1/Classic y el estado experimental. Después de publicar 0.2.0 se aceptaron una prueba individual de texto y un lote de cinco etiquetas con logo/campos compuestos externamente, en esta U1/Windows con papel de 50 × 25 mm y separación de 2 mm. Los lotes largos, otros tamaños y el origen final del rollo siguen pendientes. Consulta [evidencia física](HARDWARE.md).

## Una etiqueta configurada

```python
from tinylabel_sdk import Media, TextLabel, TextStyle, prepare_text_batch

label = TextLabel.from_text(
    "Café molido\nPrecio: USD 7,82\nLote: 0017",
    label_id="producto-0017",
    style=TextStyle(font_size_mm=3, align="center", bold=False),
    vertical_align="center",
)
plan = prepare_text_batch([label], Media(50, 25, 2))
plan.save_previews("preview-text")  # sin Bluetooth ni movimiento de papel
```

`font_size_mm` indica el tamaño nominal de la fuente en milímetros, referido al cuerpo tipográfico. La altura de tinta depende de las métricas; no significa que cada mayúscula mida exactamente esos milímetros. A 8 puntos/mm, 3 mm selecciona una fuente de 24 píxeles. Revisa la vista previa a tamaño nativo y valida legibilidad física.

El perfil inicial conserva los desplazamientos +2 mm horizontal y −0,25 mm vertical usados en las imágenes. Son ajustes del equipo/rollo, no avances nuevos exclusivos del texto. Por defecto se centra la extensión vertical visible del texto. Otros anchos y alturas se calculan dinámicamente.

## Título y detalles con estilos diferentes

```python
from tinylabel_sdk import TextBlock, TextLabel, TextStyle

label = TextLabel("producto-0017", blocks=(
    TextBlock("Café molido", TextStyle(font_size_mm=4, bold=True), gap_after_mm=0.75),
    TextBlock("USD 7,82\nLote: 0017", TextStyle(font_size_mm=3, align="left")),
), vertical_align="center")
```

| Ajuste | Significado / valor inicial |
| --- | --- |
| `TextStyle.font_size_mm` | Tamaño nominal, 3 mm |
| `TextStyle.align` | `left`, `center` (inicial), `right`, por bloque |
| `TextStyle.bold` | Fuente incluida normal/negrita; inicial `False` |
| `TextStyle.font_path` | Ruta opcional a fuente local `.ttf`/`.otf` |
| `TextStyle.line_spacing_mm` | Espacio adicional entre líneas, 0,5 mm |
| `TextStyle.wrap` | Ajuste automático de líneas, inicial `True` |
| `TextBlock.gap_after_mm` | Separación adicional entre bloques, 0,75 mm; no deja relleno visible después del último |
| `TextLabel.vertical_align` | `top`, `center` (inicial), `bottom` |
| `TextLabel.overflow` | `error` (inicial) o reducción explícita `shrink` |
| `TextLabel.min_font_size_mm` | Mínimo al reducir, 1,5 mm |

Se respetan saltos explícitos. El ajuste automático normaliza espacios entre palabras y divide identificadores demasiado largos; usa `wrap=False` si un código debe quedar en una línea. Las tabulaciones se expanden a espacios. Se conservan líneas vacías internas; el espacio vertical vacío al principio/final no cambia el centrado de la tinta visible. Los bloques comparten área de texto y no alteran el paso del papel.

Se incluyen **Noto Sans Regular/Bold**, con los acentos, ñ y símbolos monetarios de los ejemplos comprobados por las pruebas. El paquete conserva archivos, licencia OFL-1.1 y procedencia. Otros sistemas de escritura requieren fuente adecuada y revisión visual: no se promete sustitución automática de fuentes ni cobertura Unicode universal. Para fuente personalizada negrita selecciona directamente su archivo mediante `font_path` y deja `bold=False`; combinar ruta personalizada con `bold=True` se rechaza. Fija la versión de fuente para tipografía consistente; fija también Pillow/FreeType si necesitas ráster idéntico píxel por píxel entre equipos.

## Datos externos ya formateados

El límite de integración son cadenas de texto. La aplicación decide cómo tratar tipos de celda, ceros iniciales, fórmulas, vacíos, decimales, moneda y fechas **antes** de crear la etiqueta. Evita convertir un vacío accidentalmente en `None` visible y no supongas que una celda numérica de Excel conserva los ceros mostrados en pantalla.

```python
from tinylabel_sdk import TextLabel, format_text, prepare_text_batch

# Resultado de tu aplicación, independientemente de cómo lea Excel:
filas = [
    {"id": "producto-0017", "nombre": "Café molido", "precio": "USD 7,82", "lote": "0017"},
    {"id": "producto-0018", "nombre": "Arroz integral", "precio": "USD 5,83", "lote": "0018"},
]
labels = [TextLabel.from_text(
    format_text("{nombre}\n{precio}\nLote: {lote}", fila), label_id=fila["id"]
) for fila in filas]
plan = prepare_text_batch(labels)
```

También puedes componer toda la cadena fuera del SDK mediante tu motor de plantillas o f-string. `format_text` es opcional. Admite campos planos como `{nombre}` o `{Nombre del producto}` y valores de tipo cadena. Campos ausentes, números o `None` producen `ConfigurationError`. No permite acceso a atributos/índices, conversiones, evaluación, sustitución anidada ni especificadores de formato: da formato a números/fechas fuera. Usa `{{`/`}}` para llaves literales. Los valores con llaves no se interpretan otra vez.

Ejecuta el [ejemplo de campos externos](../examples/text_from_fields.py), que solo genera vistas previas:

```shell
python examples/text_from_fields.py
```

## JSON externo y CLI

Otros lenguajes pueden entregar JSON UTF-8. Una etiqueta contiene `text` literal, `template` con `fields`, o un arreglo `blocks`. Cada bloque exige exactamente uno entre `text` y `template`. Las plantillas usan los `fields` de su etiqueta; `text` nunca se interpola. Se rechazan ajustes desconocidos para detectar errores de escritura. Las rutas de fuentes del JSON son relativas al archivo JSON.

```json
{
  "schema": 1,
  "labels": [
    {
      "label_id": "producto-0017",
      "template": "{nombre}\n{precio}\nLote: {lote}",
      "fields": {"nombre": "Café molido", "precio": "USD 7,82", "lote": "0017"},
      "style": {"font_size_mm": 3, "align": "center"},
      "vertical_align": "center",
      "overflow": "error"
    }
  ]
}
```

Revisa el [ejemplo JSON con varios estilos](../examples/text_labels.json):

```shell
tinylabel preview-text examples/text_labels.json --profile profiles/u1_50x25_gap2.json --out preview-text
tinylabel preview-text examples/text_labels.json --width-mm 40 --height-mm 30 --gap-mm 2 --out preview-text-40x30
```

Para una impresión autorizada y alineada físicamente:

```shell
tinylabel print-text examples/text_labels.json --target U1-XXXX --profile profiles/u1_50x25_gap2.json --journal .label-jobs --job-id lote-texto-104-v1 --aligned
```

Todo el texto se prepara y verifica antes de conectar. `print-text` mantiene las reglas de alineación, IDs persistentes, flujo, espera y confirmación física de `print`. El éxito sigue siendo `transmitted_unconfirmed` hasta observar el papel. `inspect`, `confirm` y `recover` funcionan como explica el [manual](USER_GUIDE.es.md).

## Ajuste, posición y validación

Con `overflow="error"`, texto demasiado ancho/alto produce `GeometryError` antes del envío. No se recorta ni se reduce silenciosamente. Con `overflow="shrink"`, disminuye una escala común de fuentes, conserva la jerarquía y recalcula líneas. Nunca baja del mínimo; las separaciones mantienen sus valores. Si no cabe al mínimo, se rechaza. Reducir puede afectar legibilidad: valida el tamaño impreso antes de producción.

`plan.summary()` y `plan.json` incluyen `text_layout`: tamaños finales por bloque en píxeles, cantidad de líneas, `shrunk`, área y alineación vertical. `content_box_px` describe la extensión renderizada. El registro de trabajos no guarda el texto ni los campos; la aplicación debe conservar definiciones inmutables para recuperación.

Para mezclar contenido usa `prepare_batch([TextLabel(...), LabelInput(...)], media)`. Entrega el plan al mismo `printer.print_batch(plan, job_id=...)`; no existe otro ciclo de impresora para texto. El avance se calcula según las filas reales y el paso compartido. No reutilices los valores antiguos de 174 filas/42 de avance para texto.

Antes de activar, revisa campos largos/cortos, acentos y vacíos. Después autoriza validación física de cantidad, primera/última posición, límite final y legibilidad. El cálculo de paso por sí solo no demuestra alineación física.
