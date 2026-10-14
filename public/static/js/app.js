/**
 * CALZACRM - Aplicación Frontend en Vanilla JS
 * CRM de Zapatería con Sistema de Scoring RFM, Control de Hormas y TPV Rápido
 */

let currentClienteSeleccionadoId = null;
let currentTicketItems = [];
let allVariantesCache = [];
let allClientesCache = [];
let debounceTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

function initApp() {
  switchTab('dashboard');
  cargarClientesParaSelects();
  cargarVariantesParaSelects();
}

/* ==========================================================================
   NAVEGACIÓN POR PESTAÑAS (SPA)
   ========================================================================== */

function switchTab(tabId) {
  // Desactivar todas las pestañas
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

  // Activar seleccionada
  const pane = document.getElementById(`pane-${tabId}`);
  const navBtn = document.getElementById(`nav-${tabId}`);
  if (pane) pane.classList.add('active');
  if (navBtn) navBtn.classList.add('active');

  // Actualizar títulos
  const titles = {
    dashboard: {
      title: 'Sales Dashboard',
      subtitle: 'Métricas comerciales, segmentación de clientes y alertas de stock de zapatería'
    },
    clientes: {
      title: 'Directorio de Clientes & Scoring RFM',
      subtitle: 'Fichas personalizadas, historial de compras y tallas habituales por categoría'
    },
    matching: {
      title: 'Match de Calzado & Avisos de Novedades',
      subtitle: 'Localiza al instante clientes compatibles con cualquier talla y marca recién llegada'
    },
    ventas: {
      title: 'Ventas de Mostrador & TPV',
      subtitle: 'Registro de tickets con actualización automática del scoring de fidelización'
    },
    catalogo: {
      title: 'Catálogo de Modelos & Inventario por Tallas',
      subtitle: 'Control de pares disponibles, variantes de color y alertas de reposición'
    },
    interacciones: {
      title: 'Interacciones & Atención al Cliente',
      subtitle: 'Avisos de tallas agotadas, mensajes de WhatsApp, encargos e incidencias'
    },
    reglas: {
      title: 'Baremos y Configuración de Scoring RFM',
      subtitle: 'Reglas oficiales de Recencia, Frecuencia y Monto aplicadas a la cartera'
    }
  };

  if (titles[tabId]) {
    document.getElementById('currentPageTitle').textContent = titles[tabId].title;
    document.getElementById('currentPageSubtitle').textContent = titles[tabId].subtitle;
    const breadcrumb = document.getElementById('breadcrumbCurrent');
    if (breadcrumb) breadcrumb.textContent = titles[tabId].title;
  }

  // Cargar datos de la pestaña activa
  if (tabId === 'dashboard') loadDashboard();
  if (tabId === 'clientes') cargarClientes();
  if (tabId === 'matching') ejecutarMatching();
  if (tabId === 'ventas') cargarVentas();
  if (tabId === 'catalogo') cargarCatalogo();
  if (tabId === 'interacciones') cargarInteracciones();
  if (tabId === 'reglas') cargarReglasScoring();
}

function toggleSidebar() {
  document.getElementById('mainSidebar').classList.toggle('open');
}

/* ==========================================================================
   DASHBOARD
   ========================================================================== */

async function loadDashboard() {
  try {
    const res = await fetch('/api/dashboard');
    const data = await res.json();

    // KPIs
    document.getElementById('kpiTotalClientes').textContent = data.total_clientes;
    document.getElementById('badgeTotalClientes').textContent = data.total_clientes;
    document.getElementById('kpiTotalIngresos').textContent = `${data.total_ingresos.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €`;
    document.getElementById('kpiTotalVentasCount').innerHTML = `<i class="fa-solid fa-tags"></i> ${data.total_pedidos} tickets cobrados`;
    document.getElementById('kpiTicketMedio').textContent = `${data.ticket_medio.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €`;
    document.getElementById('kpiVentasMes').textContent = `${data.ventas_mes.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €`;

    // Segmentos RFM
    renderSegmentosRFM(data.segmentos);

    // Stock Bajo
    renderStockBajo(data.stock_bajo);

    // Últimas Ventas
    renderUltimasVentas(data.ultimas_ventas);

    // Cumpleaños
    renderCumpleanos(data.cumpleanos);

  } catch (error) {
    console.error('Error al cargar dashboard:', error);
    showToast('Error al cargar datos del dashboard', 'error');
  }
}

function renderSegmentosRFM(segmentos) {
  const container = document.getElementById('rfmSegmentsContainer');
  const items = [
    {
      key: 'VIP / Cliente TOP',
      title: '👑 VIP / Cliente TOP',
      scoreText: '13 a 15 pts',
      actionText: 'Venta privada anticipada, eventos exclusivos y copa de bienvenida.',
      cssClass: 'seg-vip',
      badgeClass: 'rfm-vip'
    },
    {
      key: 'Cliente Frecuente',
      title: '⭐ Cliente Frecuente',
      scoreText: '10 a 12 pts',
      actionText: 'Avisos automatizados al recibir stock nuevo de su marca y talla preferida.',
      cssClass: 'seg-frecuente',
      badgeClass: 'rfm-frecuente'
    },
    {
      key: 'Cliente Dormido',
      title: '💤 Cliente Dormido',
      scoreText: '7 a 9 pts',
      actionText: 'Notificaciones al cambio de temporada con incentivo suave (10%).',
      cssClass: 'seg-dormido',
      badgeClass: 'rfm-dormido'
    },
    {
      key: 'En Riesgo / Ocasional',
      title: '⚠️ En Riesgo / Ocasional',
      scoreText: '3 a 6 pts',
      actionText: 'Cupón directo de descuento (15%) para incentivar su retorno.',
      cssClass: 'seg-riesgo',
      badgeClass: 'rfm-riesgo'
    }
  ];

  container.innerHTML = items.map(item => {
    const count = segmentos[item.key] || 0;
    return `
      <div class="rfm-segment-box ${item.cssClass}" onclick="filtrarClientesPorCategoria('${item.key}')">
        <div class="seg-header">
          <span class="seg-title">${item.title}</span>
          <span class="rfm-badge-pill ${item.badgeClass}">${item.scoreText}</span>
        </div>
        <div class="seg-count">${count} <span style="font-size:0.8rem; font-weight:400; color:var(--text-muted)">clientes</span></div>
        <p class="seg-action-text">${item.actionText}</p>
      </div>
    `;
  }).join('');
}

