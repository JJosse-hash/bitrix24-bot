# Despliegue en Render

## Servicio actual

El servicio fue creado manualmente en Render como Web Service.

Configuracion actual compatible:

```text
Root Directory: apps/api
Build Command: pip install -r requirements.txt
Start Command: uvicorn address_ai.api.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /api/health
```

Por eso existe un espejo en la raiz del repo: `apps/api`.

## Carpeta nueva

La carpeta principal ordenada ahora es:

```text
AgentVentas BOT/apps/api
```

El script `AgentVentas BOT/scripts/subir_a_github.sh` sincroniza esa carpeta al
espejo `apps/api` antes de subir a GitHub. Asi Render sigue funcionando aunque
el trabajo diario se haga dentro de `AgentVentas BOT`.

## Autodeploy

Render hace autodeploy cuando:

1. El repo de GitHub recibe push en `main`.
2. Auto Deploy esta activo en el servicio.
3. La app compila correctamente.

El script de subida hace:

1. Sincroniza API canonica hacia `apps/api`.
2. Corre pruebas basicas si estan disponibles.
3. Hace `git add`.
4. Hace commit.
5. Hace push a `origin main`.

## Si quieres cambiar Render a la carpeta nueva

Cuando quieras dejar de usar el espejo, cambia en Render:

```text
Root Directory: AgentVentas BOT/apps/api
```

Despues de eso se podria eliminar el espejo `apps/api`, pero no lo hagas hasta
confirmar un deploy exitoso con la nueva ruta.
