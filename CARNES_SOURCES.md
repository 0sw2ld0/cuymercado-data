# Carnes: boletín diario de aves de MIDAGRI

## Fuente

[Boletín diario de comercialización y precio de aves](https://www.gob.pe/institucion/midagri/colecciones/4-boletin-diario-de-comercializacion-y-precio-de-aves), de la DGESEP de MIDAGRI (SISAP). Cada mes tiene una página de publicación con un PDF por día hábil. Solo se leen la colección, las páginas mensuales y sus PDF de `cdn.www.gob.pe`. Las páginas `?sheet=` están prohibidas por robots.txt y nunca se solicitan. No se usa ningún servicio interno del SISAP.

## Series

Cada fila del boletín es una serie propia y no se mezcla con otras ni se convierte de unidad (todas en S/ por kg):

| Serie | Etapa | Lugar | Origen del dato |
| --- | --- | --- | --- |
| Pollo vivo | Granja | Granjas que abastecen Lima Metropolitana | MIDAGRI |
| Pollo vivo | Mayorista | Centros de distribución de Lima Metropolitana | MIDAGRI |
| Pollo eviscerado | Consumidor | Mercados minoristas de Lima Metropolitana | MIDAGRI |
| Gallina de postura (colorada), gallina reproductora, huevo rosado | Mayorista | Mercado de Productores de Santa Anita | Según el boletín |
| Jurel, bonito | Promedio | Terminales pesqueros de Villa María del Triunfo y Ventanilla | PRODUCE, publicado en el boletín |

Jurel y bonito son una serie diaria distinta de los 12 promedios por ámbito del feed `sea/` y no se combinan.

## Extracción y límites

- Se toma solo la columna del día del boletín, localizada por su posición bajo el encabezado de cada tabla. Si esa celda está vacía o tiene «-», no hay observación para ese día: no se usa el día anterior ni el promedio de 7 días. Por ejemplo, el 14/10/2026 no hubo dato de pescado.
- La fecha del texto del PDF, la del nombre del archivo y la del encabezado de cada tabla deben coincidir.
- El formato actual existe desde agosto de 2026. Los boletines anteriores, de diseño distinto, se registran como rechazados en `data-input/carnes/bulletins.json` con su motivo y no se importan. Primera fecha importada: 19/08/2026.
- El precio al consumidor se publica tal como figura cada día. La fuente puede repetir el último valor relevado, por lo que dos días iguales no implican dos mediciones.
- La sección de Arequipa no se importa.
- **Res y cerdo:** no se encontró una serie oficial diaria y verificable en soles por kg. El portal SISAP presentó un certificado TLS vencido (no se desactivó la verificación) y el INEI publica variaciones porcentuales del IPC, no precios.

## Distribución

`carnes/current.json` y `carnes/releases/<sha256>/pack.json`, con el mismo puntero y las mismas comprobaciones que los demás feeds. Cada observación conserva la URL del PDF y su SHA-256. Para la carga inicial: `python etl/update_carnes.py --months 4`. El workflow diario lee los dos últimos meses y solo descarga PDF nuevos.