function renderStockBajo(items) {
  const container = document.getElementById('stockAlertsContainer');
  if (!items || items.length === 0) {
    container.innerHTML = '<p class="text-sm text-muted text-center py-3">¡Excelente! Todo el calzado tiene stock suficiente.</p>';
    return;
  }

  container.innerHTML = items.map(v => `
    <div class="stock-alert-item">
      <div class="stock-item-info">
        <strong>${escapeHtml(v.nombre_modelo)} (${escapeHtml(v.marca)})</strong>
        <span>Talla ${v.talla} · Color: ${escapeHtml(v.color)} · SKU: ${escapeHtml(v.sku)}</span>
      </div>
      <div>
        <span class="stock-pill">${v.stock_actual === 0 ? 'AGOTADO' : v.stock_actual + ' par(es)'}</span>
      </div>
    </div>
  `).join('');
}

function renderUltimasVentas(ventas) {
  const tbody = document.getElementById('ultimasVentasTableBody');
  if (!ventas || ventas.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No hay ventas registradas todavía.</td></tr>';
    return;
  }

  tbody.innerHTML = ventas.map(v => `
    <tr>
      <td>${formatearFechaCorta(v.fecha_venta)}</td>
      <td><strong>${escapeHtml(v.cliente_nombre)}</strong></td>
      <td><span class="rfm-badge-pill ${getRfmClass(v.categoria_cliente)}">${escapeHtml(v.categoria_cliente)}</span></td>
      <td><span class="badge-tag tag-blue">${escapeHtml(v.metodo_pago)}</span></td>
      <td><strong>${v.total.toFixed(2)} €</strong></td>
    </tr>
  `).join('');
}

function renderCumpleanos(cumples) {
  const container = document.getElementById('cumpleanosList');
  if (!cumples || cumples.length === 0) {
    container.innerHTML = '<p class="text-sm text-muted text-center py-3">No hay fechas registradas.</p>';
    return;
  }

  container.innerHTML = cumples.map(c => `
    <div class="d-flex justify-between align-center py-2" style="border-bottom: 1px solid var(--border-light)">
      <div>
        <strong>${escapeHtml(c.nombre)}</strong>
        <p class="text-xs text-muted">Cumpleaños: ${c.fecha_nacimiento || 'Pendiente'}</p>
      </div>
      <div class="d-flex align-center gap-2">
        <span class="rfm-badge-pill ${getRfmClass(c.categoria_cliente)}">${escapeHtml(c.categoria_cliente.split('/')[0].trim())}</span>
        ${c.telefono ? `
          <button class="btn btn-sm btn-outline btn-icon" onclick="enviarWhatsAppCumple('${c.telefono}', '${escapeHtml(c.nombre)}')" title="Felicitar por WhatsApp">
            <i class="fa-brands fa-whatsapp text-emerald"></i>
          </button>
        ` : ''}
      </div>
    </div>
  `).join('');
}

/* ==========================================================================
   CLIENTES Y SCORING RFM
   ========================================================================== */

function debounceFiltrarClientes() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    cargarClientes();
  }, 300);
}

function filtrarClientesPorCategoria(categoria) {
  switchTab('clientes');
  document.getElementById('filtroCategoria').value = categoria;
  cargarClientes();
}

function limpiarFiltrosClientes() {
  document.getElementById('filtroSearch').value = '';
  document.getElementById('filtroCategoria').value = '';
  document.getElementById('filtroTalla').value = '';
  document.getElementById('filtroMarca').value = '';
  cargarClientes();
}

