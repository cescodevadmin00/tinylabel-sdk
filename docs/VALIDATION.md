# Release validation / Validación de versión

Release / Versión: **0.1.0**, experimental.

Local validation used Windows and Python 3.12.10. / Validación local en Windows con Python 3.12.10.

| Check / Comprobación | Result / Resultado |
| --- | --- |
| `python -m unittest discover -s tests -v` | 40 tests passed / 40 pruebas aprobadas |
| `python scripts/check_docs.py` | Local Markdown link targets exist / Enlaces locales válidos |
| `python -m build --no-isolation` | Wheel and source distribution built / Wheel y distribución fuente construidos |
| `python scripts/check_wheel.py dist/tinylabel_sdk-0.1.0-py3-none-any.whl` | Extracted wheel imported in an isolated subprocess outside the source tree; private catalog and planner load / Wheel importado fuera del código fuente; catálogo y preparación válidos |
| Vendored snapshot integrity | 157 Python/JSON files match the pinned upstream snapshot byte-for-byte / 157 archivos coinciden byte por byte con la revisión original |
| Eight local source images, preparation only | All calculated 216-unit pitch, 174 bitmap rows + 42 advance; one mode initialization, no status query/reverse / Paso 216, 174 filas + 42 avance; una inicialización, sin consulta/retroceso |

The local source images and generated previews are excluded from the public repository and distributions. Tests use synthetic artwork. CI independently runs software checks on Windows/Linux with Python 3.10 and 3.12; consult the Actions page for actual run results.

Las imágenes locales y sus vistas previas quedan fuera del repositorio público y distribuciones. Las pruebas usan arte sintético. CI ejecuta verificaciones en Windows/Linux con Python 3.10 y 3.12; consulta Actions para conocer los resultados reales.

**No physical printing was performed for this SDK release validation.** Completion of the last label, final paper registration, alternative roll sizes and long physical batches remain acceptance work. See [hardware evidence](HARDWARE.md).

**Esta validación del SDK no imprimió papel.** La salida de la última etiqueta, posición final, tamaños alternativos y lotes físicos largos siguen pendientes de aceptación. Consulta la [evidencia física](HARDWARE.md).
