# Dashboard ejecutivo de Habits — Brian

**Estado: preparación en curso, pendiente de validación en Power BI Desktop y del
dataset final de Rodrigo.** El PBIP es una fuente editable complementaria; no
sustituye `Habits_Analytics.pbix`. No presentar esta carpeta como entrega terminada
hasta completar [VALIDACION.md](VALIDACION.md).

## Requisitos académicos y responsabilidades

Se revisaron las cuatro páginas de la guía oficial «Proyecto 03 - Implementación
OLAP», CC3088, semestre II 2026. Exige fuentes crudas, estrella en PostgreSQL,
DataMart como entrada del tablero, al menos cinco tipos de gráficos y enfoque de
negocio. También exige exportar el tablero como imagen o PDF y entregar el dump
de la base. La presentación dura como máximo 20 minutos. No hay contradicción con
el acuerdo de una página, cuatro KPIs y los cinco gráficos; esos detalles, GTQ,
10,000 tickets y las fechas son acuerdos del equipo, no cifras impuestas por la guía.

Andrew entrega estructura/vistas; Rodrigo, CSV/generador/ETL; Brian, Power BI;
Chris, diseño final, PDF y presentación. No se encontraron archivos de diseño de
Chris ni fuentes/ETL de Rodrigo al iniciar este trabajo. El diseño incluido es
provisional, sin conclusiones inventadas ni datos de Proyecto 2.

## Conexión en Windows

No hay una base remota documentada. Seguir [WINDOWS.md](WINDOWS.md) para la base
local aislada. No ejecutar instaladores SQL sobre la base operativa. Mantener
PostgreSQL encendido para actualizar; Flask y pgAdmin no son necesarios. En modo
Import se puede consultar lo ya guardado en el PBIX sin servidor, pero no actualizar.

1. Abrir `Habits_Analytics.pbip` con Power BI Desktop actualizado. Si la edición
   instalada lo requiere, habilitar proyectos de Power BI en Opciones >
   Características de versión preliminar y reiniciar.
2. En **Transformar datos > Editar parámetros**, revisar `Servidor` (incluye puerto)
   y `BaseDatos`. Los valores locales previstos son `127.0.0.1:55440` y `habits_olap`.
3. En **Configuración de origen de datos > Editar permisos**, usar autenticación
   Base de datos con el lector `habits_powerbi`. Introducir la contraseña en el
   diálogo de Power BI, nunca en M, DAX, Git o capturas. No se publica al servicio.
4. Revisar/autorizar la consulta SQL nativa: solo lee `dm.v_ventas_detalle`. La
   conversión de BIGINT a texto ocurre en PostgreSQL antes de importar. Fechas
   son Date y los importes históricos son moneda fija de cuatro decimales.
   Si un importe excede el rango de moneda fija, detener la carga y revisar el
   tipo con el equipo; no redondear ni reemplazar un error silenciosamente.
5. Pulsar **Actualizar** después del ETL validado de Rodrigo. Las vistas son
   normales: no requieren `REFRESH MATERIALIZED VIEW`.
6. Confirmar el calendario marcado como tabla de fechas, relación activa
   `Calendario[Fecha]` (1) → `v_ventas_detalle[fecha]` (*), dirección única, y
   `Mes año` ordenado por `Año mes`. Desactivar fecha/hora automática.
7. Ejecutar las comprobaciones de VALIDACION.md, guardar con **Archivo > Guardar
   como > Power BI (.pbix)** en `olap/powerbi/Habits_Analytics.pbix`, cerrar y volver
   a abrir ese PBIX. Verificar medidas, filtros y cinco gráficos antes de aprobar.
8. Facilitar a Chris la exportación mediante **Archivo > Exportar > PDF**, con los
   filtros de la presentación. Chris conserva la responsabilidad del PDF final.

Microsoft documenta el [formato PBIP y la conversión mediante Guardar como](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)
y el [conector PostgreSQL incluido en Desktop](https://learn.microsoft.com/en-us/power-query/connectors/postgresql).
No hace falta instalar Npgsql adicional ni pgAdmin.

## Qué muestran los indicadores

| KPI | Para qué sirve |
|---|---|
| Ingresos totales | Cuánto se vendió en GTQ con los precios históricos del detalle. |
| Ventas distintas | Cuántos tickets compraron dentro de la selección, sin duplicar productos. |
| Unidades vendidas | Cuántas unidades de productos se vendieron. |
| Ticket promedio | Ingresos seleccionados divididos entre tickets distintos seleccionados. |

Al filtrar categoría, el ticket promedio mide solo el gasto en esa categoría por
ticket que la compró. Nunca sumar tickets por producto ni promediar promedios.
Sin ventas se muestran ingresos/unidades/tickets en 0 y ticket promedio en blanco;
no existe un promedio con denominador cero. Ver las expresiones en `medidas.dax`.

## Usar y presentar la página

Los tres segmentadores filtran fecha, sucursal y categoría. Ctrl permite selección
múltiple; el borrador del segmentador limpia su selección. Seleccionar de nuevo
un punto o hacer clic en espacio libre quita la selección de un gráfico.
Antes de comparar con SQL, quitar todas las selecciones de puntos y reproducir
exactamente los filtros. Las fechas de Power BI incluyen ambos extremos; SQL usa
inicio inclusivo y fin exclusivo (el día siguiente al último seleccionado).

| Gráfico | Lectura de negocio |
|---|---|
| Línea | Ingresos mensuales GTQ; localizar meses de mayor o menor ingreso. |
| Barras | Productos ordenados por unidades; identificar los de mayor demanda. |
| Dona | Ingresos GTQ por `local`/`llevar`; observar participación por canal. |
| Treemap | Ingresos GTQ por categoría y producto; observar composición. |
| Dispersión | Un punto por producto, unidades en X e ingresos GTQ en Y; comparar volumen y facturación. |

Diseño provisional: lienzo 1600 × 1000, cuatro tarjetas arriba, filtros debajo,
dos gráficos en la fila central y tres en la inferior; tonos café, verde y crema.
Los nombres extensos de productos requieren revisar etiquetas y tooltips en Desktop.
No se añade un sexto gráfico para conservar legibilidad; las sucursales se comparan
con el filtro y sus KPIs. Se define filtrado cruzado entre los cinco gráficos y
tarjetas, sin modificar segmentadores desde gráficos. La respuesta real de estas
interacciones y la legibilidad están pendientes de probar en Desktop.