async function cargarClientes() {
  const search = document.getElementById('filtroSearch').value;
  const categoria = document.getElementById('filtroCategoria').value;
  const talla = document.getElementById('filtroTalla').value;
  const marca = document.getElementById('filtroMarca').value;

  const url = new URL('/api/clientes', window.location.origin);
  if (search) url.searchParams.set('q', search);
  if (categoria) url.searchParams.set('categoria', categoria);
  if (talla) url.searchParams.set('talla', talla);
  if (marca) url.searchParams.set('marca', marca);

  try {
    const res = await fetch(url);
    const clientes = await res.json();

    document.getElementById('clientesCountBadge').textContent = `${clientes.length} clientes encontrados`;
    const tbody = document.getElementById('clientesTableBody');

    if (clientes.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No se encontraron clientes con los filtros aplicados.</td></tr>';
      return;
    }

    tbody.innerHTML = clientes.map(c => {
      const prefsHtml = (c.preferencias && c.preferencias.length > 0)
        ? c.preferencias.map(p => `
            <div class="mb-1">
              <span class="talla-badge">T.${escapeHtml(p.talla_habitual || '?')}</span>
              <span class="brand-badge">${escapeHtml(p.marca_favorita || 'Cualquiera')}</span>
              <span class="text-xs text-muted">(${escapeHtml(p.categoria_calzado || '')})</span>
            </div>
          `).join('')
        : '<span class="text-xs text-muted">Sin preferencias registradas</span>';

      return `
        <tr>
          <td>
            <div class="d-flex align-center gap-2">
              <div class="user-avatar-sm">${getInitials(c.nombre)}</div>
              <div>
                <strong>${escapeHtml(c.nombre)}</strong>
                <p class="text-xs text-muted">ID: #${c.id_cliente}</p>
              </div>
            </div>
          </td>
          <td>
            <div>${c.telefono ? `<i class="fa-solid fa-phone text-xs text-muted"></i> ${escapeHtml(c.telefono)}` : '-'}</div>
            <div class="text-xs text-muted">${c.email ? `<i class="fa-solid fa-envelope text-xs"></i> ${escapeHtml(c.email)}` : ''}</div>
          </td>
          <td>
            <span class="rfm-badge-pill ${getRfmClass(c.categoria_cliente)}">
              ${escapeHtml(c.categoria_cliente)}
            </span>
          </td>
          <td>
            <div class="d-flex align-center gap-2">
              <span class="score-badge ${getScoreBadgeClass(c.score_total)}">${c.score_total} pts</span>
              <span class="text-xs text-muted" title="Recencia: ${c.puntos_recencia} | Frecuencia: ${c.puntos_frecuencia} | Monto: ${c.puntos_monto}">
                (R:${c.puntos_recencia} + F:${c.puntos_frecuencia} + M:${c.puntos_monto})
              </span>
            </div>
          </td>
          <td>${prefsHtml}</td>
          <td><p class="text-xs text-muted" style="max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(c.observaciones || 'Sin notas')}</p></td>
          <td class="text-right">
            <div class="d-flex justify-end gap-1">
              <button class="btn btn-sm btn-primary" onclick="verFichaCliente(${c.id_cliente})" title="Ver ficha completa y scoring">
                <i class="fa-solid fa-eye"></i> Ficha
              </button>
              ${c.telefono ? `
                <button class="btn btn-sm btn-emerald btn-icon" onclick="abrirWhatsAppEstrategia(${c.id_cliente})" title="Enviar WhatsApp con acción sugerida">
                  <i class="fa-brands fa-whatsapp"></i>
                </button>
              ` : ''}
              <button class="btn btn-sm btn-secondary btn-icon" onclick="abrirVentaParaCliente(${c.id_cliente})" title="Nueva compra para este cliente">
                <i class="fa-solid fa-cart-shopping"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

  } catch (error) {
    console.error('Error al cargar clientes:', error);
    showToast('Error al cargar lista de clientes', 'error');
  }
}

/* ==========================================================================
   MODAL FICHA DETALLADA DE CLIENTE
   ========================================================================== */

async function verFichaCliente(id_cliente) {
  try {
    currentClienteSeleccionadoId = id_cliente;
    const res = await fetch(`/api/clientes/${id_cliente}`);
    const data = await res.json();

    if (data.error) {
      showToast(data.error, 'error');
      return;
    }

    document.getElementById('modalClienteAvatar').textContent = getInitials(data.nombre);
    document.getElementById('modalClienteNombre').textContent = data.nombre;
    const badge = document.getElementById('modalClienteBadge');
    badge.textContent = data.categoria_cliente;
    badge.className = `rfm-badge-pill ${getRfmClass(data.categoria_cliente)}`;

    // Tarjeta RFM Detallada
    document.getElementById('modalClientRfmCard').innerHTML = `
      <div class="rfm-score-breakdown-row">
        <div class="rfm-score-metric-box">
          <div class="text-xs text-muted">Recencia</div>
          <div class="metric-score-number text-accent">${data.puntos_recencia} <span style="font-size:0.9rem">/ 5</span></div>
          <div class="text-xs text-muted">${data.dias_recencia !== undefined ? data.dias_recencia + ' días' : 'Días transcurridos'}</div>
        </div>
        <div class="rfm-score-metric-box">
          <div class="text-xs text-muted">Frecuencia</div>
          <div class="metric-score-number text-purple">${data.puntos_frecuencia} <span style="font-size:0.9rem">/ 5</span></div>
          <div class="text-xs text-muted">${data.ventas ? data.ventas.length : 0} compras</div>
        </div>
        <div class="rfm-score-metric-box">
          <div class="text-xs text-muted">Monto</div>
          <div class="metric-score-number text-emerald">${data.puntos_monto} <span style="font-size:0.9rem">/ 5</span></div>
          <div class="text-xs text-muted">${data.ventas ? data.ventas.reduce((a, b) => a + b.total, 0).toFixed(2) : '0.00'} €</div>
        </div>
        <div class="rfm-score-metric-box highlight">
          <div class="text-xs text-gold font-semibold">Score Total RFM</div>
          <div class="metric-score-number text-gold">${data.score_total} <span style="font-size:0.9rem">/ 15</span></div>
          <div class="text-xs text-muted">Actualizado: ${data.ultima_actualizacion_score || 'Hoy'}</div>
        </div>
      </div>
    `;

    // Banner de Estrategia Comercial Recomendada
    const est = data.estrategia_comercial;
    document.getElementById('modalStrategyBanner').innerHTML = `
      <div>
        <h4 style="color:#fff; font-size:0.95rem; margin-bottom:4px;">
          <i class="fa-solid fa-lightbulb text-gold"></i> Estrategia Recomendada: <strong>${escapeHtml(est.estrategia)}</strong>
        </h4>
        <p class="text-xs text-muted">${escapeHtml(est.accion_sugerida)}</p>
      </div>
      <div>
        ${data.telefono ? `
          <button class="btn btn-sm btn-emerald" onclick="enviarMensajeWhatsAppPersonalizado('${data.telefono}', '${encodeURIComponent(est.plantilla_whatsapp)}')">
            <i class="fa-brands fa-whatsapp"></i> Enviar Mensaje
          </button>
        ` : '<span class="text-xs text-muted">Sin teléfono</span>'}
      </div>
    `;

    // Datos Personales
    document.getElementById('modalClienteTelefono').textContent = data.telefono || 'No registrado';
    document.getElementById('modalClienteEmail').textContent = data.email || 'No registrado';
    document.getElementById('modalClienteNacimiento').textContent = data.fecha_nacimiento || 'No registrada';
    document.getElementById('modalClienteObservaciones').textContent = data.observaciones || 'Sin observaciones de horma o calzado.';

    // Preferencias de Calzado
    const prefList = document.getElementById('modalClientePreferenciasList');
    if (data.preferencias && data.preferencias.length > 0) {
      prefList.innerHTML = data.preferencias.map(p => `
        <div class="d-flex justify-between align-center p-2 mb-2" style="background: rgba(255,255,255,0.03); border-radius: var(--radius-sm); border:1px solid var(--border-light)">
          <div>
            <span class="badge-tag tag-blue">${escapeHtml(p.categoria_calzado)}</span>
            <span class="talla-badge ml-1">Talla ${escapeHtml(p.talla_habitual)}</span>
            <span class="brand-badge">${escapeHtml(p.marca_favorita || 'Todas')}</span>
          </div>
          <button class="btn btn-sm btn-outline btn-icon" onclick="eliminarPreferencia(${p.id_preferencia})" title="Eliminar preferencia">
            <i class="fa-solid fa-trash text-rose"></i>
          </button>
        </div>
      `).join('');
    } else {
      prefList.innerHTML = '<p class="text-xs text-muted py-2">No hay tallas ni marcas registradas aún.</p>';
    }

    // Historial de Compras
    document.getElementById('modalClienteComprasCount').textContent = data.ventas ? data.ventas.length : 0;
    const comprasContainer = document.getElementById('modalClienteComprasHistory');
    if (data.ventas && data.ventas.length > 0) {
      comprasContainer.innerHTML = data.ventas.map(v => `
        <div class="card p-3 mb-2" style="background: rgba(255,255,255,0.02)">
          <div class="d-flex justify-between align-center mb-2">
            <div>
              <strong>Ticket #${v.id_venta}</strong> · <span class="text-xs text-muted">${formatearFechaHora(v.fecha_venta)}</span>
            </div>
            <div>
              <span class="badge-tag tag-emerald">${v.total.toFixed(2)} €</span>
              <span class="badge-tag tag-blue">${escapeHtml(v.metodo_pago)}</span>
            </div>
          </div>
          <div class="text-xs text-muted">
            ${v.detalles && v.detalles.length > 0 ? v.detalles.map(d => `
              <div>• ${d.cantidad}x ${escapeHtml(d.nombre_modelo)} (${escapeHtml(d.marca)}) - Talla ${d.talla}, Color ${escapeHtml(d.color)} (${d.precio_unitario.toFixed(2)} €/par)</div>
            `).join('') : 'Detalle no disponible'}
          </div>
        </div>
      `).join('');
    } else {
      comprasContainer.innerHTML = '<p class="text-sm text-muted text-center py-3">Este cliente aún no ha realizado ninguna compra.</p>';
    }

    // Historial de Interacciones
    document.getElementById('modalClienteInteraccionesCount').textContent = data.interacciones ? data.interacciones.length : 0;
    const timeline = document.getElementById('modalClienteTimeline');
    if (data.interacciones && data.interacciones.length > 0) {
      timeline.innerHTML = data.interacciones.map(i => `
        <div class="card p-2 mb-2" style="border-left: 3px solid var(--primary-light)">
          <div class="d-flex justify-between text-xs text-muted">
            <strong>${escapeHtml(i.tipo)}</strong>
            <span>${formatearFechaHora(i.fecha)}</span>
          </div>
          <p class="text-sm mt-1">${escapeHtml(i.comentarios)}</p>
        </div>
      `).join('');
    } else {
      timeline.innerHTML = '<p class="text-sm text-muted text-center py-3">No hay registros de contacto previos.</p>';
    }

    // Resetear a la primera sub-pestaña
    switchClientSubTab('info');

    // Abrir Modal
    openModal('modalClienteDetalle');

  } catch (error) {
    console.error('Error al ver ficha cliente:', error);
    showToast('Error al abrir la ficha del cliente', 'error');
  }
}

function switchClientSubTab(subTabId) {
  document.querySelectorAll('.sub-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.sub-pane').forEach(pane => pane.classList.remove('active'));

  const btn = Array.from(document.querySelectorAll('.sub-tab-btn')).find(b => b.getAttribute('onclick').includes(subTabId));
  const pane = document.getElementById(`subpane-${subTabId}`);
  if (btn) btn.classList.add('active');
  if (pane) pane.classList.add('active');
}

async function recalcularClienteScoring() {
  if (!currentClienteSeleccionadoId) return;
  try {
    const res = await fetch(`/api/clientes/${currentClienteSeleccionadoId}/recalcular-score`, { method: 'POST' });
    const data = await res.json();
    showToast(`Scoring recalculado: ${data.score_total} pts (${data.categoria_cliente})`, 'success');
    verFichaCliente(currentClienteSeleccionadoId);
    cargarClientes();
  } catch (error) {
    showToast('Error al recalcular scoring', 'error');
  }
}

async function recalcularTodosScoring() {
  try {
    showToast('Recalculando scoring de todos los clientes...', 'info');
    const res = await fetch('/api/clientes/recalcular-todos', { method: 'POST' });
    const data = await res.json();
    showToast(data.message, 'success');
    loadDashboard();
    cargarClientes();
  } catch (error) {
    showToast('Error al recalcular scoring masivo', 'error');
  }
}

/* ==========================================================================
   MATCHING INTELIGENTE DE NOVEDADES DE CALZADO
   ========================================================================== */

async function ejecutarMatching() {
  const talla = document.getElementById('matchTalla').value;
  const marca = document.getElementById('matchMarca').value;
  const categoria = document.getElementById('matchCategoria').value;

  const url = new URL('/api/matching/calzado', window.location.origin);
  if (talla) url.searchParams.set('talla', talla);
  if (marca) url.searchParams.set('marca', marca);
  if (categoria) url.searchParams.set('categoria', categoria);

  try {
    const res = await fetch(url);
    const matches = await res.json();

    document.getElementById('matchResultsCount').textContent = `${matches.length} clientes encontrados`;
    const container = document.getElementById('matchResultsGrid');

    if (matches.length === 0) {
      container.innerHTML = `
        <div class="col-span-full text-center py-5 text-muted">
          <i class="fa-solid fa-shoe-prints" style="font-size:2.5rem; opacity:0.3; margin-bottom:12px;"></i>
          <p>No se encontraron clientes con coincidencia exacta para Talla ${talla || 'Cualquiera'} y Marca ${marca || 'Cualquiera'}.</p>
          <p class="text-xs mt-1">Prueba seleccionando otra talla o borrando el filtro de marca para ampliar la búsqueda.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = matches.map(m => {
      const msgSugerido = `¡Hola ${m.nombre.split(' ')[0]}! 👞 Nos acaba de llegar una novedad a la zapatería que te va a encantar: modelo de ${escapeHtml(m.marca_favorita || marca || 'nueva colección')} en tu talla ${escapeHtml(m.talla_habitual || talla)}. Si te apetece probártelo sin compromiso, ¡te lo dejamos reservado!`;

      return `
        <div class="match-card">
          <div class="match-card-header">
            <div class="d-flex align-center gap-2">
              <div class="user-avatar-sm">${getInitials(m.nombre)}</div>
              <div>
                <strong>${escapeHtml(m.nombre)}</strong>
                <p class="text-xs text-muted">${m.telefono || 'Sin teléfono'}</p>
              </div>
            </div>
            <span class="rfm-badge-pill ${getRfmClass(m.categoria_cliente)}">${escapeHtml(m.categoria_cliente.split('/')[0].trim())}</span>
          </div>

          <div class="match-card-body">
            <p><strong>Talla Habitual:</strong> <span class="talla-badge">Talla ${escapeHtml(m.talla_habitual)}</span> (${escapeHtml(m.categoria_calzado || 'General')})</p>
            <p><strong>Marca Favorita:</strong> <span class="brand-badge">${escapeHtml(m.marca_favorita)}</span></p>
            <p><strong>Score RFM:</strong> <span class="score-badge ${getScoreBadgeClass(m.score_total)}">${m.score_total} pts</span></p>
          </div>

          <div class="d-flex justify-between align-center mt-2">
            <button class="btn btn-sm btn-outline" onclick="verFichaCliente(${m.id_cliente})">
              <i class="fa-solid fa-user"></i> Ver Ficha
            </button>
            ${m.telefono ? `
              <button class="btn btn-sm btn-emerald" onclick="enviarMensajeWhatsAppPersonalizado('${m.telefono}', '${encodeURIComponent(msgSugerido)}')">
                <i class="fa-brands fa-whatsapp"></i> Avisar por WhatsApp
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }).join('');

  } catch (error) {
    console.error('Error al ejecutar matching:', error);
  }
}

/* ==========================================================================
   VENTAS Y TPV RÁPIDO
   ========================================================================== */

async function cargarVentas() {
  try {
    const res = await fetch('/api/ventas');
    const ventas = await res.json();

    const tbody = document.getElementById('ventasTableBody');
    if (ventas.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No hay ventas registradas.</td></tr>';
      return;
    }

    tbody.innerHTML = ventas.map(v => {
      const itemsText = v.items && v.items.length > 0
        ? v.items.map(it => `${it.cantidad}x ${escapeHtml(it.nombre_modelo)} (${it.talla}/${escapeHtml(it.color)})`).join(', ')
        : 'Sin desglose';

      return `
        <tr>
          <td><strong>#${v.id_venta}</strong></td>
          <td>${formatearFechaHora(v.fecha_venta)}</td>
          <td>
            <strong>${escapeHtml(v.cliente_nombre)}</strong>
            <span class="rfm-badge-pill ${getRfmClass(v.categoria_cliente)} ml-1">${escapeHtml(v.categoria_cliente.split('/')[0].trim())}</span>
          </td>
          <td><p class="text-xs text-muted" style="max-width:280px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${itemsText}</p></td>
          <td><span class="badge-tag tag-blue">${escapeHtml(v.metodo_pago)}</span></td>
          <td><strong>${v.total.toFixed(2)} €</strong></td>
          <td class="text-right">
            <button class="btn btn-sm btn-outline btn-icon" onclick="verFichaCliente(${v.id_cliente})" title="Ver cliente de la compra">
              <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </button>
          </td>
        </tr>
      `;
    }).join('');

  } catch (error) {
    console.error('Error al cargar ventas:', error);
  }
}

async function cargarClientesParaSelects() {
  try {
    const res = await fetch('/api/clientes');
    allClientesCache = await res.json();

    const selects = ['ventaClienteSelect', 'interaccionClienteSelect'];
    selects.forEach(selId => {
      const el = document.getElementById(selId);
      if (!el) return;
      el.innerHTML = '<option value="">Selecciona cliente...</option>' + 
        allClientesCache.map(c => `<option value="${c.id_cliente}">${escapeHtml(c.nombre)} (${c.categoria_cliente} - ${c.score_total} pts)</option>`).join('');
    });
  } catch (e) {
    console.error(e);
  }
}

async function cargarVariantesParaSelects() {
  try {
    const res = await fetch('/api/variantes');
    allVariantesCache = await res.json();

    const el = document.getElementById('ventaVarianteSelect');
    if (!el) return;

    el.innerHTML = '<option value="">Selecciona modelo, color y talla...</option>' +
      allVariantesCache.map(v => `
        <option value="${v.id_variante}" data-precio="${v.precio_base}" data-stock="${v.stock_actual}">
          ${escapeHtml(v.nombre_modelo)} (${escapeHtml(v.marca)}) - Talla: ${v.talla} | Color: ${escapeHtml(v.color)} [Stock: ${v.stock_actual}] (${v.precio_base.toFixed(2)} €)
        </option>
      `).join('');
  } catch (e) {
    console.error(e);
  }
}

function onClienteSeleccionadoVenta() {
  const sel = document.getElementById('ventaClienteSelect');
  const cid = sel.value;
  const hint = document.getElementById('ventaClienteInfoHint');
  if (!cid) {
    hint.textContent = 'Selecciona un cliente para registrar la compra';
    return;
  }
  const cliente = allClientesCache.find(c => c.id_cliente == cid);
  if (cliente) {
    hint.innerHTML = `<span class="rfm-badge-pill ${getRfmClass(cliente.categoria_cliente)}">${cliente.categoria_cliente} (${cliente.score_total} pts)</span> · Tel: ${cliente.telefono || 'Sin tel.'}`;
  }
}

function actualizarPrecioVentaItem() {
  const sel = document.getElementById('ventaVarianteSelect');
  const selectedOpt = sel.options[sel.selectedIndex];
  if (!selectedOpt || !selectedOpt.value) return;

  const precio = selectedOpt.getAttribute('data-precio');
  document.getElementById('ventaPrecioUnitario').value = parseFloat(precio).toFixed(2);
}

function agregarItemTicket() {
  const sel = document.getElementById('ventaVarianteSelect');
  const opt = sel.options[sel.selectedIndex];
  if (!opt || !opt.value) {
    showToast('Selecciona un modelo y talla para agregar', 'error');
    return;
  }

  const id_variante = parseInt(opt.value);
  const stock = parseInt(opt.getAttribute('data-stock'));
  const cantidad = parseInt(document.getElementById('ventaCantidad').value) || 1;
  const precio = parseFloat(document.getElementById('ventaPrecioUnitario').value) || 0;

  if (cantidad <= 0) {
    showToast('La cantidad debe ser mayor que 0', 'error');
    return;
  }

  if (cantidad > stock) {
    showToast(`Stock insuficiente (Solo hay ${stock} pares disponibles)`, 'error');
    return;
  }

  // Buscar en cache datos de la variante
  const vData = allVariantesCache.find(v => v.id_variante === id_variante);
  if (!vData) return;

  // Añadir a items
  currentTicketItems.push({
    id_variante: id_variante,
    nombre_modelo: vData.nombre_modelo,
    marca: vData.marca,
    talla: vData.talla,
    color: vData.color,
    cantidad: cantidad,
    precio_unitario: precio,
    subtotal: cantidad * precio
  });

  renderTicketItems();
  showToast('Artículo añadido a la cesta del ticket', 'info');
}

function renderTicketItems() {
  const container = document.getElementById('ticketItemsList');
  const btnFinalizar = document.getElementById('btnFinalizarVenta');

  if (currentTicketItems.length === 0) {
    container.innerHTML = '<p class="text-sm text-muted py-2 text-center">No hay artículos añadidos todavía.</p>';
    document.getElementById('ticketTotalImporte').textContent = '0.00 €';
    btnFinalizar.disabled = true;
    return;
  }

  let total = 0;
  container.innerHTML = currentTicketItems.map((item, idx) => {
    total += item.subtotal;
    return `
      <div class="d-flex justify-between align-center py-2" style="border-bottom:1px solid var(--border-light)">
        <div>
          <strong>${item.cantidad}x ${escapeHtml(item.nombre_modelo)}</strong>
          <div class="text-xs text-muted">Talla: ${item.talla} · Color: ${escapeHtml(item.color)} (${item.precio_unitario.toFixed(2)} €/par)</div>
        </div>
        <div class="d-flex align-center gap-2">
          <strong>${item.subtotal.toFixed(2)} €</strong>
          <button type="button" class="btn btn-sm btn-outline btn-icon" onclick="eliminarItemTicket(${idx})">
            <i class="fa-solid fa-xmark text-rose"></i>
          </button>
        </div>
      </div>
    `;
  }).join('');

  document.getElementById('ticketTotalImporte').textContent = `${total.toFixed(2)} €`;
  btnFinalizar.disabled = false;
}

function eliminarItemTicket(index) {
  currentTicketItems.splice(index, 1);
  renderTicketItems();
}

function openNuevaVentaModal() {
  currentTicketItems = [];
  renderTicketItems();
  document.getElementById('formNuevaVenta').reset();
  cargarVariantesParaSelects();
  cargarClientesParaSelects();
  openModal('modalNuevaVenta');
}

function abrirVentaParaCliente(id_cliente) {
  openNuevaVentaModal();
  setTimeout(() => {
    document.getElementById('ventaClienteSelect').value = id_cliente;
    onClienteSeleccionadoVenta();
  }, 100);
}

async function guardarNuevaVenta(e) {
  e.preventDefault();
  const id_cliente = document.getElementById('ventaClienteSelect').value;
  const metodo_pago = document.getElementById('ventaMetodoPago').value;

  if (!id_cliente || currentTicketItems.length === 0) {
    showToast('Selecciona cliente y añade al menos un zapato al ticket', 'error');
    return;
  }

  try {
    const payload = {
      id_cliente: parseInt(id_cliente),
      metodo_pago: metodo_pago,
      items: currentTicketItems.map(it => ({
        id_variante: it.id_variante,
        cantidad: it.cantidad,
        precio_unitario: it.precio_unitario
      }))
    };

    const res = await fetch('/api/ventas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (data.error) {
      showToast(data.error, 'error');
      return;
    }

    closeModal('modalNuevaVenta');
    showToast(`¡Venta #${data.id_venta} registrada! Total: ${data.total} €. Nuevo Score: ${data.nuevo_score.score_total} pts (${data.nuevo_score.categoria_cliente})`, 'success');

    // Recargar datos
    loadDashboard();
    cargarVentas();
    cargarClientes();
    cargarVariantesParaSelects();

  } catch (error) {
    console.error('Error al guardar venta:', error);
    showToast('Error al registrar la venta', 'error');
  }
}

/* ==========================================================================
   CATÁLOGO Y STOCK
   ========================================================================== */

async function cargarCatalogo() {
  try {
    const res = await fetch('/api/productos');
    const productos = await res.json();

    const container = document.getElementById('productosCatalogGrid');
    if (productos.length === 0) {
      container.innerHTML = '<p class="text-muted text-center py-4">No hay modelos de calzado en catálogo.</p>';
      return;
    }

    container.innerHTML = productos.map(p => `
      <div class="product-card">
        <div class="product-card-header">
          <div>
            <span class="badge-tag tag-blue">${escapeHtml(p.marca)}</span>
            <span class="badge-tag tag-purple ml-1">${escapeHtml(p.categoria)}</span>
            <h3 class="mt-1" style="font-size:1.05rem;">${escapeHtml(p.nombre_modelo)}</h3>
          </div>
          <div class="text-right">
            <span style="font-family:var(--font-display); font-size:1.25rem; font-weight:800;">${p.precio_base.toFixed(2)} €</span>
            <div class="text-xs text-muted">Stock total: ${p.stock_total} pares</div>
          </div>
        </div>

        <div>
          <h5 class="text-xs text-muted mb-1 uppercase font-semibold">Variantes de Stock por Talla y Color:</h5>
          <table class="variants-table-mini">
            <thead>
              <tr>
                <th>Talla</th>
                <th>Color</th>
                <th>SKU</th>
                <th class="text-right">Stock</th>
              </tr>
            </thead>
            <tbody>
              ${p.variantes ? p.variantes.map(v => `
                <tr>
                  <td><span class="talla-badge">T.${v.talla}</span></td>
                  <td>${escapeHtml(v.color)}</td>
                  <td><span class="text-xs text-dim">${escapeHtml(v.sku)}</span></td>
                  <td class="text-right">
                    <span class="${v.stock_actual <= 2 ? 'stock-pill' : 'font-semibold'}">${v.stock_actual}</span>
                  </td>
                </tr>
              `).join('') : '<tr><td colspan="4">Sin variantes</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `).join('');

  } catch (error) {
    console.error('Error al cargar catálogo:', error);
  }
}

function openNuevoProductoModal() {
  document.getElementById('formNuevoProducto').reset();
  openModal('modalNuevoProducto');
}

async function guardarNuevoProducto(e) {
  e.preventDefault();
  const nombre = document.getElementById('prodNombre').value;
  const marca = document.getElementById('prodMarca').value;
  const categoria = document.getElementById('prodCategoria').value;
  const precio = parseFloat(document.getElementById('prodPrecio').value);

  const tallasStr = document.getElementById('prodTallasList').value;
  const color = document.getElementById('prodColor').value;
  const stockInit = parseInt(document.getElementById('prodStockInit').value) || 0;

  const tallas = tallasStr.split(',').map(t => t.trim()).filter(t => t);
  const variantes = tallas.map(t => ({
    talla: t,
    color: color,
    stock_actual: stockInit
  }));

  try {
    const res = await fetch('/api/productos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nombre_modelo: nombre,
        marca: marca,
        categoria: categoria,
        precio_base: precio,
        variantes: variantes
      })
    });

    const data = await res.json();
    if (data.error) {
      showToast(data.error, 'error');
      return;
    }

    closeModal('modalNuevoProducto');
    showToast('Modelo de calzado y variantes creados', 'success');
    cargarCatalogo();
    cargarVariantesParaSelects();

  } catch (error) {
    showToast('Error al crear producto', 'error');
  }
}

