# Visitas independientes de reservas y ventas

Andrew aprobó registrar cada atención efectiva de un cliente identificado como
una visita, tenga o no reserva e incluso si compra para llevar. Una visita puede
agrupar varias ventas y cuenta una sola vez para medir frecuencia. Contar reservas
incluiría personas que no asistieron; contar ventas duplicaría atenciones con más
de una compra. Por eso el modelo tendrá una entidad visitas separada; sus columnas
y restricciones quedaron aprobadas con el DER antes de implementarlas.

Andrew ratificó que una reserva origina como máximo una visita y que una visita
puede existir sin reserva. Registrar la llegada crea la visita real y completa la
reserva vinculada, conservando su bloqueo durante los noventa minutos originales.
Los reportes de frecuencia cuentan visitas, mientras que los reportes de reservas
pueden contar confirmadas y completadas, identificando qué están midiendo.
