# Comprobación estructural local. No abre Desktop, ejecuta DAX ni aprueba el PBIX.
[CmdletBinding()]
param(
    [string]$PowerBIBin = 'C:/Program Files/Microsoft Power BI Desktop/bin'
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$modelPath = Join-Path $root 'Habits_Analytics.SemanticModel/model.bim'
foreach ($dll in @('Microsoft.AnalysisServices.Server.Core.dll',
                   'Microsoft.AnalysisServices.Server.Tabular.dll',
                   'Microsoft.AnalysisServices.Server.Tabular.Json.dll')) {
    Add-Type -Path (Join-Path $PowerBIBin $dll)
}
$database = [Microsoft.AnalysisServices.Tabular.JsonSerializer]::DeserializeDatabase(
    [IO.File]::ReadAllText($modelPath)
)
if ($database.Model.Tables.Count -ne 2) { throw 'Se esperan detalle y calendario.' }
$detalle = $database.Model.Tables.Find('v_ventas_detalle')
$calendario = $database.Model.Tables.Find('Calendario')
if (-not $detalle -or -not $calendario) { throw 'Faltan tablas esperadas.' }
if ($detalle.Measures.Count -ne 4) { throw 'Se esperan cuatro medidas.' }
foreach ($name in @('Ingresos totales','Ventas distintas','Unidades vendidas','Ticket promedio')) {
    if (-not $detalle.Measures.Find($name)) { throw "Falta la medida $name" }
}
foreach ($name in @('detalle_id','ticket_id','producto_id','sucursal_id')) {
    if ($detalle.Columns.Find($name).DataType.ToString() -ne 'String') {
        throw "El identificador $name debe ser texto."
    }
}
if ($database.Model.Relationships.Count -ne 1) { throw 'Se espera una sola relación.' }
$relationship = $database.Model.Relationships[0]
if (-not $relationship.IsActive -or
    $relationship.FromTable.Name -ne 'v_ventas_detalle' -or
    $relationship.ToTable.Name -ne 'Calendario' -or
    $relationship.FromColumn.Name -ne 'fecha' -or
    $relationship.ToColumn.Name -ne 'Fecha' -or
    $relationship.FromCardinality.ToString() -ne 'Many' -or
    $relationship.ToCardinality.ToString() -ne 'One' -or
    $relationship.CrossFilteringBehavior.ToString() -ne 'OneDirection') {
    throw 'Revisar relación activa detalle N:1 calendario, dirección única.'
}
if ($calendario.Columns.Find('Mes año').SortByColumn.Name -ne 'Año mes') {
    throw 'Los meses no tienen orden cronológico configurado.'
}
$pages = Join-Path $root 'Habits_Analytics.Report/definition/pages'
$pageFiles = @(Get-ChildItem $pages -Filter page.json -Recurse)
if ($pageFiles.Count -ne 1) { throw 'El tablero debe tener una página.' }
$page = Get-Content $pageFiles[0].FullName -Raw -Encoding UTF8 | ConvertFrom-Json
$visuals = @(Get-ChildItem $pages -Filter visual.json -Recurse | ForEach-Object {
    Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
})
$names = @($visuals | ForEach-Object name)
foreach ($type in @('lineChart','clusteredBarChart','donutChart','treemap','scatterChart')) {
    if (@($visuals | Where-Object { $_.visual.visualType -eq $type }).Count -ne 1) {
        throw "Falta o se repite un gráfico de tipo $type"
    }
}
if (@($visuals | Where-Object { $_.visual.visualType -eq 'card' }).Count -ne 4 -or
    @($visuals | Where-Object { $_.visual.visualType -eq 'slicer' }).Count -ne 3) {
    throw 'Se esperan cuatro tarjetas y tres filtros.'
}
foreach ($v in $visuals) {
    $p = $v.position
    if ($p.x -lt 0 -or $p.y -lt 0 -or $p.x+$p.width -gt $page.width -or
        $p.y+$p.height -gt $page.height) { throw "Visual fuera de página: $($v.name)" }
    foreach ($role in $v.visual.query.queryState.PSObject.Properties) {
        foreach ($projection in $role.Value.projections) {
            $reference = @($projection.field.PSObject.Properties)[0]
            $table = $database.Model.Tables.Find($reference.Value.Expression.SourceRef.Entity)
            if (-not $table) { throw "Tabla inexistente en visual $($v.name)" }
            $target = if ($reference.Name -eq 'Measure') {
                $table.Measures.Find($reference.Value.Property)
            } else {
                $table.Columns.Find($reference.Value.Property)
            }
            if (-not $target) {
                throw "Campo inexistente en visual $($v.name): $($reference.Value.Property)"
            }
        }
    }
}
foreach ($interaction in $page.visualInteractions) {
    if ($interaction.source -notin $names -or $interaction.target -notin $names) {
        throw 'Interacción referida a un visual inexistente.'
    }
}
Write-Output 'Estructura correcta: modelo legible, campos/relación/orden válidos, 1 página, 4 tarjetas, 3 filtros y 5 tipos de gráfico.'
Write-Output 'Pendiente: ejecutar M/DAX, actualizar, revisar interacción y legibilidad en Desktop, guardar y reabrir PBIX.'
