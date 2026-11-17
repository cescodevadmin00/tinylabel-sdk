# Manual de usuario

[English](USER_GUIDE.en.md) · [Inicio](../README.es.md) · [Integración](INTEGRATION.es.md)

## 1. Preparar el equipo

Instala Python >=3.10 y el SDK siguiendo las [instrucciones](../README.es.md#instalación). Para imprimir necesitas una U1 y Bluetooth Classic/SPP en la computadora. Enciende la impresora, carga papel compatible y empareja mediante el sistema operativo si es necesario. Desconecta TinyPrint y otras aplicaciones que puedan ocupar la conexión. Usa el nombre o dirección exactos como `--target`; `U1-XXXX` es un ejemplo para sustituir.

La versión actual es experimental. Consulta [compatibilidad](COMPATIBILITY.md) y [evidencia física](HARDWARE.md) antes de usarla en producción. Las rutas pertenecen al equipo que ejecuta Python. Los ejemplos con perfiles suponen un repositorio clonado; instalando solo el wheel puedes usar los valores predeterminados o descargar el JSON por separado.

## 2. Seleccionar papel e imágenes

El ancho cruza el cabezal. La altura sigue el movimiento del papel. `gap_mm` es la separación entre etiquetas precortadas y no forma parte de la altura. El valor inicial es ancho=50, alto=25, separación=2 mm: paso total de 27 mm. En papel continuo usa separación 0 y define deliberadamente la altura de cada segmento; no hay control de cortador.

Cada imagen estática corresponde a una etiqueta. Se recomienda PNG; también se admiten formatos ráster estáticos decodificables por Pillow. La transparencia se convierte en blanco y se respeta la orientación EXIF. La imagen conserva su proporción, se ajusta al área disponible y pasa a blanco/negro por umbral. Usa texto y códigos de alto contraste; una vista previa no certifica la lectura de códigos. No se aceptan PDF, animaciones ni lenguajes de comandos de impresora.

Valores iniciales: oscuridad 5/5, margen 2 mm, desplazamiento horizontal +2 mm y vertical −0,25 mm. Estos ajustes reproducen la configuración de las pruebas anteriores; no son valores universales para todos los rollos. X positivo mueve a la derecha; Y positivo mueve hacia abajo en la etiqueta. Se rechaza una calibración que recorte la imagen.

## 3. Revisar sin gastar papel

```shell
tinylabel preview primera.png segunda.png --profile profiles/u1_50x25_gap2.json --out preview
```

Revisa `preview/0001.png`, `0002.png` y `plan.json`. Los PNG muestran los 384 puntos del cabezal; para rollos más estrechos el área física se centra dentro del cabezal. La salida JSON incluye dimensiones, posición del contenido, huellas digitales y `printed:false`.

Para seleccionar otro tamaño:

```shell
tinylabel preview primera.png --width-mm 40 --height-mm 30 --gap-mm 2 --darkness 4 --out preview
```

También puedes copiar un perfil y modificar `media`, `calibration`, `options` y `drain`. El [ejemplo de 40 × 30](../profiles/u1_40x30_gap2.example.json) no está validado físicamente. No aumentes límites de ancho ni escalas para evitar un error sin comprobar antes la capacidad real del equipo.

## 4. Alinear el origen físico

Alinea el inicio de una etiqueta usando el procedimiento conocido de la impresora/app y desconecta la app. El SDK no consulta el sensor de separación ni busca el origen automáticamente. Tras detener la impresora, apagarla, cambiar papel, moverlo manualmente o detectar etiquetas ausentes/desplazadas, considera desconocida la posición y vuelve a alinear.

`--aligned` y `confirm_alignment()` registran esa acción del operador; no mueven papel. Cada sesión nueva exige confirmación. Dentro de una sesión persistente no reinicies entre etiquetas ni lotes: conserva el mismo papel, calibración y opciones hasta cerrar.

## 5. Enviar un lote

Usa un identificador único y estable para la solicitud intencional:

```shell
tinylabel print primera.png segunda.png --target U1-XXXX --profile profiles/u1_50x25_gap2.json --journal .label-jobs --job-id envio-104-v1 --aligned
```

El orden de impresión es el orden de argumentos. El ejemplo de carpeta ordena los PNG numéricos por número y los demás por nombre. No hay duplicación implícita. Todos los procesos que usen la misma impresora deben compartir un único directorio persistente de registro; no crees uno temporal o distinto para cada solicitud.

La conexión permanece abierta durante el envío y la espera pasiva. La espera predeterminada supone de manera conservadora 2 mm/s mínimos: ocho pasos de 27 mm requieren aproximadamente 108 segundos desde el comienzo del envío, más las condiciones de estabilización/silencio que correspondan. Sigue siendo una estimación. Las pausas de flujo deben terminar; una desconexión o espera agotada deja el resultado incierto. No mates el proceso porque Bluetooth ya haya enviado todos los bytes.

Después del último paso calculado, el SDK no añade expulsión, retroceso, reinicio de modo ni consulta final de estado. Al cerrar solo desconecta el transporte. No sabe si la posición física final es correcta.

## 6. Interpretar el comprobante

| Estado | Significado | Acción |
| --- | --- | --- |
| `reserved` | ID reservado de forma persistente | Si murió el proceso, inspeccionar y recuperar sin reenvío automático |
| `sending` | Comenzó el envío; puede quedar así tras un cierre abrupto | Tratar como incierto hasta revisar |
| `transmitted_unconfirmed` | Datos enviados y espera pasiva terminada | Comprobar etiquetas reales y posición |
| `uncertain` | Error, cancelación o proceso interrumpido | Puede haberse impreso parte o todo; revisar |
| `confirmed` | Operador registró todos los IDs solicitados | Revisar también `physical_alignment_ok` |
| `partial_confirmed` | Operador registró un subconjunto, incluso vacío | Revisar faltantes antes de autorizar recuperación |

`transmitted:true` solo demuestra envío. `confirmed_label_ids:null` indica que no hay observación física registrada. `position_after:"expected_next_label_start"` es una expectativa, no una lectura del sensor. Incluso `confirmed` requiere realinear si `physical_alignment_ok:false`.

Consultar un trabajo:

```shell
tinylabel inspect --journal .label-jobs --job-id envio-104-v1
```

Después de comprobar físicamente ambas etiquetas y la posición:

```shell
tinylabel confirm --journal .label-jobs --job-id envio-104-v1 --label-id primera.png --label-id segunda.png --alignment-ok --note "Ambas etiquetas revisadas"
```

Las rutas usan el nombre de archivo como ID. En Python, `LabelInput` permite IDs del negocio. Confirmar es una declaración del operador, no telemetría. Omite `--alignment-ok` si la posición es incorrecta o desconocida.

Códigos de salida: **0**, operación de software completada, consultar estado; **2**, entrada inválida o error; **4**, trabajo no encontrado por `inspect`. Los errores de argumentos pueden ser texto de argparse; los errores de operación salen como JSON por stderr. Tras un error de impresión consulta siempre el registro.

## 7. Recuperar sin duplicar etiquetas

Si el proceso murió dejando `reserved`/`sending`, detén el proceso anterior, revisa el papel y marca explícitamente el trabajo como incierto:

```shell
tinylabel recover --journal .label-jobs --job-id envio-104-v1 --note "Proceso detenido; revisando salida"
```

La operación obtiene el mismo bloqueo, rechaza una impresora ocupada y no envía comandos Bluetooth. No libera el ID para reutilizarlo. Registra con `confirm` los IDs realmente observados.

Si falta únicamente la última imagen, no repitas el lote. Identifica el faltante, realinea y autoriza otra solicitud con **solo esa imagen** y un ID nuevo, por ejemplo `envio-104-recuperacion-1`. El SDK nunca hace esa impresión de recuperación automáticamente.

## 8. Resolver problemas

| Síntoma | Revisión / respuesta |
| --- | --- |
| Impresora no encontrada | Nombre exacto, encendido, emparejamiento, adaptador Classic y app desconectada; solo se admite modelo `u1` |
| `PrinterBusy` | Otro proceso tiene el control; compartir registro y serializar solicitudes |
| Primera etiqueta desplazada | Origen físico y desplazamientos de calibración; la vista previa describe el ráster |
| Desplazamiento acumulativo | Altura/separación medidas, escala de avance y una sola inicialización; validar lote largo |
| Falta última etiqueta / posición final incorrecta | Revisar IDs físicos, registrar subconjunto, realinear y recuperar solo faltantes |
| Negro claro | Revisar oscuridad, batería y papel; energía/velocidad del protocolo no son unidades físicas calibradas |
| `DuplicateJob` | Consultar comprobante; no cambiar ID solo para evitar el bloqueo |
| `DeliveryUncertain` / tiempo agotado | Revisar registro y papel; sin reintento automático |

Antes de cambiar rollo/perfil en producción, revisa la vista previa, una etiqueta, un lote corto y uno largo, contando etiquetas y comparando la primera/última y la posición final. La calibración no garantiza el resultado físico sin esta validación.
