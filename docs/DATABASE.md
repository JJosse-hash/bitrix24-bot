# Base de Datos

PostgreSQL + PostGIS se inicializa en `docker/postgres/init.sql`.

## Tablas

- `geo_sources`: origen, licencia, atribución y URL.
- `places`: POIs, instituciones, asentamientos puntuales y referencias.
- `roads`: calles, avenidas, carreteras y caminos.
- `admin_areas`: estados, municipios, alcaldías y localidades poligonales.

## Índices

- GiST sobre `geom` para consultas espaciales.
- GIN trigram sobre `normalized_name` para fuzzy search.
- GIN JSONB sobre `tags` para categorías, programas, aliases y metadatos.

## Consultas esperadas

```sql
SELECT *
FROM places
WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :meters);
```

```sql
SELECT roads.*
FROM roads
JOIN admin_areas a ON ST_Intersects(roads.geom, a.geom)
WHERE a.level = 'municipality'
  AND a.normalized_name % :municipality
  AND roads.normalized_name % :street;
```

No se deben recorrer tablas completas para búsquedas geográficas en producción.
