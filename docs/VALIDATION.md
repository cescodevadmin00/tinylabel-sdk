# Release validation / Validación de versión

Release / Versión: **0.2.0**, experimental.

Local validation used Windows and Python 3.12.10. / Validación local en Windows con Python 3.12.10.

| Check / Comprobación | Result / Resultado |
| --- | --- |
| `python -m unittest discover -s tests -v` | 68 tests passed: original image/session suite plus text, fields and JSON / 68 pruebas aprobadas, incluyendo regresión y texto |
| `python scripts/check_docs.py` | Local Markdown link targets exist / Enlaces locales válidos |
| `python -m build --no-isolation` | Wheel and source distribution built / Wheel y distribución fuente construidos |
| `python scripts/check_wheel.py dist/tinylabel_sdk-0.2.0-py3-none-any.whl` | Extracted wheel imported outside the source tree; private catalog, image/text planner and packaged fonts load / Wheel importado fuera del código fuente; catálogo, imágenes, texto y fuentes válidos |
| Vendored snapshot integrity | 157 Python/JSON files match the pinned upstream snapshot byte-for-byte / 157 archivos coinciden byte por byte con la revisión original |
| Eight local source images, preparation only | All calculated 216-unit pitch, 174 bitmap rows + 42 advance; one mode initialization, no status query/reverse / Paso 216, 174 filas + 42 avance; una inicialización, sin consulta/retroceso |
| Text at 50 × 25 and 40 × 30 mm | Previews inspected; wrapping, offsets and dynamic dimensions checked / Vistas previas revisadas, dimensiones y ajustes comprobados |
| Typography and fields | Accents, ñ, currency symbols, bold, zero-prefixed identifiers, missing fields, overflow/minimum size, mixed batches / Acentos, ñ, moneda, negrita, ceros iniciales, faltantes, desbordamiento y lotes mixtos |
| Font provenance | Bundled Noto Sans Regular/Bold and OFL checksums verified / Fuentes y licencia verificadas mediante SHA-256 |

The local source images and generated previews are excluded from the public repository and distributions. Tests use synthetic artwork. CI independently runs software checks on Windows/Linux with Python 3.10 and 3.12; consult the Actions page for actual run results.

Las imágenes locales y sus vistas previas quedan fuera del repositorio público y distribuciones. Las pruebas usan arte sintético. CI ejecuta verificaciones en Windows/Linux con Python 3.10 y 3.12; consulta Actions para conocer los resultados reales.

**No physical printing was performed during package creation.** In subsequent testing on 2026-11-17, the operator accepted single text/mixed proofs and all five consecutive mixed labels on one U1/Windows setup with 50 × 25 mm media and a 2 mm gap. The host application composed fixed artwork and external fields before passing them to the SDK. Final roll origin, alternative media and long physical batches remain unverified. See [hardware evidence](HARDWARE.md).

**La creación del paquete no imprimió papel.** En pruebas posteriores del 17/11/2026, el operador aceptó pruebas individuales de texto/mixtas y las cinco etiquetas consecutivas, en una U1/Windows con papel de 50 × 25 mm y separación de 2 mm. La aplicación externa compuso recursos fijos y campos antes de entregarlos al SDK. El origen final del rollo, otros tamaños y lotes largos siguen sin verificar. Consulta la [evidencia física](HARDWARE.md).
