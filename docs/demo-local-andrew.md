# Acceso demo local de Andrew

Pedido posterior a la entrega del 26: permitir usuario `admin` y contraseña `123`
sin escribir correo. La contraseña se guarda con hash scrypt. Esta excepción
explícita corresponde solo a la cuenta demo; el personal conserva su política.

No cambiar tablas compartidas ni módulos de Rodrigo, Chris o Brian. Usar un alias
de login sobre una cuenta con correo técnico reservado `admin@demo.invalid`, sin
envío de correo. Mantener el login por correo del personal.

Crear la cuenta únicamente con `flask --app app create-demo-admin`, con
`HABITS_ENV=development` y `HABITS_DEMO_LOGIN=1`. La bandera está apagada por defecto.
Ni el arranque WSGI, ni seed, ni db-upgrade crean cuentas. Producción rechaza el
comando y el acceso demo, incluso por correo técnico o con una cookie previa.
Repetir el comando no modifica cuentas existentes; una colisión incompatible
requiere intervención del operador, nunca un reseteo silencioso.

Verificar HTTP, CLI y contrato SQL en PostgreSQL real, usando los límites de pruebas
ya aceptados. Revisión contra la base fija ya aceptada `5bb3939`, incluyendo los
commits anteriores de Andrew pendientes de publicación. El usuario autoriza commit
y push de `feat/andrew-core-deploy`; no merge a main ni despliegue Railway.

## Verificación

- Ciclos TDD: comando ausente, formulario que exigía correo, sesión demo no bloqueada
  y registro de correo reservado reprodujeron fallos antes de sus implementaciones.
- Suite final: **55 pruebas aprobadas**, PostgreSQL real, 15,37 segundos.
- mypy: sin errores en 18 archivos; Ruff lint y formato correctos.
- Gunicorn temporal en loopback con la base de desarrollo: login `admin / 123`,
  sesión de administrador, acceso al registro y logout verificados por HTTP real.
  El servidor de comprobación se detuvo al terminar.
- `.env` local habilitado explícitamente y cuenta demo creada; `.env` no se versiona.
- Se conservan las dos sucursales. No hay DDL nuevo ni cambios en módulos del equipo.
