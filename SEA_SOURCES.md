# El mar: precios y disposiciones de PRODUCE

## Precios reales

La fuente automatizada es el listado público de [Reportes Coyunturales del Observatorio PRODUCEmpresarial](https://www.producempresarial.pe/category/pesca-acuicultura/artesanal-om/artesanal-reportes/), el observatorio de la Oficina General de Evaluación de Impacto y Estudios Económicos de PRODUCE. La identidad institucional y finalidad se describen en https://www.producempresarial.pe/acerca-de/ .

La consulta inicial del 29/10/2026 encontró como publicación más reciente el reporte del **28/10/2026**, con [PDF original](https://www.producempresarial.pe/wp-content/uploads/2026/10/28102026.pdf), SHA-256 `a5ff47d785e64e3e581c7960ab6e24538876d5d1b95b299d1781ede50aa9a310`.

Su tabla contiene 12 precios promedio mayoristas en soles por kg: seis en Lima y Callao, seis agregados regionales. No son mínimos/máximos ni precios individuales de Ventanilla, Villa María del Triunfo u otra ciudad. Los valores y las columnas anterior/actual se contrastaron visualmente con el PDF. Una ausencia se guarda como null; nunca como cero ni copiando el precio anterior. La fecha del precio y la de consulta son diferentes.

Se consultó manualmente el formulario público del Datero para dos mercados y tres fechas (27–29/10/2026). Devolvió únicamente filas sin especie y valores cero, sin observaciones útiles. No se importaron. El Datero no participa en la automatización: su robots.txt responde 403 y su formulario depende de tokens. Tampoco se usa el portal histórico www2 de PRODUCE por HTTP, endpoints de Power BI, ni el sitio Pesca y Consumo Responsable, que respondió 421. No se desactivó TLS ni se intentaron evasiones.

## Vedas y alcance normativo

El índice automatizado es la primera página del [compendio Vedas de PRODUCE](https://www.gob.pe/institucion/produce/colecciones/1918-vedas): 25 disposiciones recientes al momento de la integración. No se usa paginación `sheet`. Se conservan título, fecha de publicación, resumen completo de la página y enlaces a la página/PDF. Los resúmenes se almacenan por firma del título, fecha y extracto del índice; se vuelven a consultar al cambiar esa firma. `summaryCheckedAt` registra cuándo se obtuvo el resumen, que no equivale a la revisión jurídica de vigencia. El índice se consulta diariamente.

Se revisaron específicamente tres especies y cuatro periodos:

- Choro, Aulacomya atra: RM 00313-2026-PRODUCE. Publicada el 02/09; periodo desde 03/09 hasta 30/11/2026, litoral peruano. El PDF es escaneado; se revisó visualmente su artículo 1, incluidas las excepciones documentales por extracción anterior.
- Bagre andino, Rhamdia quelen: RM 00307-2026-PRODUCE, río Pampas dentro de Cangallo, Ayacucho. Periodo excepcional 03–30/09/2026; desde 2027, 01/06–30/09 anual. Excepciones con documentación de extracción anterior o procedencia de otra zona. No se aplica automáticamente a todo Ayacucho ni a todo el Perú.
- Paiche, Arapaima gigas: RM 215-2001-PE, modificada por RM 320-2020-PRODUCE. Del 01/10 al 28/02 siguiente, cuerpos de agua públicos del país excepto cuenca del Putumayo; la modificación permite la excepción documentada por extracción previa. Se leyó el original de 2020, que reproduce el periodo y modifica la excepción.

`data-input/sea/rules.json` conserva reglas revisadas y hashes de los originales. Cada actualización vuelve a leer esos tres PDF. Si cambia un original o la firma del índice, publica `reviewRequired=true`; la app muestra que hay cambios por revisar y no presenta un estado confirmado de periodo. El workflow termina en error después de publicar esa alerta y las nuevas disposiciones. Actualizar la firma revisada exige revisar las novedades; el runner nunca la acepta automáticamente.

**La cobertura es parcial.** Ni las 25 disposiciones ni los tres recursos revisados representan todas las vedas, cierres temporales, cuotas, tallas mínimas, restricciones regionales, autorizaciones exploratorias o condiciones de origen. Las publicaciones históricas no se clasifican automáticamente como vigentes. Estar fuera del periodo de una norma no autoriza pesca o venta; un precio publicado tampoco acredita disponibilidad, origen legal ni permiso. Las excepciones no se reducen a un indicador rojo/verde.

## Distribución y operación

El feed independiente es `sea/current.json` y `sea/releases/<sha256>/pack.json`. No modifica el esquema ni los precios agrícolas. El cliente valida hashes, tamaño, fechas, fuente, mercados y enlaces, guarda `sea-cache.json` atómicamente y conserva su copia si falla la red. Descarga compatible con el binario desde HTTPS, más una copia inicial incluida. Los paquetes se limitan a 1 MB; la primera versión ronda 32 KB.

El workflow público `cuymercado-sea.yml` usa runner estándar Ubuntu, se programa a las 21:45 UTC (16:45 Lima, con posibles retrasos de GitHub) y permite ejecución manual. Se consulta por la tarde porque el reporte inicial fue publicado después del mediodía. Comparte el grupo de concurrencia con agricultura para evitar pushes simultáneos, pero un fallo pesquero no bloquea su extracción. Comprueba robots.txt, limita solicitudes/tamaño/tiempo, usa identificación propia y un único reintento para errores transitorios de conexión. No publica PDF ni logos. Un fallo de acceso/extracción conserva el feed anterior; no modifica fechas para aparentar frescura. La app advierte al superar 48 horas desde la consulta de fuentes.