/* ==========================================================================
   ALTA DE NUEVO CLIENTE & PREFERENCIAS
   ========================================================================== */

function openNuevoClienteModal() {
  document.getElementById('formNuevoCliente').reset();
  openModal('modalNuevoCliente');
}

async function guardarNuevoCliente(e) {
  e.preventDefault();
  const nombre = document.getElementById('nuevoNombre').value;
  const telefono = document.getElementById('nuevoTelefono').value;
  const email = document.getElementById('nuevoEmail').value;
  const fecha_nacimiento = document.getElementById('nuevoNacimiento').value || null;
  const observaciones = document.getElementById('nuevoObservaciones').value;

  const prefCat = document.getElementById('nuevoPrefCat').value;
  const prefTalla = document.getElementById('nuevoPrefTalla').value;
  const prefMarca = document.getElementById('nuevoPrefMarca').value;

  const preferencias = [];
  if (prefTalla) {
    preferencias.push({
      categoria_calzado: prefCat,
      talla_habitual: prefTalla,
      marca_favorita: prefMarca
    });
  }

  try {
    const res = await fetch('/api/clientes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nombre,
        telefono,
        email,
        fecha_nacimiento,
        observaciones,
        preferencias
      })
    });

    const data = await res.json();
    if (data.error) {
      showToast(data.error, 'error');
      return;
    }

    closeModal('modalNuevoCliente');
    showToast('Cliente creado y scoring calculado', 'success');
    cargarClientes();
    cargarClientesParaSelects();
    loadDashboard();

  } catch (error) {
    showToast('Error al crear cliente', 'error');
  }
}

