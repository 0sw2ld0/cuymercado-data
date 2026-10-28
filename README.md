# CuyMercado · procesamiento y distribución

Este repositorio público contiene el extractor, el generador de archivos versionados y GitHub Actions. La app iOS permanece en un repositorio privado independiente. El workflow usa un runner estándar `ubuntu-24.04`; no necesita acceder al repositorio privado ni usar un token entre repositorios.

## Estado real

Las pruebas usan datos sintéticos temporales, marcados como tales, que no se publican. No hay PDF ni precios reales en este repositorio. El acceso automatizado y la redistribución de las fuentes siguen pendientes de confirmar. Un workflow de pruebas exitoso no significa que los precios estén actualizados o publicados. No hay descarga programada ni acceso a endpoints internos de entidades.

## Pruebas

`python -m pip install -r requirements.txt`

`python -m unittest discover -s tests -v`

Las pruebas comprueban hash y reproducibilidad, conservación de unidades y datos faltantes, coherencia de catálogo e histórico, rechazo de duplicados y bloqueo de publicación de fixtures.

## Procesamiento de reportes revisados

Cuando se hayan confirmado las condiciones de uso y redistribución, aportar `data-input/reports.json` y los PDF revisados. Cada entrada del manifest debe tener `date` (AAAA-MM-DD), `file` (nombre local, sin directorios), `sha256`, `url` oficial y `expectedRows` (72 por defecto). El extractor valida la fecha del PDF, su hash, cobertura y unicidad. No calcula precios por conversiones ni considera promedios semanales como observaciones de un día.

`python etl/extract_reports.py --input data-input --output data-input/processed`

`python etl/build_release.py --resources data-input/processed --output dist`

Se generan `current.json`, `releases/<sha256>/pack.json` y `_headers`. El paquete incluye catálogo e histórico con fuente, fecha, unidad y trazabilidad. La fecha de corte determina antigüedad, no la hora de descarga.

## Actions y publicación

Cada cambio del pipeline ejecuta las pruebas. Sin fuentes revisadas y `CUY_DATA_REDISTRIBUTION_APPROVED=true`, la generación de precios queda desactivada. Una ejecución manual con `publish=true` publica el paquete en este repositorio mediante `GITHUB_TOKEN`, conservando las versiones anteriores. Los permisos de escritura solo se conceden a ese job. El repositorio puede requerir permitir escritura de Actions según su configuración.

El despliegue opcional `deploy_cloudflare=true` requiere un proyecto existente y la variable `CUY_DATA_PAGES_PROJECT`, además de los secretos `CLOUDFLARE_ACCOUNT_ID` y `CLOUDFLARE_API_TOKEN`. Solo se suben archivos de distribución; no el extractor ni tests. No se crea ningún recurso ni se modifica facturación desde el workflow.

La app se configura una vez con la URL HTTPS del sitio. Luego descarga versiones compatibles y mantiene caché local sin necesitar reinstalación para cada actualización de datos. Actualmente no hay proyecto ni URL de Cloudflare configurados.
