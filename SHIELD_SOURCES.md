# Escudo · fuentes y alcance

Integración solicitada el 30/10/2026. No es un servicio oficial ni una certificación de seguridad.

## Consulta sanitaria interactiva

La portada de DIGESA enlaza el formulario vigente:
https://consultas-digesa.minsa.gob.pe/ConsultaWebRS/Consultas/Consulta_Registro_Sanitario.aspx

Se comprobó con el formulario público la consulta `P0652824`, que devolvió el registro `P0652824N/NAINYY`, producto agua de mesa sin gas, marcas Timonel/Lybre, empresa INCO BRANDS. La existencia del registro y su fecha de vencimiento **no** acreditan ausencia de alertas ni autenticidad. La app muestra los resultados originales de DIGESA en una vista web, sin crear una base paralela de registros ni inferir estados. También permite búsquedas por producto, empresa o RUC en el propio formulario. El código se adapta a la instrucción de DIGESA de omitir su última letra. No se usa una API privada. No se almacenan consultas ni resultados de registros en el feed público.

La descarga automatizada desde este entorno recibió HTTP 403 de Cloudflare tanto para la portada, los PDF y robots.txt. No se intentó evadirlo. La navegación interactiva al formulario sí funcionó. Un fallo del servidor se presenta como estado desconocido, no como registro inexistente. TLS se conserva. La búsqueda requiere conexión.

## Comunicados revisados

El índice oficial es https://www.digesa.minsa.gob.pe/noticias/comunicados.asp . Los resúmenes factuales, registros y lotes de `data-input/shield/reviewed.json` se contrastaron con los originales enlazados desde ese índice mediante consulta interactiva y lectura de PDF:

- 09-2026: Timonel/Lybre, 16/09/2026. Todos los lotes y presentaciones de las aguas indicadas. Registro P0652824N/NAINYY.
- 02-2026: Alula, 23/01/2026. Se conserva la lista de lotes, pero se exige comprobar la combinación de producto, presentación y lote en la tabla original de dos páginas. No se atribuye cada lote a todos los productos.
- 01-2026: NAN Supreme Pro 2, 06/01/2026. Solo lata de 800 g, lote 52840742F2.
- 11-2025: ByHeart, fecha del documento **21/11/2025**. El índice lo presenta como 24/11/2025; se prioriza la fecha del PDF y se deja constancia de la diferencia. Todos los lotes de las presentaciones citadas.
- 08-2025: Guttis, 01/09/2025. Ratificación de medidas y registros identificados. No se generaliza a todos los purés ni a los ingredientes frescos.

El boletín DIGESA 029-2026 menciona una reunión para orientar sobre el **procedimiento** de levantamiento de medidas de INCO BRANDS. Eso no es un acto de levantamiento: no se cambió el estado de la alerta a «resuelta». No se afirma que las medidas de ninguno de los comunicados sigan vigentes hoy. Su fecha de revisión editorial queda separada de la del monitor.

No se inventan hashes de originales obtenidos mediante lectura interactiva; no se conserva ni redistribuye el PDF. Los paquetes publicados sí tienen SHA-256 y tamaño verificables.

## Monitor diario de noticias MINSA

`etl/update_shield.py` consulta tres primeras páginas públicas del listado de noticias de MINSA, usando el campo visible `filter[terms]` con `alerta`, `retiro` y `digesa`. Comprueba robots.txt, usa el lector HTTPS existente con límites y dos segundos entre peticiones, y no recorre paginación `sheet` ni endpoints internos. Extrae título, fecha y enlace de tarjetas. Un filtro conservador distingue noticias alimentarias de artículos de enfermedades, medicamentos o juguetes. No interpreta automáticamente el texto como una nueva alerta o un levantamiento. Las noticias quedan en una lista aparte, conservando hasta 100 entradas previas.

La cobertura es **parcial**: esas primeras páginas no equivalen a todos los comunicados de DIGESA, INDECOPI, SENASA o SANIPES. Un producto sin coincidencias no se declara seguro. Los cambios de sitio, HTTP no exitoso o estructura inválida fallan antes de publicar; conservan la consulta anterior. Los recibos URL/HTTP/SHA-256/hora UTC se escriben en logs, y los hashes de los tres índices se conservan en el paquete. Ningún reloj de revisión editorial se renueva por ejecutar el monitor.

Workflow público `cuymercado-shield.yml`: diario a las **22:15 UTC / 17:15 Lima**, manual y pruebas en cambios de código. GitHub puede retrasarlo. No usa Droplet, Cloudflare, secretos ni minutos de repositorio privado. `shield/current.json` apunta al paquete por hash. El cliente verifica tamaño, integridad, esquema, fechas, fuentes y retrocesos; conserva caché sin conexión y advierte después de 48 horas sin revisión del monitor. Una noticia nueva no necesita nueva versión iOS; nuevos resúmenes revisados requieren editar y verificar `reviewed.json` y publicar el paquete.

INDECOPI https://www.alertasdeconsumo.gob.pe/ permanece como consulta oficial complementaria: el portal es una aplicación web con flujo de autenticación para su servicio interno. No se extraen credenciales, no se usa ese servicio ni se automatiza la inscripción a notificaciones. No se contactó a ninguna entidad.
