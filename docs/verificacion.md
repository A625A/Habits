# Verificación de la Fase 1

Fecha local: 25 de octubre de 2026, America/Guatemala.

## Entorno y evidencia

- Python 3.14.6, PostgreSQL 17.11, Flask 3.1.3, psycopg 3.3.6.
- `python -m pytest`: **20 passed**, usando PostgreSQL real. Sin SQLite ni mocks de BD.
- `python -m mypy`: sin errores, 13 archivos de aplicación.
- `python -m ruff check .`: sin hallazgos; `ruff format --check .`: formato válido.
- `git diff --check`: sin errores de espacios.
- `flask --app app db-init` y `db-seed`: ejecutados en la base de desarrollo vacía.
- HTTP real con Flask y Gunicorn: `/health` y `/health/db` respondieron 200 en ambos.
- Desarrollo: dos sucursales demo, cero usuarios. Sin schemas temporales de pruebas restantes.

Los ciclos TDD comprobaron primero fallas esperadas: módulo Flask inexistente,
endpoint DB 404, error de conexión sin manejar, comandos CLI ausentes, falta de
restricciones y falta de validación de configuración. Luego se implementó cada
comportamiento y se verificó su caso. Se agregaron regresiones para atomicidad
de DDL, preservación de datos, FK, unicidad y transacciones completas.

## Estado operativo

Clúster PostgreSQL dentro de `.local/postgres`, solo en `127.0.0.1:55432`, bases
`habits` y `habits_test` con cuentas separadas sin superusuario. `.env` privado
contiene credenciales aleatorias; no está versionado. Los procesos HTTP usados
en la verificación se detuvieron al finalizar; PostgreSQL queda disponible para
continuar. El README contiene comandos de arranque y parada.

## Límites

No se han probado login, autorización, reservas, ventas, inventario, reportes o
Railway porque no forman parte de esta implementación. Tampoco se valida aún
el DER general del equipo. Esta evidencia no equivale a una aplicación completa.
El repositorio de destino es `A625A/Habits`; no se hizo push, merge ni despliegue.

Revisión independiente en dos ejes: [revision-fase-1.md](revision-fase-1.md).