function openNuevaPreferenciaModal() {
  document.getElementById('formNuevaPreferencia').reset();
  openModal('modalNuevaPreferencia');
}

async function guardarNuevaPreferencia(e) {
  e.preventDefault();
  if (!currentClienteSeleccionadoId) return;

  const cat = document.getElementById('prefCat').value;
  const talla = document.getElementById('prefTalla').value;
  const marca = document.getElementById('prefMarca').value;

  try {
    const res = await fetch(`/api/clientes/${currentClienteSeleccionadoId}/preferencias`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        categoria_calzado: cat,
        talla_habitual: talla,
        marca_favorita: marca
      })
    });

    closeModal('modalNuevaPreferencia');
    showToast('Preferencia añadida', 'success');
    verFichaCliente(currentClienteSeleccionadoId);
    cargarClientes();

  } catch (error) {
    showToast('Error al guardar preferencia', 'error');
  }
}

async function eliminarPreferencia(id_preferencia) {
  try {
    await fetch(`/api/preferencias/${id_preferencia}`, { method: 'DELETE' });
    showToast('Preferencia eliminada', 'info');
    if (currentClienteSeleccionadoId) {
      verFichaCliente(currentClienteSeleccionadoId);
    }
    cargarClientes();
  } catch (e) {
    showToast('Error al eliminar', 'error');
  }
}

