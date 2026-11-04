\set ON_ERROR_STOP on
BEGIN;
SELECT pg_advisory_xact_lock(3088,2);

-- La instalación pertenece al esquema actual, aunque search_path incluya otros.
SELECT to_regclass(format('%I.sucursales', current_schema())) IS NULL
   AND to_regclass(format('%I.usuarios', current_schema())) IS NULL AS crear_core \gset
\if :crear_core
\ir ../01_core.sql
\endif
\ir ../01_auth.sql
\ir ../06_auditoria.sql

DO $$
DECLARE numero INTEGER;
BEGIN
    SELECT count(*) INTO numero FROM information_schema.tables
    WHERE table_schema=current_schema() AND table_name IN (
        'mesas','clientes','productos','ingredientes','receta_ingrediente','inventario_ingrediente',
        'preferencias_cliente','reservas','visitas','observaciones_cliente','lotes_ingrediente',
        'producciones','ventas','detalle_ventas');
    IF numero NOT IN (0,14) THEN
        RAISE EXCEPTION 'Esquema parcial: revisar antes de integrar; no se borraron datos';
    END IF;
    IF numero=14 AND obj_description(to_regclass(format('%I.productos',current_schema())),'pg_class') IS DISTINCT FROM 'Habits Fase 1 v1' THEN
        RAISE EXCEPTION 'Esquema distinto a la versión aprobada; no sobrescribir automáticamente';
    END IF;
END;
$$;
SELECT to_regclass(format('%I.productos', current_schema())) IS NULL AS ampliar \gset
\if :ampliar
\ir 10_catalogo.sql
\ir 20_atencion.sql
\ir 30_inventario.sql
\ir 40_ventas.sql
\ir 50_reportes.sql
\ir 60_auditoria.sql
\ir 70_acceso.sql
COMMENT ON TABLE productos IS 'Habits Fase 1 v1';
\endif
\ir cargar_catalogo.sql
COMMIT;
