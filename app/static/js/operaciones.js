/* Las pantallas usan las operaciones existentes; la base sigue controlando saldos y permisos. */
(() => {
  "use strict";
  const root = document.querySelector("#operation-app");
  if (!root) return;
  const $ = (id) => document.getElementById(id);
  const role = root.dataset.role;
  const managers = ["administrador", "gerente"];
  const admin = ["administrador"];
  const field = (name, label, type = "text", source = null, optional = false) => ({
    name,
    label,
    type,
    source,
    optional
  });
  const branch = () => field("sucursal_id", "Sucursal", "id", "sucursales");
  const target = (label, source) => field("_target", label, "id", source);
  const customer = () => field("cliente_id", "Cliente", "id", "clientes");
  const table = () => field("mesa_id", "Mesa", "id", "mesas", true);
  const kind = () => field("tipo", "Tipo de atención", "choice:llevar,local");
  const due = () => field("fecha_vencimiento", "Vencimiento", "date");
  const active = (name = "activo") => field(name, "Estado", "bool");
  const action = (title, path, fields, options = {}) => ({
    title,
    path,
    fields,
    method: "POST",
    ...options
  });
  const resources = {
    sucursales: ["/sucursales", "sucursales", "sucursal_id"],
    clientes: ["/clientes", "clientes", "cliente_id"],
    mesas: ["/mesas", "mesas", "mesa_id"],
    reservas: ["/reservas", "reservas", "reserva_id"],
    visitas: ["/visitas", "visitas", "visita_id"],
    productos: ["/catalogo/productos", "productos", "producto_id"],
    ingredientes: ["/catalogo/ingredientes", "ingredientes", "ingrediente_id"],
    existencias: ["/inventario/existencias", "ingredientes", "inventario_id"],
    lotes: ["/inventario/lotes", "lotes", "lote_id"],
    terminados: ["/inventario/terminados", "terminados", null],
    producciones: ["/producciones", "producciones", "produccion_id"],
    ventas: ["/ventas", "ventas", "venta_id"],
  };
  const view = (resource, title, columns, scoped = true) => ({
    resource,
    title,
    columns: columns.split(","),
    scoped
  });
  const configs = {
    clientes: {
      views: [view("clientes", "Clientes", "cliente_id,nombre,telefono,email,activo", false)],
      actions: [
        action("Registrar cliente", "/clientes", [field("nombre", "Nombre"), field("telefono", "Teléfono", "tel", null, true), field("email", "Correo", "email", null, true)]),
        action("Actualizar cliente", "/clientes/{_target}", [target("Cliente", "clientes"), field("nombre", "Nombre"), field("telefono", "Teléfono", "tel", null, true), field("email", "Correo", "email", null, true), active()], {
          method: "PATCH",
          edit: true
        }),
        action("Guardar preferencia", "/clientes/{_client}/preferencias/{_product}", [field("_client", "Cliente", "id", "clientes"), field("_product", "Producto", "id", "productos"), field("nota_preferencia", "Preferencia", "text", null, true)], {
          method: "PUT"
        }),
        action("Quitar preferencia", "/clientes/{_client}/preferencias/{_product}", [field("_client", "Cliente", "id", "clientes"), field("_product", "Producto", "id", "productos")], {
          method: "DELETE",
          help: "Se quita la preferencia actual. Las operaciones históricas se conservan."
        }),
        action("Agregar observación", "/clientes/{_client}/observaciones", [field("_client", "Cliente", "id", "clientes"), field("observacion", "Observación"), field("visita_id", "Visita relacionada (opcional)", "id", "visitas", true)]),
      ],
    },
    reservas: {
      views: [view("reservas", "Agenda", "reserva_id,sucursal_id,mesa_id,cliente_id,fecha_inicio,fecha_fin,personas,estado")],
      actions: [
        action("Crear reserva", "/reservas", [branch(), customer(), {
          ...table(),
          optional: false
        }, field("fecha_inicio", "Inicio (hora de Guatemala)", "datetime-local"), field("personas", "Personas", "integer")], {
          help: "La reserva dura 90 minutos. La base comprueba capacidad y cruces de horario."
        }),
        action("Confirmar reserva pendiente", "/reservas/{_target}/confirmar", [target("Reserva pendiente", "reservas")], {
          states: ["pendiente"]
        }),
        action("Registrar llegada", "/reservas/{_target}/llegada", [target("Reserva confirmada", "reservas")], {
          states: ["confirmada"],
          help: "Registra una visita y completa la reserva. No crees otra visita para esa misma llegada."
        }),
        action("Cancelar reserva", "/reservas/{_target}/cancelar", [target("Reserva", "reservas")], {
          states: ["pendiente", "confirmada"]
        }),
      ],
    },
    visitas: {
      views: [view("visitas", "Visitas", "visita_id,sucursal_id,cliente_id,mesa_id,tipo,atendida_en")],
      actions: [action("Atención sin reserva", "/visitas", [branch(), customer(), kind(), table()], {
        help: "Para una reserva usa Registrar llegada en Reservas. Una visita puede tener varias ventas."
      })],
    },
    mesas: {
      views: [view("mesas", "Mesas", "mesa_id,sucursal_id,numero_mesa,capacidad,activa")],
      actions: [
        action("Registrar mesa", "/mesas", [branch(), field("numero_mesa", "Número de mesa", "integer"), field("capacidad", "Capacidad", "integer")], {
          roles: managers
        }),
        action("Actualizar mesa", "/mesas/{_target}", [target("Mesa", "mesas"), field("numero_mesa", "Número de mesa", "integer"), field("capacidad", "Capacidad", "integer"), active("activa")], {
          method: "PATCH",
          edit: true,
          roles: managers
        }),
      ],
    },
    catalogo: {
      views: [view("productos", "Menú", "producto_id,codigo,nombre,categoria,precio,activo", false)],
      actions: [
        action("Actualizar producto", "/catalogo/productos/{_target}", [target("Producto", "productos"), field("nombre", "Nombre"), field("precio", "Precio (Q)", "price"), active()], {
          method: "PATCH",
          edit: true,
          roles: admin
        }),
        action("Guardar receta completa", "/catalogo/productos/{_target}/receta", [target("Producto", "productos")], {
          method: "PUT",
          roles: admin,
          lines: "ingredientes",
          help: "Carga la receta existente antes de editar. Guardar sustituye la receta completa."
        }),
      ],
    },
    ingredientes: {
      views: [view("ingredientes", "Ingredientes", "ingrediente_id,nombre,unidad,activo", false)],
      actions: [
        action("Registrar ingrediente", "/catalogo/ingredientes", [field("nombre", "Nombre"), field("unidad", "Unidad", "choice:g,ml,unidad")], {
          roles: admin
        }),
        action("Actualizar ingrediente", "/catalogo/ingredientes/{_target}", [target("Ingrediente", "ingredientes"), field("nombre", "Nombre"), field("unidad", "Unidad", "choice:g,ml,unidad"), active()], {
          method: "PATCH",
          edit: true,
          roles: admin
        }),
      ],
    },
    inventario: {
      views: [view("existencias", "Ingredientes disponibles", "inventario_id,sucursal_id,nombre,unidad,cantidad_disponible,cantidad_referencia,stock_bajo"), view("lotes", "Lotes recibidos", "lote_id,sucursal_id,ingrediente_id,cantidad_inicial,cantidad_disponible,fecha_vencimiento"), view("terminados", "Productos preparados", "sucursal_id,producto_id,cantidad_disponible")],
      alerts: true,
      actions: [
        action("Configurar ingrediente por sucursal", "/inventario/configuraciones", [branch(), field("ingrediente_id", "Ingrediente", "id", "ingredientes"), field("cantidad_referencia", "Cantidad de referencia", "decimal")]),
        action("Actualizar referencia", "/inventario/configuraciones/{_target}", [target("Inventario", "existencias"), field("cantidad_referencia", "Cantidad de referencia", "decimal")], {
          method: "PATCH",
          edit: true
        }),
        action("Recibir lote", "/inventario/recepciones", [field("inventario_id", "Inventario de la sucursal", "id", "existencias"), field("cantidad", "Cantidad recibida", "decimal"), due()], {
          help: "Un lote vencido se registra para trazabilidad, pero no aumenta el stock utilizable."
        }),
      ],
    },
    producciones: {
      views: [view("producciones", "Lotes producidos", "produccion_id,sucursal_id,producto_id,cantidad_producida,cantidad_disponible,fecha_vencimiento")],
      actions: [action("Registrar producción", "/producciones", [branch(), field("producto_id", "Pan o postre", "id", "productos"), field("cantidad", "Unidades", "integer"), due()], {
        help: "Consume los ingredientes de la receta y crea unidades para vender. Las bebidas se preparan al venderlas."
      })],
    },
    ventas: {
      views: [view("ventas", "Ventas confirmadas", "venta_id,sucursal_id,visita_id,tipo,fecha,total"), view("terminados", "Productos preparados", "sucursal_id,producto_id,cantidad_disponible")],
      actions: [action("Registrar venta", "/ventas", [branch(), kind(), field("visita_id", "Visita (opcional, para compra identificada)", "id", "visitas", true), table()], {
        lines: "productos",
        help: "Sin visita la venta es anónima. Para llevar no lleva mesa. El servidor calcula el total y descuenta las existencias al guardar."
      })],
    },
  };
  const cfg = configs[root.dataset.module];
  const actions = cfg.actions.filter(a => !a.roles || a.roles.includes(role));
  const cache = {};
  let offset = 0,
    currentAction, loading = false,
    pendingRecords = false,
    saving = false,
    recipeReady = true,
    recipeRequest = 0;
  const node = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text != null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };

  function message(text, error = false) {
    const box = $("operation-message");
    box.textContent = text;
    box.className = `alert alert-${error ? "danger" : "success"}`;
    box.hidden = false;
  }
  async function api(path, method = "GET", body) {
    const response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: {
        "X-CSRF-Token": root.dataset.csrf,
        ...(body === undefined ? {} : {
          "Content-Type": "application/json"
        })
      },
      ...(body === undefined ? {} : {
        body: JSON.stringify(body)
      })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) {
        window.location.assign("/auth/login");
        throw new Error("Tu sesión terminó. Inicia sesión de nuevo.");
      }
      throw new Error(data.error || "No se pudo completar la operación. Revisa los datos e inténtalo de nuevo.");
    }
    return data;
  }
  async function all(resource) {
    const [path, key] = resources[resource];
    let rows = [],
      start = 0;
    while (true) {
      const data = await api(`${path}?limite=200&offset=${start}`);
      rows = rows.concat(data[key]);
      if (resource === "sucursales" || data[key].length < 200) return rows;
      start += 200;
    }
  }
  async function loadChoices() {
    const needed = new Set(["sucursales", "productos", "clientes", "mesas"]);
    for (const a of actions) {
      for (const f of a.fields)
        if (f.source) needed.add(f.source);
      if (a.lines) needed.add(a.lines);
    }
    if (["inventario", "ingredientes", "catalogo"].includes(root.dataset.module)) needed.add("ingredientes");
    await Promise.all([...needed].map(async key => {
      cache[key] = await all(key);
    }));
  }

  function nameOf(key, value) {
    const mapping = {
      sucursal_id: "sucursales",
      cliente_id: "clientes",
      mesa_id: "mesas",
      producto_id: "productos",
      ingrediente_id: "ingredientes",
      inventario_id: "existencias"
    };
    const resource = mapping[key];
    const row = resource && (cache[resource] || []).find(r => String(r[resources[resource][2]]) === String(value));
    return row ? optionLabel(resource, row) : String(value ?? "—");
  }

  function optionLabel(resource, row) {
    if (resource === "mesas") return `Mesa ${row.numero_mesa} · ${nameOf("sucursal_id", row.sucursal_id)} · ${row.capacidad} personas`;
    if (resource === "sucursales") return `${row.nombre} (${row.codigo})`;
    if (resource === "existencias") return `${row.nombre} · ${nameOf("sucursal_id",row.sucursal_id)} · ${row.unidad}`;
    if (resource === "reservas") return `#${row.reserva_id} · ${nameOf("cliente_id",row.cliente_id)} · ${format("fecha_inicio",row.fecha_inicio)} · ${row.estado}`;
    if (resource === "visitas") return `#${row.visita_id} · ${nameOf("cliente_id",row.cliente_id)} · ${row.tipo} · ${format("atendida_en",row.atendida_en)}`;
    return `${row.nombre || row.codigo || "Registro"}${row.unidad ? ` (${row.unidad})` : ""}${row.activo === false ? " · inactivo" : ""}`;
  }
  const labels = {
    cliente_id: "Cliente",
    sucursal_id: "Sucursal",
    mesa_id: "Mesa",
    producto_id: "Producto",
    ingrediente_id: "Ingrediente",
    inventario_id: "Inventario",
    reserva_id: "Reserva",
    visita_id: "Visita",
    venta_id: "Venta",
    produccion_id: "Producción",
    lote_id: "Lote",
    fecha_inicio: "Inicio",
    fecha_fin: "Fin",
    atendida_en: "Atención",
    cantidad_disponible: "Disponible",
    cantidad_referencia: "Referencia",
    cantidad_inicial: "Recibido",
    cantidad_producida: "Producido",
    fecha_vencimiento: "Vencimiento",
    stock_bajo: "Stock bajo",
    precio_unitario: "Precio cobrado",
    nota_preferencia: "Preferencia",
    fecha_creacion: "Fecha",
    precio: "Precio (Q)",
    total: "Total (Q)",
    numero_mesa: "Mesa"
  };
  const label = key => labels[key] || key.replaceAll("_", " ").replace(/^./, c => c.toUpperCase());

  function format(key, value) {
    if (value == null) return "—";
    if (typeof value === "boolean") return value ? "Sí" : "No";
    if (key.endsWith("_id")) return nameOf(key, value);
    if (["fecha_inicio", "fecha_fin", "fecha", "atendida_en", "producida_en", "recibido_en", "fecha_creacion"].includes(key)) return new Date(value).toLocaleString("es-GT", {
      timeZone: "America/Guatemala"
    });
    if (["precio", "total", "precio_unitario"].includes(key)) return `Q ${Number(value).toFixed(2)}`;
    return String(value);
  }

  function renderTable(rows, columns, detailResource) {
    if (!rows.length) return node("p", "No hay registros para esta consulta.", "text-secondary");
    const wrap = node("div", null, "table-responsive");
    const table = node("table", null, "table table-hover operation-table");
    const head = node("tr");
    for (const c of columns) {
      const th = node("th", label(c));
      th.scope = "col";
      head.append(th);
    }
    if (detailResource) head.append(node("th", "Acciones"));
    const thead = node("thead");
    thead.append(head);
    table.append(thead);
    const tbody = node("tbody");
    for (const row of rows) {
      const tr = node("tr");
      for (const c of columns) tr.append(node("td", format(c, row[c])));
      if (detailResource) {
        const td = node("td");
        const b = node("button", detailResource === "productos" ? "Ver receta" : detailResource === "clientes" ? "Ver historial" : "Ver detalle", "btn btn-sm btn-outline-primary");
        b.type = "button";
        b.addEventListener("click", () => showDetail(detailResource, row).catch(e => message(e.message, true)));
        td.append(b);
        tr.append(td);
      }
      tbody.append(tr);
    }
    table.append(tbody);
    wrap.append(table);
    return wrap;
  }
  async function showDetail(resource, row) {
    const id = row[resources[resource][2]];
    const panel = $("detail-content");
    panel.replaceChildren();
    $("detail-panel").hidden = false;
    $("detail-title").textContent = resource === "clientes" ? `Historial · ${row.nombre}` : resource === "productos" ? `Receta · ${row.nombre}` : `Detalle de venta #${id}`;
    const sections = resource === "clientes" ? [
      ["Reservas", "/clientes/" + id + "/historial", "reservas", ["reserva_id", "fecha_inicio", "estado", "sucursal_id"]],
      ["Visitas", "/clientes/" + id + "/historial", "visitas", ["visita_id", "atendida_en", "tipo", "sucursal_id"]],
      ["Compras", "/clientes/" + id + "/historial", "compras", ["venta_id", "fecha", "total"]],
      ["Preferencias", "/clientes/" + id + "/preferencias", "preferencias", ["producto_id", "nota_preferencia"]],
      ["Observaciones", "/clientes/" + id + "/observaciones", "observaciones", ["observacion", "fecha_creacion", "visita_id"]],
    ] : resource === "productos" ? [
      ["Ingredientes", `/catalogo/productos/${id}/receta`, "ingredientes", ["nombre", "cantidad", "unidad"]]
    ] : [
      ["Productos", `/ventas/${id}`, "lineas", ["nombre", "cantidad", "precio_unitario"]]
    ];
    for (const [title, path, key, columns] of sections) {
      const section = node("section", null, "mb-4");
      section.append(node("h3", title, "h5"));
      panel.append(section);
      let start = 0;
      const more = node("button", "Cargar más", "btn btn-sm btn-outline-primary");
      more.type = "button";
      const load = async () => {
        more.disabled = true;
        try {
          const result = await api(`${path}?limite=50&offset=${start}`);
          section.insertBefore(renderTable(result[key], columns), more);
          if (key === "observaciones") {
            for (const observation of result[key]) {
              if (role !== "administrador" && String(observation.usuario_id) !== root.dataset.user) continue;
              const editor = node("details", null, "mb-3");
              editor.append(node("summary", `Editar observación #${observation.observacion_id}`));
              const form = node("form", null, "mt-2");
              const lab = node("label", "Observación", "form-label");
              const input = node("textarea", null, "form-control");
              input.id = `observation-${observation.observacion_id}`;
              input.required = true;
              input.value = observation.observacion;
              lab.htmlFor = input.id;
              const save = node("button", "Guardar observación", "btn btn-primary btn-sm mt-2");
              save.type = "submit";
              form.append(lab, input, save);
              form.addEventListener("submit", async event => {
                event.preventDefault();
                save.disabled = true;
                try {
                  await api(`/clientes/${id}/observaciones/${observation.observacion_id}`, "PATCH", {
                    observacion: input.value
                  });
                  message("Observación guardada.");
                  await showDetail(resource, row);
                } catch (e) {
                  message(e.message, true);
                } finally {
                  save.disabled = false;
                }
              });
              editor.append(form);
              section.insertBefore(editor, more);
            }
          }
          start += 50;
          more.hidden = result[key].length < 50 || resource !== "clientes";
        } finally {
          more.disabled = false;
        }
      };
      more.addEventListener("click", () => load().catch(e => message(e.message, true)));
      section.append(more);
      await load();
    }
    $("detail-panel").scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }

  function choices(f, form) {
    let rows = cache[f.source] || [];
    const sede = form.elements.sucursal_id?.value;
    const cliente = form.elements._client?.value || form.elements.cliente_id?.value;
    const tipo = form.elements.tipo?.value;
    rows = rows.filter(row => (!sede || !row.sucursal_id || String(row.sucursal_id) === sede) && (!cliente || !row.cliente_id || String(row.cliente_id) === cliente));
    if (f.source === "visitas" && tipo) rows = rows.filter(r => r.tipo === tipo);
    if (f.name === "_target" && currentAction.states) rows = rows.filter(r => currentAction.states.includes(r.estado));
    if (root.dataset.module === "producciones" && f.source === "productos") rows = rows.filter(r => r.categoria !== "bebida" && r.activo);
    if (!currentAction.edit && f.name !== "_target") rows = rows.filter(r => r.activo !== false && r.activa !== false);
    return rows;
  }

  function fillSelect(input, f, form) {
    const previous = input.value;
    input.replaceChildren(new Option(f.optional ? "Sin seleccionar" : "Seleccionar…", ""));
    for (const row of choices(f, form)) input.add(new Option(optionLabel(f.source, row), row[resources[f.source][2]]));
    input.value = previous;
  }

  function createInput(f, form, prefix = "field-") {
    const group = node("div", null, "col-md-6");
    const id = prefix + f.name;
    const lab = node("label", f.label, "form-label");
    lab.htmlFor = id;
    let input;
    if (f.source || f.type.startsWith("choice:") || f.type === "bool") {
      input = node("select", null, "form-select");
      if (f.source) fillSelect(input, f, form);
      else
        for (const value of f.type === "bool" ? ["true", "false"] : f.type.slice(7).split(",")) input.add(new Option(value === "true" ? "Activo" : value === "false" ? "Inactivo" : value, value));
    } else {
      input = node("input", null, "form-control");
      input.type = ["integer", "price", "decimal"].includes(f.type) ? "number" : f.type;
      if (input.type === "number") {
        input.min = f.type === "integer" ? "1" : f.type === "price" ? "0.01" : "0.001";
        input.step = f.type === "integer" ? "1" : f.type === "price" ? "0.01" : "0.001";
      }
    }
    input.id = id;
    input.name = f.name;
    input.required = !f.optional;
    group.append(lab, input);
    return group;
  }

  function addLine(values = {}) {
    const row = node("div", null, "line-editor");
    row.dataset.line = "true";
    const source = currentAction.lines;
    const idKey = resources[source][2];
    const lab = node("label", source === "productos" ? "Producto" : "Ingrediente", "form-label");
    const select = node("select", null, "form-select");
    select.required = true;
    select.dataset.key = idKey;
    select.add(new Option("Seleccionar…", ""));
    for (const item of cache[source] || [])
      if (item.activo !== false || values[idKey] === item[idKey]) select.add(new Option(optionLabel(source, item), item[idKey]));
    select.value = values[idKey] || "";
    lab.append(select);
    const qlab = node("label", "Cantidad", "form-label");
    const q = node("input", null, "form-control");
    q.type = "number";
    q.required = true;
    q.min = source === "productos" ? "1" : "0.001";
    q.step = source === "productos" ? "1" : "0.001";
    q.value = values.cantidad || "1";
    q.dataset.quantity = "true";
    qlab.append(q);
    const remove = node("button", "Quitar", "btn btn-outline-danger");
    remove.type = "button";
    remove.addEventListener("click", () => row.remove());
    row.append(lab, qlab, remove);
    $("line-rows").append(row);
  }
  async function prefill() {
    const form = $("operation-form");
    const id = form.elements._target?.value;
    if (!id) return;
    if (currentAction.edit) {
      const f = currentAction.fields.find(x => x.name === "_target");
      const row = cache[f.source].find(r => String(r[resources[f.source][2]]) === id);
      for (const field of currentAction.fields)
        if (!field.name.startsWith("_")) form.elements[field.name].value = row[field.name] ?? "";
    }
    if (currentAction.lines === "ingredientes") {
      const requestId = ++recipeRequest;
      recipeReady = false;
      $("save").disabled = true;
      const result = await api(`/catalogo/productos/${id}/receta`);
      if (requestId !== recipeRequest || form.elements._target.value !== id) return;
      $("line-rows").replaceChildren();
      for (const item of result.ingredientes) addLine(item);
      if (!result.ingredientes.length) addLine();
      recipeReady = true;
      $("save").disabled = saving;
    }
  }

  function buildForm() {
    currentAction = actions[Number($("action").value)];
    const form = $("operation-form");
    $("fields").replaceChildren();
    $("lines").replaceChildren();
    $("lines").hidden = !currentAction.lines;
    $("action-help").textContent = currentAction.help || "Los cambios se guardan al completar la operación.";
    for (const f of currentAction.fields) $("fields").append(createInput(f, form));
    if (currentAction.lines) {
      const rows = node("div");
      rows.id = "line-rows";
      const add = node("button", "Agregar línea", "btn btn-outline-primary btn-sm");
      add.type = "button";
      add.addEventListener("click", () => addLine());
      $("lines").append(rows, add);
      addLine();
    }
    recipeRequest++;
    recipeReady = currentAction.lines !== "ingredientes";
    $("save").disabled = saving || !recipeReady;
    const tipo = form.elements.tipo;
    if (tipo && form.elements.mesa_id) form.elements.mesa_id.disabled = tipo.value === "llevar";
  }
  $("operation-form").addEventListener("change", event => {
    const form = event.currentTarget;
    if (["sucursal_id", "tipo", "_client", "cliente_id"].includes(event.target.name))
      for (const f of currentAction.fields)
        if (f.source && !["sucursales", "clientes"].includes(f.source)) fillSelect(form.elements[f.name], f, form);
    if (event.target.name === "tipo" && form.elements.mesa_id) {
      form.elements.mesa_id.disabled = event.target.value === "llevar";
      if (form.elements.mesa_id.disabled) form.elements.mesa_id.value = "";
    }
    if (event.target.name === "visita_id" && event.target.value) {
      const v = cache.visitas.find(r => String(r.visita_id) === event.target.value);
      if (form.elements.mesa_id) form.elements.mesa_id.value = v.mesa_id || "";
    }
    if (event.target.name === "_target") prefill().catch(e => message(e.message, true));
  });
  $("operation-form").addEventListener("submit", async event => {
    event.preventDefault();
    if ($("save").disabled || saving) return;
    saving = true;
    $("operation-fields").disabled = true;
    $("action").disabled = true;
    $("save").disabled = true;
    const form = event.currentTarget;
    try {
      const data = {};
      let path = currentAction.path;
      for (const f of currentAction.fields) {
        let value = form.elements[f.name].value;
        if (f.name.startsWith("_")) {
          path = path.replace(`{${f.name}}`, encodeURIComponent(value));
          continue;
        }
        if (!value && f.optional) {
          if ((currentAction.edit && ["email", "telefono"].includes(f.name)) || f.name === "nota_preferencia") data[f.name] = null;
          continue;
        }
        if (["integer", "id"].includes(f.type)) value = Number(value);
        else if (f.type === "bool") value = value === "true";
        else if (f.type === "datetime-local") value += ":00-06:00";
        data[f.name] = value;
      }
      if (root.dataset.module === "clientes" && ["POST", "PATCH"].includes(currentAction.method) && currentAction.path.startsWith("/clientes") && data.nombre && !data.telefono && !data.email) throw new Error("Indica teléfono o correo para el cliente.");
      if (currentAction.lines) {
        const list = [...document.querySelectorAll("[data-line]")].map(row => ({
          [row.querySelector("select").dataset.key]: Number(row.querySelector("select").value),
          cantidad: currentAction.lines === "productos" ? Number(row.querySelector("input").value) : row.querySelector("input").value
        }));
        if (!list.length) throw new Error("Agrega al menos una línea.");
        data[currentAction.lines === "productos" ? "lineas" : "ingredientes"] = list;
      }
      if (currentAction.method === "DELETE" && !window.confirm("¿Quitar esta preferencia?")) return;
      const result = await api(path, currentAction.method, Object.keys(data).length ? data : undefined);
      message(`Operación guardada.${result.total ? ` Total: Q ${Number(result.total).toFixed(2)}.` : ""}`);
      $("detail-panel").hidden = true;
      try {
        await loadChoices();
        buildForm();
        offset = 0;
        await loadRecords();
      } catch (e) {
        message("La operación se guardó, pero no se pudo actualizar la pantalla. Consulta los registros antes de repetirla.", true);
      }
    } catch (e) {
      message(e instanceof TypeError ? "No se pudo confirmar la respuesta. Consulta los registros antes de repetir la operación." : e.message, true);
    } finally {
      saving = false;
      $("operation-fields").disabled = false;
      $("action").disabled = false;
      $("save").disabled = !recipeReady;
    }
  });
  async function loadRecords() {
    if (loading) {
      pendingRecords = true;
      return;
    }
    loading = true;
    $("previous").disabled = true;
    $("next").disabled = true;
    try {
      if ($("view").value === "alertas") {
        const data = await api("/inventario/alertas?" + new URLSearchParams($("branch").value ? {
          sucursal_id: $("branch").value
        } : {}));
        const panel = $("records");
        panel.replaceChildren();
        for (const [key, rows] of Object.entries(data))
          if (Array.isArray(rows)) {
            panel.append(node("h3", label(key), "h5"), renderTable(rows, rows.length ? Object.keys(rows[0]).filter(k => !k.endsWith("_id") || ["sucursal_id", "ingrediente_id", "producto_id"].includes(k)) : []));
          } $("page-label").textContent = "Alertas completas";
        return;
      }
      const v = cfg.views[Number($("view").value)];
      const [path, key] = resources[v.resource];
      const params = new URLSearchParams({
        limite: "50",
        offset: String(offset)
      });
      if (v.scoped && $("branch").value) params.set("sucursal_id", $("branch").value);
      if (root.dataset.module === "clientes" && $("search").value.trim()) params.set("q", $("search").value.trim());
      if (root.dataset.module === "reservas" && $("date").value) params.set("fecha", $("date").value);
      const data = await api(`${path}?${params}`);
      const rows = data[key];
      $("records").replaceChildren(renderTable(rows, v.columns, ["clientes", "productos", "ventas"].includes(v.resource) ? v.resource : null));
      $("previous").disabled = offset === 0;
      $("next").disabled = rows.length < 50;
      $("page-label").textContent = `Página ${offset/50+1} · ${rows.length} registros`;
    } catch (e) {
      $("records").replaceChildren(node("p", "No se pudieron cargar los registros.", "text-danger"));
      message(e.message, true);
    } finally {
      loading = false;
      if (pendingRecords) {
        pendingRecords = false;
        await loadRecords();
      }
    }
  }
  $("filters").addEventListener("submit", e => {
    e.preventDefault();
    offset = 0;
    loadRecords();
  });
  $("view").addEventListener("change", () => {
    offset = 0;
    loadRecords();
  });
  $("previous").addEventListener("click", () => {
    offset = Math.max(0, offset - 50);
    loadRecords();
  });
  $("next").addEventListener("click", () => {
    offset += 50;
    loadRecords();
  });
  $("action").addEventListener("change", buildForm);
  async function start() {
    $("action-panel").hidden = true;
    for (const [i, v] of cfg.views.entries()) $("view").add(new Option(v.title, i));
    if (cfg.alerts) $("view").add(new Option("Alertas de existencias y vencimiento", "alertas"));
    await loadChoices();
    $("branch").add(new Option("Todas mis sucursales", ""));
    for (const row of cache.sucursales) $("branch").add(new Option(optionLabel("sucursales", row), row.sucursal_id));
    $("branch-filter").hidden = !cfg.views.some(v => v.scoped);
    $("search-filter").hidden = root.dataset.module !== "clientes";
    $("date-filter").hidden = root.dataset.module !== "reservas";
    for (const [i, a] of actions.entries()) $("action").add(new Option(a.title, i));
    if (actions.length) {
      $("action-panel").hidden = false;
      buildForm();
    }
    await loadRecords();
  }
  start().catch(e => {
    $("records").textContent = "No se pudo abrir el módulo. Recarga la página para volver a intentar.";
    message(e.message, true);
  });
})();
