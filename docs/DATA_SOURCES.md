# Fuentes de Datos

Investigación realizada el 5 de septiembre de 2026.

## OpenStreetMap

Uso propuesto: calles, POIs, amenidades, estaciones, escuelas, hospitales, cementerios, parques y geometrías generales.

Fuente práctica: extractos `.osm.pbf` de Geofabrik para México o regiones. OSM está bajo ODbL; se debe atribuir a OpenStreetMap contributors y cumplir obligaciones de bases derivadas. Ver [OpenStreetMap copyright](https://www.openstreetmap.org/copyright) y [Geofabrik downloads](https://download.geofabrik.de/).

## INEGI

Uso propuesto: límites estatales/municipales/localidades y validación administrativa.

El Marco Geoestadístico de INEGI publica información vectorial nacional; la página del Marco Geoestadístico 2025 describe la división geoestadística por áreas estatales. Ver [Marco Geoestadístico INEGI](https://www.inegi.org.mx/temas/mg/) y [ficha 2025](https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551163061).

## Correos de México / SEPOMEX

Uso propuesto: códigos postales, asentamientos, municipios y estados asociados.

Correos publica el Catálogo Nacional de Códigos Postales de forma gratuita e indica que no está permitida su comercialización total o parcial. La consulta oficial muestra actualización al 4 de septiembre de 2026. Ver [consulta CP](https://www.correosdemexico.gob.mx/sslservicios/consultacp/descarga.aspx) y [datos abiertos Correos](https://www.gob.mx/correosdemexico/documentos/datos-abiertos-367834).

## Qué cubre cada fuente

- OSM: red vial y POIs, cobertura comunitaria variable.
- INEGI: divisiones administrativas confiables.
- SEPOMEX: colonias/asentamientos y CP, con restricciones de comercialización.

## Pipeline

```text
Fuente -> Downloader -> Parser -> Normalizer -> Validator -> Deduplicator -> PostGIS -> Search indexes
```

Los importadores deben guardar `source_id`, fecha de importación, licencia, atribución y versión/hash del archivo.
