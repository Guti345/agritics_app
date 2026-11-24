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
- **Base de datos:** MongoDB local, colecciones con validadores `$jsonSchema` e índices
  únicos (segunda línea de defensa: toda regla falla antes, en la API, con mensaje claro en
  español)
- **Fotos** (lluvia, recibos de la Cooperativa, comprobantes): carpeta local `/fotos` del
  repo; el documento guarda la ruta
- Sin Docker en el MVP; reproducibilidad con `requirements.txt`

## Estructura del repositorio

```
agritics_app/
  Agritics_kit_visual/   # marca: logos, paleta, fuentes, íconos (assets/ para la app)
  back/                  # FastAPI
    main.py              #   app, ruta base /api/v1, Swagger en /docs
    init_db.py           #   crea colecciones con validadores $jsonSchema e índices
    datos_mongo.py       #   carga los datos simulados (un año cafetero: enero - semana 46 2026)
    app/                 #   database.py, schemas.py, routers/, reglas/
  front/                 # Streamlit: app.py, pages/, assets/, .streamlit/config.toml
  fotos/                 # imágenes subidas por la app (ruta guardada en el documento)
  .env.example           # MONGO_URI y MONGO_DB (copiar a .env)
  requirements.txt
```

## Cómo correr el MVP

Desde la raíz del repo, con un `.env` creado a partir de `.env.example`:

```bash
pip install -r requirements.txt
python back/datos_mongo.py          # crea las colecciones y deja la base con el año simulado
uvicorn back.main:app --reload      # API en http://localhost:8000, Swagger en /docs
streamlit run front/app.py          # app en http://localhost:8501
```

## Qué se decidió (memoria del planteamiento, D1-D81)

**Modelo de operación:** un registro de labor = trabajador x día x lote x labor; pago a
jornal (día a tarifa libre, admite medios jornales) o a contrato (tarifa por meta: kilos,
horas o labor completada); la recolección es una labor más. Al jornal se paga el día
completo: la medición del avance evalúa, no recorta. Semana lunes-domingo: lo de
lunes-viernes se paga el sábado; lo del fin de semana se causa y se paga la siguiente.
Una sola caja (Portugal); ingresos operativos solo café y plátano; los aportes de capital
alimentan el flujo de caja, nunca el margen. Lluvia: 1-2 lecturas al día, cada una con hora
y foto del pluviómetro; los mm del día son la suma.

**Datos (MongoDB, 15 colecciones):** catálogos (lotes, labores, trabajadores, insumos,
unidades, usuarios) y operación (labor_diaria, pool_semana, cosecha_platano, venta_platano,
venta_cafe, compra_insumo, gasto, movimiento_caja, lluvia). Identidad por referencia (IDs);
valores pactados por copia congelada (tarifa y forma de pago dentro de labor_diaria). Sin
arreglos que crecen sin límite: el historial se consulta por índice; las correcciones van a
una colección de auditoría (nada se borra). El tipo y el rendimiento del trabajador siempre
se calculan, nunca se guardan a mano.

**Reglas (todas fallan con mensaje claro antes de tocar la base):** cantidades positivas;
fecha no futura ni de semana cerrada; existencia y estado de catálogos; el trabajador debe
estar activo en el pool de la semana; stock no negativo (409); un trabajador no puede tener
dos labores abiertas a la vez; aritmética del recibo de la Cooperativa verificada al
capturar; tope de 500 mm/día de lluvia. Cuadres (jornales vs. nómina, kg cereza vs.
vendido) como alertas del tablero, no bloqueos.

**Cierre de semana (solo administrador):** resumen previo; registros cerrados e inmutables;
nómina a pagar generada; pool archivado; consolidado Excel listo para la junta.

**Roles:** mayordomo (captura en campo, pool, asignaciones; corrige mientras la semana está
abierta), administrador (todo + ventas, compras, gastos, caja, catálogos, cierre), junta
familiar (KPIs, reportes, descarga Excel), superusuario (usuarios y auditoría global).
Login obligatorio; sin login no se ve nada.

**Reportes:** R1 producción (café cereza por día; series mojado/pasilla/pergamino con doble
eje contra el factor de rendimiento; kg/ha; mapa de lotes; vista plátano aparte), R2 flujo
de caja (ingresos vs. gastos por semana + margen; detalle en formato largo filtrable por
día/semana/mes), R3 nómina lista para pagar + calendario de labores. KPIs: margen semanal,
producción por lote, ROI simple (margen acumulado / gasto acumulado) y adopción digital (%
de registros capturados el mismo día). Alertas: cuadres e insumo bajo de stock.

**Frontend:** Streamlit con la marca Agritics (paleta verde oscuro #004846 / marfil #FFF4E8,
Montserrat); pantallas por rol; formularios cortos; foto obligatoria donde aplica; errores
409/422 mostrados en español sin perder lo digitado; semana en curso siempre visible.

**Fuera del MVP:** ROI formal, offline, optimización móvil, deployment, app nativa,
multi-finca, integraciones en vivo, histórico del Excel, mejoras de decisión (PE II).

## Uso de herramientas de IA en este proyecto

| Herramienta | Para qué sirvió |
|---|---|
| Asistente conversacional (Instinct) | Análisis de los registros en papel, organización de las decisiones del planteamiento y borradores de los entregables |
| Claude Code | Apoyo en la escritura del código del backend y el frontend a partir de especificaciones |
| Swagger / documentación automática | Evidencias de las reglas y los endpoints |
| LaTeX | Documento final y presentación |

Las decisiones de negocio y la redacción final son del autor.
