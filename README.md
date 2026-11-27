# Agritics by Soagro

**"Mi finca en datos"** - Los datos de tu finca, aliados para crecer.

Sistema de información para la operación diaria de la Finca Portugal (café y plátano,
Caldas, Colombia). Digitaliza lo que hoy se lleva en papel: labores y jornales, recolección
de café y plátano, lluvia, insumos, ventas, gastos y caja; liquida la nómina de la semana y
produce los reportes de producción, flujo de caja y nómina para el administrador y la junta
familiar.

MVP del Proyecto Empresarial - Maestría en Business Analytics, Universidad del Rosario.

## Stack

- **Frontend:** Streamlit (nunca habla directo con la base; solo con la API)
- **Backend:** FastAPI, ruta base `/api/v1`, routers + DTOs Pydantic + capa de reglas de
  negocio (las reglas viven en la API, no en triggers de base)
- **Base de datos:** MongoDB, colecciones con validadores `$jsonSchema` e índices únicos
  (segunda línea de defensa: toda regla falla antes, en la API, con mensaje claro en
  español)
- **Fotos** (lluvia, recibos de la Cooperativa, comprobantes): carpeta local `/fotos` del
  repo; el documento guarda la ruta
- Sin Docker en el MVP; reproducibilidad con `requirements.txt`

## Qué hay en el repositorio

```
agritics_app/
  back/                     # API FastAPI (75 endpoints en 21 routers)
    main.py                 #   app, ruta base /api/v1, Swagger en /docs
    init_db.py              #   crea colecciones con validadores $jsonSchema e índices (idempotente)
    datos_mongo.py          #   UNA corrida deja todo: año simulado 2026 (W02-W46) y la coyuntura
                            #   de la sustentación (W47 pagada, W48 por pagar y planeada, W49 programada)
    app/                    #   database.py, routers/, schemas/, reglas/
    datos_finca.geojson     #   lotes de la finca para el mapa
  front/                    # app Streamlit por roles: mayordomo, administrador, junta, superusuario
    app.py                  #   entrada: sin iniciar sesión no se ve nada
    pages/                  #   29 pantallas (registro, programación, pool, cortes, caja, reportes R1-R3...)
    assets/                 #   marca, fuentes, íconos, fondos
  fotos/                    # imágenes subidas por la app (ruta guardada en el documento)
  evidencias_backend/       # capturas de las pruebas de los 75 endpoints (Swagger)
  evidencias_frontend/      # capturas de las pantallas de cada rol
  Agritics_Pruebas_Backend.pdf   # informe de pruebas del backend, endpoint por endpoint
  Agritics_Manual_Usuario.pdf    # manual de usuario por rol, pantalla por pantalla
  Agritics_ppt.pdf               # presentación del proyecto (se carga después)
  Agritics_kit_visual/      # marca: logos, paleta, fuentes, íconos y guía de marca
  .env.example              # MONGO_URI y MONGO_DB (copiar a .env)
  requirements.txt
```

## Cómo replicar el proyecto en cualquier computador (Windows / PowerShell)

Prerrequisitos: Python 3.10 o superior y MongoDB Community corriendo en local
(`mongodb://localhost:27017`). Sirve igual con MongoDB Atlas: basta cambiar `MONGO_URI`
en el `.env`.

```powershell
# 1. Clonar y entrar
git clone https://github.com/Guti345/agritics_app.git
cd agritics_app

# 2. Entorno virtual e instalación
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Configuración: copiar el ejemplo y poner tus valores
copy .env.example .env
#   edita .env: MONGO_URI=mongodb://localhost:27017  y  MONGO_DB=agritics

# 4. Crear la base (colecciones, validadores e índices; idempotente)
python -m back.init_db

# 5. Cargar los datos de demostración (ver la ADVERTENCIA de abajo)
python back/datos_mongo.py            # primero en seco: muestra qué haría, no toca nada
python back/datos_mongo.py --confirmar

# 6. Levantar la API (queda en http://localhost:8000, Swagger en /docs)
uvicorn back.main:app --reload

# 7. Levantar la app, en OTRA consola PowerShell con el venv activado (queda en http://localhost:8501)
streamlit run front/app.py
```

> **ADVERTENCIA:** `python back/datos_mongo.py --confirmar` **borra TODOS los datos de
> TODAS las colecciones** y vuelve a crear el mundo de demostración desde cero. Úsalo solo
> sobre una base desechable, nunca sobre datos reales.

### Entrar a la app

El seed crea un usuario por rol (la clave de demostración está en `back/datos_mongo.py`):

| Usuario | Rol | Qué ve |
| --- | --- | --- |
| `mayordomo` | Mayordomo | Registro de labores y recolección, programación, trabajadores |
| `jaime` | Administrador | Lo del mayordomo y además pagar nómina, ventas/compras/gastos, caja, catálogos, reportes R1-R3, trazabilidad y Excel |
| `junta` | Junta familiar | Reportes R1-R3 y nómina (solo lectura) |
| `antonio` | Superusuario | Todo lo anterior y además usuarios y auditoría |

## Credenciales y datos sensibles

Ninguna credencial real está en el repositorio. `.env` está en `.gitignore` y solo se
publica `.env.example` con valores de ejemplo. La clave de los usuarios de demostración la
define `back/datos_mongo.py`; cada quien puede cambiarla en su copia antes de correr el
seed.

## Evidencias y documentos

- `Agritics_Pruebas_Backend.pdf`: informe de las pruebas de los 75 endpoints (qué se
  probó, respuesta y captura de cada uno). Las capturas están en `evidencias_backend/`.
- `Agritics_Manual_Usuario.pdf`: manual de usuario organizado por rol, con cada pantalla
  explicada. Las capturas están en `evidencias_frontend/`.
- `Agritics_ppt.pdf`: presentación del proyecto en PDF (se carga después).

## Hacia dónde apunta

Agritics nace de la operación real de una finca cafetera familiar: el MVP demuestra que lo
que hoy se lleva en papel se puede digitalizar sin cambiar la forma de trabajar de quienes
están en el campo. Más allá del curso, el camino es crecer hacia modelos sostenibles de
agricultura regenerativa, con sensores IoT, diversidad de cultivos y una plataforma a la
mano del pequeño y mediano agricultor: varias fincas sobre la misma base, registro móvil
que funcione sin conexión y analítica sobre los datos acumulados para decidir mejor cada
semana.

## Matriz de uso de IA

| Etapa | Herramienta | Uso |
| --- | --- | --- |
| Alcance y diseño | Claude | Apoyo para aterrizar reglas de negocio y el modelo de datos. |
| Kit de marca | ChatGPT | Generación del kit visual (logos, paleta, íconos) a partir de la identidad definida. |
| Backend | Claude Code | Escritura y corrección de código con revisión y decisiones del equipo. |
| Frontend | Claude Code | Construcción de pantallas y estilos, verificadas en la app corriendo. |
| Datos y evidencias | Claude Code | Seed determinista y captura automática de las pruebas. |
| Documentos | Claude | Borradores del informe de pruebas y del manual, editados y aprobados por el equipo. |

Todas las decisiones de diseño, la verificación del código y la aprobación final de cada
entregable fueron del equipo.