/* ==========================================================================
   INTERACCIONES
   ========================================================================== */

async function cargarInteracciones() {
  try {
    const res = await fetch('/api/interacciones');
    const interacciones = await res.json();

    const tbody = document.getElementById('interaccionesTableBody');
    if (interacciones.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No hay interacciones registradas.</td></tr>';
      return;
    }

    tbody.innerHTML = interacciones.map(i => `
      <tr>
        <td>${formatearFechaHora(i.fecha)}</td>
        <td>
          <strong>${escapeHtml(i.cliente_nombre)}</strong>
          <span class="rfm-badge-pill ${getRfmClass(i.categoria_cliente)} ml-1">${escapeHtml(i.categoria_cliente.split('/')[0].trim())}</span>
        </td>
        <td><span class="badge-tag tag-purple">${escapeHtml(i.tipo)}</span></td>
        <td>${escapeHtml(i.comentarios)}</td>
        <td class="text-right">
          <button class="btn btn-sm btn-outline btn-icon" onclick="verFichaCliente(${i.id_cliente})" title="Ver cliente">
            <i class="fa-solid fa-arrow-up-right-from-square"></i>
          </button>
        </td>
      </tr>
    `).join('');

  } catch (error) {
    console.error('Error al cargar interacciones:', error);
  }
}

