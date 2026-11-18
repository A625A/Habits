# Dashboard ejecutivo de Habits — Brian

**Estado: PBIX guardado, estructura comprobada y reapertura confirmada manualmente
por Brian.** Siguen pendientes la actualización desde PostgreSQL y la validación
de cifras e interacciones con el dataset final de Rodrigo. El PBIP es una fuente
editable complementaria. No presentar la carpeta como entrega terminada hasta
completar [VALIDACION.md](VALIDACION.md).

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

1. Abrir **`Habits_Analytics.pbix`** con Power BI Desktop. Para trabajar sobre la
   fuente editable complementaria, abrir `Habits_Analytics.pbip`; si la edición
   instalada lo requiere, habilitar proyectos de Power BI en Opciones >
   Características de versión preliminar y reiniciar.
2. En **Transformar datos > Editar parámetros**, revisar `Servidor` (incluye puerto)
   y `BaseDatos`. Los valores locales previstos son `127.0.0.1:5432` y `habits_olap`.
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
7. Guardar y comprobar el PBIX con el protocolo siguiente. La reapertura del
   archivo y la validación con datos finales son comprobaciones independientes.
   Completar ambas en VALIDACION.md antes de aprobar la entrega.
8. Facilitar a Chris la exportación mediante **Archivo > Exportar > PDF**, con los
   filtros de la presentación. Chris conserva la responsabilidad del PDF final.

Microsoft documenta el [formato PBIP y la conversión mediante Guardar como](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)
y el [conector PostgreSQL incluido en Desktop](https://learn.microsoft.com/en-us/power-query/connectors/postgresql).
No hace falta instalar Npgsql adicional ni pgAdmin.

La comprobación estructural se puede repetir desde PowerShell con:
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File olap/powerbi/comprobar_fuentes.ps1`.
La excepción de política afecta solo a ese proceso; no cambia la configuración de
Windows. Comprueba referencias, relación, meses y visuales con las bibliotecas
instaladas de Desktop. No ejecuta las consultas ni sustituye la revisión visual.

## Guardar y comprobar el PBIX en Desktop

1. Abrir **`olap/powerbi/Habits_Analytics.pbip`**, dentro de este repositorio, con
   Power BI Desktop. Si faltan los datos finales, conservar el modelo sin ventas;
   no cambiar el origen por un CSV de ejemplo ni inventar cifras para guardarlo.
2. Seleccionar **Archivo > Guardar como > Examinar**. En tipo de archivo elegir
   **Power BI (*.pbix)**, carpeta `olap/powerbi/` y nombre
   **`Habits_Analytics.pbix`**. Guardar desde Desktop; no renombrar el PBIP.
3. Cerrar ese informe, atendiendo cualquier aviso de cambios. Abrir desde el
   Explorador el archivo **`.pbix` recién guardado**, no el acceso `.pbip`.
4. Comprobar que abre sin errores y conserva una página «Resumen ejecutivo»,
   cuatro tarjetas, tres segmentadores y línea, barras, dona, treemap y dispersión.
   Sin datos, comprobar el tipo de cada gráfico seleccionándolo en Desktop.
5. En el modelo, comprobar `Calendario` y `v_ventas_detalle`, la relación activa
   1:N, las cuatro medidas y sus fórmulas, y los parámetros Servidor/BaseDatos.
   Registrar en VALIDACION.md si se comprobó directamente o por confirmación de
   Brian; no marcarlo aprobado solo porque el archivo existe.

Un PBIX guardado/reabierto sin ventas sería un avance editable. Para finalizar
faltan el ETL de Rodrigo, la actualización real desde PostgreSQL y la comparación
de métricas e interacciones con los 10,000 tickets finales. El
[PR #3](https://github.com/A625A/Habits/pull/3) permanece en borrador mientras falten
esas comprobaciones.

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
