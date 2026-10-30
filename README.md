# CuyMercado · precios públicos y actualización diaria

El extractor, el workflow y los archivos de distribución viven en este repositorio público. La app iOS se mantiene privada. Se procesan precios publicados por MIDAGRI con fuente, mercado, unidad y fecha; consulte [DATA_POLICY.md](DATA_POLICY.md) para las reglas de acceso y reutilización.

## Consumo

Base HTTPS: `https://raw.githubusercontent.com/0sw2ld0/cuymercado-data/main`

`current.json` identifica el paquete con versión de esquema, fecha de corte, tamaño y SHA-256. `releases/<sha256>/pack.json` contiene catálogo e histórico. El cliente verifica integridad, conserva caché y muestra antigüedad. GitHub Raw puede tardar en reflejar un cambio por caché; no se garantiza disponibilidad ni actualización al minuto. Cloudflare sigue siendo una opción de distribución futura, sin proyecto configurado todavía.

## Actualización

Actions usa `ubuntu-24.04`, un runner estándar público. Ejecuta pruebas al cambiar el pipeline y consulta MIDAGRI diariamente a las 15:30 UTC (10:30 de Lima), además de permitir ejecución manual. Respeta robots.txt, consulta páginas directas sin paginación y descarga el último PDF enlazado, con identificación y límites. Recupera también los reportes intermedios desde el último corte (hasta tres publicaciones mensuales); valida todo en una carpeta temporal antes de modificar los datos publicables. Si la interrupción supera ese límite, falla y requiere una carga histórica explícita. Un error conserva la versión anterior. No consulta endpoints internos de EMMSA.

Se publican los datos numéricos normalizados, no PDF ni contenido de la app. `data-input/reports.json` registra procedencia. Los JSON procesados permiten mantener el histórico sin volver a descargar todos los originales. Cada observación conserva fecha, unidad, documento, hash y página. La fuente y corte reales aparecen en el paquete; la fecha de ejecución no transforma un reporte antiguo en uno actual.

## Desarrollo y validación

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python etl/update_daily.py
python etl/build_release.py
```

Los tests sintéticos son temporales y se rechazan para publicación por defecto. El extractor falla ante fecha, hash, conteo o esquema inesperados. El paquete se limita a 8 MB para mantener compatibilidad con la app instalada. El conteo esperado actual es 72 filas; un catálogo distinto requiere revisión del formato. No se interpolan días ni se usan promedios semanales como precios diarios.

Opcionalmente, una ejecución manual puede desplegar en un proyecto Cloudflare existente mediante `deploy_cloudflare=true`, `CUY_DATA_PAGES_PROJECT`, `CLOUDFLARE_ACCOUNT_ID` y `CLOUDFLARE_API_TOKEN`. Nunca se incluyen secretos en la app o los JSON; no se crean recursos desde el workflow.

## Ampliar el histórico por publicación mensual

`python etl/backfill.py --publication URL_OFICIAL_MENSUAL --since AAAA-MM-DD` descarga únicamente los PDF enlazados y aún no registrados, con las mismas reglas de acceso. Está limitado a una publicación y 31 reportes por ejecución; valida todos antes de escribir el histórico. El corte no se adelanta: solo añade fechas anteriores. Después se genera una versión con `python etl/build_release.py`. No se rellena automáticamente un año ni se asume que existan todos los días.

La primera ampliación de octubre incorporó 18 fechas y 1.296 precios entre el 1 y el 27/10/2026. Los 504 valores anteriormente publicados se mantuvieron iguales.

## Verificación de la programación

El workflow está activo. Las ejecuciones programadas del [28/10/2026](https://github.com/0sw2ld0/cuymercado-data/actions/runs/40763713684) y [29/10/2026](https://github.com/0sw2ld0/cuymercado-data/actions/runs/40949385619) publicaron correctamente los reportes de esos días. La programación es diaria; GitHub puede retrasar el inicio (esas ejecuciones comenzaron aproximadamente a las 15:29 de Lima). No garantiza datos nuevos cada día: depende de la publicación de MIDAGRI. El resumen de cada ejecución informa corte, antigüedad, número de fechas y observaciones; los errores impiden publicar.

El lector histórico v2 reconoce «setiembre» y «septiembre», ignora la columna de promedio semanal (no se usa como precio diario) y corrige únicamente los marcadores ocultos de volumen de la fila «Zapallo Macre» en el formato antiguo, contrastados visualmente. Nunca corrige ni rellena precios ausentes. `--skip-invalid` es una opción explícita para cargas históricas: registra los documentos rechazados en `data-input/rejected-reports.json`, sin importar sus filas. El Action diario conserva el modo estricto y no omite errores. `--cache /ruta/temporal` permite reutilizar originales locales; esos PDF no se publican.

El paquete vigente conserva una ventana móvil de 360 días hasta el corte oficial; las versiones publicadas anteriores se conservan por hash. Esto evita que la descarga crezca indefinidamente y supere el límite del cliente instalado. La procedencia de los reportes sigue registrada aunque una observación salga de la ventana vigente.

## Histórico ampliado, verificado el 29/10/2026

El paquete publicado tiene 72 productos, 17.352 observaciones y 241 fechas del 04/11/2025 al 29/10/2026 (ventana de 360 días calendario). No se rellenan fines de semana, feriados ni reportes ausentes. Cuatro documentos inconsistentes quedaron excluidos; sus URLs, hashes y motivos están en `data-input/rejected-reports.json`. La auditoría de esta ampliación está en `data-input/audits/history-2026-10-29.json`: se contrastaron los 222 originales descargados durante la carga y se conservaron intactas las 1.440 observaciones publicadas antes de ella. El paquete pesa 5.567.169 bytes. La auditoría es una evidencia fechada; el corte vigente siempre se consulta en `current.json`.

## El mar · feed independiente

`https://raw.githubusercontent.com/0sw2ld0/cuymercado-data/main/sea/current.json` identifica el paquete de precios pesqueros y disposiciones de PRODUCE. `python etl/update_sea.py` consulta el reporte y el compendio; `--build-only` valida y reconstruye los inputs ya guardados. Workflow público `cuymercado-sea.yml`, diario a las 16:45 Lima y bajo demanda. La cobertura inicial es de 12 precios promedio al 28/10/2026, 25 disposiciones recientes y periodos revisados de choro, paiche y bagre andino. No afirma contener todas las vedas vigentes. Consulte [SEA_SOURCES.md](SEA_SOURCES.md) antes de interpretar o ampliar sus reglas. Los cambios normativos disparan una alerta de revisión; no se aceptan automáticamente como permisos de pesca o venta.

## Escudo · alertas y registros

`shield/current.json` distribuye comunicados alimentarios revisados de DIGESA y noticias detectadas en MINSA. El workflow público `cuymercado-shield.yml` revisa diariamente a las 17:15 Lima los listados oficiales accesibles; no renueva la revisión editorial de los comunicados. El formulario real DIGESA se consulta interactivamente desde iOS. Cobertura parcial, fuente, lote y fechas explícitas: [SHIELD_SOURCES.md](SHIELD_SOURCES.md). `python etl/update_shield.py` consulta y publica; `--build-only` reconstruye el paquete ya guardado. Las fuentes que bloquean automatización no se eluden.
