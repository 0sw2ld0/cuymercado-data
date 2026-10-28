# CuyMercado · precios públicos y actualización diaria

El extractor, el workflow y los archivos de distribución viven en este repositorio público. La app iOS se mantiene privada. Se procesan precios publicados por MIDAGRI con fuente, mercado, unidad y fecha; consulte [DATA_POLICY.md](DATA_POLICY.md) para las reglas de acceso y reutilización.

## Consumo

Base HTTPS: `https://raw.githubusercontent.com/0sw2ld0/cuymercado-data/main`

`current.json` identifica el paquete con versión de esquema, fecha de corte, tamaño y SHA-256. `releases/<sha256>/pack.json` contiene catálogo e histórico. El cliente verifica integridad, conserva caché y muestra antigüedad. GitHub Raw puede tardar en reflejar un cambio por caché; no se garantiza disponibilidad ni actualización al minuto. Cloudflare sigue siendo una opción de distribución futura, sin proyecto configurado todavía.

## Actualización

Actions usa `ubuntu-24.04`, un runner estándar público. Ejecuta pruebas al cambiar el pipeline y consulta MIDAGRI diariamente a las 15:30 UTC (10:30 de Lima), además de permitir ejecución manual. Respeta robots.txt, consulta páginas directas sin paginación y descarga únicamente el último PDF enlazado, con identificación y límites. Un error conserva la versión anterior. No consulta endpoints internos de EMMSA.

Se publican los datos numéricos normalizados, no PDF ni contenido de la app. `data-input/reports.json` registra procedencia. Los JSON procesados permiten mantener el histórico sin volver a descargar todos los originales. Cada observación conserva fecha, unidad, documento, hash y página. La fuente y corte reales aparecen en el paquete; la fecha de ejecución no transforma un reporte antiguo en uno actual.

## Desarrollo y validación

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python etl/fetch_latest.py
python etl/build_release.py
```

Los tests sintéticos son temporales y se rechazan para publicación por defecto. El extractor falla ante fecha, hash, conteo o esquema inesperados. El conteo esperado actual es 72 filas; un catálogo distinto requiere revisión del formato. No se interpolan días ni se usan promedios semanales como precios diarios.

Opcionalmente, una ejecución manual puede desplegar en un proyecto Cloudflare existente mediante `deploy_cloudflare=true`, `CUY_DATA_PAGES_PROJECT`, `CLOUDFLARE_ACCOUNT_ID` y `CLOUDFLARE_API_TOKEN`. Nunca se incluyen secretos en la app o los JSON; no se crean recursos desde el workflow.

## Ampliar el histórico por publicación mensual

`python etl/backfill.py --publication URL_OFICIAL_MENSUAL --since AAAA-MM-DD` descarga únicamente los PDF enlazados y aún no registrados, con las mismas reglas de acceso. Está limitado a una publicación y 31 reportes por ejecución; valida todos antes de escribir el histórico. El corte no se adelanta: solo añade fechas anteriores. Después se genera una versión con `python etl/build_release.py`. No se rellena automáticamente un año ni se asume que existan todos los días.

La primera ampliación de octubre incorporó 18 fechas y 1.296 precios entre el 1 y el 27/10/2026. Los 504 valores anteriormente publicados se mantuvieron iguales.
