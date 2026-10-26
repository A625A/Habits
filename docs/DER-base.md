# DER del core implementado

Este diagrama muestra únicamente Fase 1. Las tablas aditivas `sesiones` y `auditoria`
del 26 se describen en `integracion-26-octubre.md`. El DER general y su exportación a imagen
se completarán al integrar el modelo de Rodrigo y Chris.

```mermaid
erDiagram
    sucursales ||--o{ usuarios : "adscribe"
    sucursales {
        bigint sucursal_id PK
        varchar codigo UK
        varchar nombre
        text direccion "opcional"
        boolean activa
        timestamptz creada_en
    }
    usuarios {
        bigint usuario_id PK
        bigint sucursal_id FK
        varchar nombre
        varchar email "único mediante lower(email)"
        text password_hash
        varchar rol
        boolean activo
        timestamptz creado_en
    }
```

Fuente ejecutable: `sql/01_core.sql`. Relación obligatoria de usuario a sucursal,
sin borrado en cascada. Los detalles futuros están en `contratos.md`.
