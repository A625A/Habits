# Andrew — autenticación, auditoría e integración del 26 de octubre

Especificación del pedido actual, posterior a Fase 1. Implementar directamente en
`feat/andrew-core-deploy`, desde `5bb3939244e53aaf6cb0e1f01b6849c9176f2ed2`.
No publicar, fusionar ni desplegar estos cambios sin nueva autorización.

## Alcance

1. Login, logout y registro del personal solo por administradores; contraseñas
   hasheadas, sesiones revocables, expiración, CSRF y cookies seguras para HTTPS.
2. Roles de administrador, gerente y mesero comprobados contra PostgreSQL en cada
   acceso autenticado, sin confiar en roles enviados por formularios o cookies.
3. Alta del primer administrador mediante CLI local interactiva, sin contraseñas
   predeterminadas ni cuentas generadas en desarrollo. Después, usar registro admin.
4. Auditoría automática INSERT/UPDATE/DELETE en sucursales y usuarios, dentro de
   la transacción original. Capturar tabla, PK, operación, fecha, actor disponible
   y campos aprobados; nunca contraseñas, hashes ni tokens. Preparar contrato para
   que los dueños conecten sus tablas posteriores.
5. Comparación SQL de sucursales con datos centrales reales. La ausencia de módulos
   de ventas/reservas significa datos no disponibles, no ventas/reservas cero.
   Dejar consulta de integración pendiente de los contratos de Rodrigo y Chris.
6. Verificar PostgreSQL real, Flask y WSGI local; Railway sigue a cargo de Brian.

## Cambios y propiedad

No modificar columnas existentes ni borrar datos. Añadir tablas de sesiones y
auditoría y triggers asociados al core. Invalidar sesiones si cambia contraseña,
rol, adscripción o estado del usuario. La actualización será explícita, atómica y
repetible; no ejecutar DDL automáticamente al iniciar Flask.

Andrew mantiene rutas/plantillas de autenticación y servicio/SQL de comparación.
El dashboard y plantillas base de Brian permanecen libres. No implementar clientes,
reservas, inventario, producción ni ventas. Conservar las dos sucursales existentes
y el catálogo previsto de doce productos, que todavía no está implementado.

## Permisos de esta entrega

| Acción | Administrador | Gerente | Mesero |
|---|---|---|---|
| Consultar su sesión y cerrarla | Sí | Sí | Sí |
| Registrar personal y asignar rol/sucursal | Sí | No | No |
| Consultar comparación de sucursales | Todas | Solo su sucursal | No |

No inferir permisos para operaciones futuras que aún no existen. Los decoradores
compartidos permitirán a sus dueños aplicar la matriz acordada al integrar módulos.

## Verificación prevista

Pruebas por HTTP, CLI y SQL público contra schemas efímeros en `habits_test`.
Los valores de prueba existen únicamente en esos schemas y se eliminan al terminar;
no son clientes, ventas, productos o credenciales de la base de desarrollo.
Revisión final independiente de estándares y de esta especificación.