function openNuevaInteraccionModal() {
  document.getElementById('formNuevaInteraccion').reset();
  cargarClientesParaSelects();
  openModal('modalNuevaInteraccion');
}

function openNuevaInteraccionClienteModal() {
  openNuevaInteraccionModal();
  setTimeout(() => {
    if (currentClienteSeleccionadoId) {
      document.getElementById('interaccionClienteSelect').value = currentClienteSeleccionadoId;
    }
  }, 100);
}

async function guardarNuevaInteraccion(e) {
  e.preventDefault();
  const id_cliente = document.getElementById('interaccionClienteSelect').value;
  const tipo = document.getElementById('interaccionTipo').value;
  const comentarios = document.getElementById('interaccionComentarios').value;

  try {
    const res = await fetch('/api/interacciones', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id_cliente: parseInt(id_cliente),
        tipo: tipo,
        comentarios: comentarios
      })
    });

    closeModal('modalNuevaInteraccion');
    showToast('Interacción registrada', 'success');
    cargarInteracciones();
    if (currentClienteSeleccionadoId) verFichaCliente(currentClienteSeleccionadoId);

  } catch (error) {
    showToast('Error al registrar interacción', 'error');
  }
}

/* ==========================================================================
   REGLAS DE SCORING RFM
   ========================================================================== */

