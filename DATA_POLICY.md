# Política de fuentes y publicación

CuyCoders publica hechos numéricos extraídos de reportes de precios de acceso público de MIDAGRI, con atribución, fecha, mercado, unidad y enlaces originales. No se presenta como servicio oficial ni usa logos institucionales. Los originales PDF no se redistribuyen aquí. Las imágenes y la app iOS no forman parte de este repositorio.

La ausencia de una licencia explícita no se interpreta como una prohibición general sobre simples hechos o datos. El artículo 9 del Decreto Legislativo 822 excluye estos de la protección por derecho de autor. Esto no equivale a afirmar que toda base de datos o todo contenido del portal carezca de protección, ni a atribuirle una licencia abierta que no publica. Referencia oficial: https://www.leyes.congreso.gob.pe/Documentos/DecretosLegislativos/00822.pdf . El usuario autorizó la publicación de los hechos extraídos y la actualización respetuosa de las fuentes el 28/10/2026. No se declara una autorización escrita de MIDAGRI o EMMSA.

El canal automatizado es el PDF que MIDAGRI enlaza en su compendio oficial. Se comprueba robots.txt de cada origen; se excluyen administración y paginación `sheet`, se usa un User-Agent identificable, se limitan tamaño y tiempo y se espacian las solicitudes. No hay endpoints internos, CAPTCHA, sesiones ni verificaciones TLS desactivadas. Se consulta una vez al día a las 10:30 de Lima (15:30 UTC); el horario del scheduler no se garantiza al minuto.

Si la fuente falla, bloquea el acceso, cambia el esquema o no supera validaciones, el job falla antes de publicar y se mantiene la última versión. La consulta registra URL, estado HTTP, hash y hora UTC en los logs de Actions. Cuando no cambia el PDF no se inventa un precio nuevo ni se cambia su fecha. No se garantiza que el último dato sea del día.

Las series de EMMSA se consultan aparte y no se mezclan con MIDAGRI. Las unidades se conservan; un kilogramo no se convierte en saco o jaba. Los precios de periodos anteriores no son cotizaciones actuales ni pronósticos.

Los originales se procesan temporalmente en el runner y se identifican por hash en cada observación. Los manifiestos de reportes registran procedencia; los paquetes versionados permiten inspeccionar qué datos se distribuyeron. La detección de cambios y un hash no sustituyen una auditoría independiente de exactitud.
