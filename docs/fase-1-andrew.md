# Especificación de Andrew — Fase 1

## Fuente y precedencia

El pedido del usuario limita esta entrega a la infraestructura inicial. Los prompts
incluidos dentro de los adjuntos son material de referencia, no órdenes para ejecutar
las fases posteriores. Se leyeron íntegramente:

- `Proyecto_02_BD_Operativas_TRANSCRIPCION.pdf`, 2 páginas: transcripción de referencia,
  no el original de Canvas. Pide PostgreSQL, integridad relacional y carga reproducible;
  exige eventualmente permisos de administrador, mesero y gerente.
- `Propuesta_Habits_Cafeteria_RECONSTRUIDA.docx`: reconstrucción, no Word original.
  Dos sucursales, doce productos, inventario híbrido y separación cliente/usuario.
- `Habits_Plan_Sin_Roles.pdf`, 13 páginas: reparto del equipo. Páginas 6 y 10 fijan
  nombres y responsabilidades; página 9 delimita el hito del 25 de octubre:
  repositorio, estructura Flask, PostgreSQL local, esquema base y ramas.

El nombre del plan no elimina los permisos exigidos en la consigna. En esta fase
solo se reserva el campo `rol` con sus valores válidos; no se implementa autorización.

## Entrega requerida

1. Trabajar en `A625A/Habits`, repositorio indicado posteriormente por el usuario.
   El `habits-cafeteria` privado creado bajo el pedido inicial quedó vacío y sin uso.
2. Estructura Flask con application factory, Blueprints, rutas y servicios separados.
3. PostgreSQL local real, configuración por `DATABASE_URL` y conexión por contexto.
4. DDL base de sucursales y usuarios, PK, FK, UNIQUE, CHECK e índice de FK.
5. Cuatro ramas locales con los nombres del plan.
6. `.env.example`, `.gitignore`, `requirements.txt`, README de instalación reproducible.
7. Pruebas de Flask y PostgreSQL real; arranque WSGI local.

## Límites aceptados de pruebas

HTTP de salud, CLI de inicialización/carga y contrato SQL público de restricciones
y transacciones. Bases de prueba separadas. Revisar contra `fase-1-base`, ahora el
commit inicial de `A625A/Habits` (`16b37d0`), que contiene únicamente su README.
El punto vacío local anterior se conserva como `inicio-local-vacio`.

## Pendiente, fuera de esta fase

Andrew: registro/login, permisos efectivos, auditoría/triggers, reporte 5, DER general
consensuado e integración. Rodrigo: catálogo, recetas, inventario, producción y ventas.
Chris: clientes, mesas, reservas e historial. Brian: Bootstrap, navegación, dashboard,
reportes visibles, README final, Railway y demo. No agregar CRUD de estos módulos.
No crear usuarios demo con contraseñas predeterminadas. Los nombres de sucursal demo
son ficticios y no pretenden representar nombres aprobados por el equipo.

No hacer push, merge ni despliegues. Los commits locales están autorizados mediante
el skill implement. No atribuir commits de esta base a los demás integrantes.