async function cargarReglasScoring() {
  try {
    const res = await fetch('/api/scoring/reglas');
    const reglas = await res.json();

    const recencia = reglas.filter(r => r.criterio === 'RECENCIA');
    const frecuencia = reglas.filter(r => r.criterio === 'FRECUENCIA');
    const monto = reglas.filter(r => r.criterio === 'MONTO');

    const renderRules = (list, elementId) => {
      document.getElementById(elementId).innerHTML = list.map(r => `
        <tr>
          <td><strong>${r.rango_min} a ${r.rango_max >= 999999 ? '∞' : r.rango_max}</strong></td>
          <td><span class="score-badge ${getScoreBadgeClass(r.puntos_asignados * 3)}">${r.puntos_asignados} pts</span></td>
          <td>${escapeHtml(r.descripcion)}</td>
        </tr>
      `).join('');
    };

    renderRules(recencia, 'reglasRecenciaBody');
    renderRules(frecuencia, 'reglasFrecuenciaBody');
    renderRules(monto, 'reglasMontoBody');

  } catch (error) {
    console.error('Error al cargar reglas de scoring:', error);
  }
}

/* ==========================================================================
   WHATSAPP ACTIONS
   ========================================================================== */

function abrirWhatsAppEstrategia(id_cliente) {
  fetch(`/api/clientes/${id_cliente}`)
    .then(r => r.json())
    .then(data => {
      if (data.telefono && data.estrategia_comercial) {
        enviarMensajeWhatsAppPersonalizado(data.telefono, encodeURIComponent(data.estrategia_comercial.plantilla_whatsapp));
      }
    });
}

function enviarWhatsAppCumple(telefono, nombre) {
  const msg = `¡Felicidades ${nombre.split(' ')[0]}! 🎂 Te deseamos un día fantástico desde tu zapatería de confianza. Para celebrarlo, tienes un detalle y 10% de descuento en tu próximo par de zapatos durante todo tu mes de cumpleaños. ¡Te esperamos!`;
  enviarMensajeWhatsAppPersonalizado(telefono, encodeURIComponent(msg));
}

function enviarMensajeWhatsAppPersonalizado(telefono, mensajeCodificado) {
  const telLimpio = telefono.replace(/[^0-9]/g, '');
  const url = `https://api.whatsapp.com/send?phone=${telLimpio.startsWith('34') ? telLimpio : '34' + telLimpio}&text=${mensajeCodificado}`;
  window.open(url, '_blank');
}

/* ==========================================================================
   UTILIDADES & HELPERS
   ========================================================================== */

function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('open');
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

function closeModalOnBackdrop(e, id) {
  if (e.target.id === id) closeModal(id);
}

function getRfmClass(cat) {
  if (!cat) return 'rfm-riesgo';
  if (cat.includes('VIP')) return 'rfm-vip';
  if (cat.includes('Frecuente')) return 'rfm-frecuente';
  if (cat.includes('Dormido')) return 'rfm-dormido';
  return 'rfm-riesgo';
}

function getScoreBadgeClass(score) {
  if (score >= 13) return 'score-vip';
  if (score >= 10) return 'score-frecuente';
  if (score >= 7) return 'score-dormido';
  return 'score-riesgo';
}

function getInitials(name) {
  if (!name) return '??';
  const parts = name.trim().split(' ');
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

function formatearFechaCorta(fechaStr) {
  if (!fechaStr) return '-';
  try {
    const d = new Date(fechaStr.replace(' ', 'T'));
    return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: '2-digit' });
  } catch (e) {
    return fechaStr.slice(0, 10);
  }
}

function formatearFechaHora(fechaStr) {
  if (!fechaStr) return '-';
  try {
    const d = new Date(fechaStr.replace(' ', 'T'));
    return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' }) + ' ' + d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return fechaStr;
  }
}

function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icon = type === 'success' ? 'fa-circle-check text-emerald' :
               type === 'error' ? 'fa-circle-xmark text-rose' : 'fa-circle-info text-accent';

  toast.innerHTML = `
    <i class="fa-solid ${icon}"></i>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
