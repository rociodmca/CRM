# Diseño de Base de Datos y Sistema de Scoring para CRM de Zapatería

## 1. Visión General
Un CRM enfocado en el sector de la zapatería requiere relacionar de forma eficiente al cliente con sus preferencias específicas de calzado (tallas por categoría, marcas de preferencia, tipo de horma), su historial de compras detallado por variante (modelo, talla, color) y un sistema de scoring automático para segmentación comercial avanzada y personalizada.

---

## 2. Modelo de Tablas y Estructura de Datos

### 2.1 Tabla: `clientes`
Almacena la información de contacto, notas de atención personalizada y la puntuación de scoring.

| Campo | Tipo de Dato | Clave | Descripción |
| :--- | :--- | :---: | :--- |
| `id_cliente` | INT / UUID | **PK** | Identificador único del cliente |
| `nombre` | VARCHAR(100) | | Nombre y apellidos |
| `telefono` | VARCHAR(20) | | Teléfono / WhatsApp para acciones directas |
| `email` | VARCHAR(100) | | Correo electrónico |
| `fecha_nacimiento` | DATE | | Para promociones y felicitaciones de cumpleaños |
| `observaciones` | TEXT | | Notas del perfil (ej. horma ancha, compra infantil) |
| `puntos_recencia` | INT | | Puntos por días desde la última compra (1 a 5) |
| `puntos_frecuencia` | INT | | Puntos por número total de compras (1 a 5) |
| `puntos_monto` | INT | | Puntos por gasto total acumulado (1 a 5) |
| `score_total` | INT | | Puntuación total RFM (suma o promedio) |
| `categoria_cliente` | VARCHAR(30) | | Etiqueta resultante (VIP, Frecuente, Dormido, En Riesgo) |
| `ultima_actualizacion_score` | DATE | | Fecha de la última evaluación de scoring |
| `fecha_creacion` | TIMESTAMP | | Fecha de alta en el sistema |

---

### 2.2 Tabla: `preferencias_cliente`
Permite registrar múltiples tallas y marcas favoritas por cliente según la categoría de calzado.

| Campo | Tipo de Dato | Clave | Descripción |
| :--- | :--- | :---: | :--- |
| `id_preferencia` | INT / UUID | **PK** | Identificador único de la preferencia |
| `id_cliente` | INT / UUID | **FK** | Relación con la tabla `clientes` |
| `categoria_calzado` | VARCHAR(50) | | Ej. Deportivo, Casual, Fiesta, Infantil |
| `talla_habitual` | VARCHAR(10) | | Número de pie habitual en esta categoría |
| `marca_favorita` | VARCHAR(50) | | Marca preferida en esta categoría |

---

### 2.3 Tabla: `productos`
Catálogo general de modelos de calzado sin especificar talla ni color.

| Campo | Tipo de Dato | Clave | Descripción |
| :--- | :--- | :---: | :--- |
| `id_producto` | INT / UUID | **PK** | Identificador único del modelo |
| `nombre_modelo` | VARCHAR(100) | | Nombre comercial del calzado |
| `marca` | VARCHAR(50) | | Fabricante o marca |
| `categoria` | VARCHAR(50) | | Clasificación (Hombre, Mujer, Infantil, Unisex) |
| `precio_base` | DECIMAL(8,2) | | Precio de venta público por defecto |

---

### 2.4 Tabla: `variantes_stock`
Desglose por combinación específica de talla y color (inventario real disponible).

| Campo | Tipo de Dato | Clave | Descripción |
| :--- | :--- | :---: | :--- |
| `id_variante` | INT / UUID | **PK** | Identificador de la variante física |
| `id_producto` | INT / UUID | **FK** | Relación con la tabla `productos` |
| `talla` | VARCHAR(10) | | Número del zapato (ej. 38, 42) |
| `color` | VARCHAR(30) | | Color específico del modelo |
| `stock_actual` | INT | | Cantidad de pares disponibles físicamente |
| `sku` | VARCHAR(50) | | Código de barras o SKU interno |

---

### 2.5 Tabla: `ventas`
Cabecera de las transacciones / tickets de compra.

| Campo | Tipo de Dato | Clave | Descripción |
| :--- | :--- | :---: | :--- |
| `id_venta` | INT / UUID | **PK** | Identificador de la transacción |
| `id_cliente` | INT / UUID | **FK** | Relación con el cliente comprador |
| `fecha_venta` | TIMESTAMP | | Día y hora de la venta |
| `total` | DECIMAL(8,2) | | Importe total pagado |
| `metodo_pago` | VARCHAR(30) | | Efectivo, Tarjeta, Bizum, etc. |

---

### 2.6 Tabla: `detalles_venta`
Líneas de detalle de cada ticket de compra.

| Campo | Tipo de Dato | Clave | Descripción |
| :--- | :--- | :---: | :--- |
| `id_detalle` | INT / UUID | **PK** | Identificador de la línea del ticket |
| `id_venta` | INT / UUID | **FK** | Relación con la tabla `ventas` |
| `id_variante` | INT / UUID | **FK** | Relación con la tabla `variantes_stock` |
| `cantidad` | INT | | Número de pares comprados |
| `precio_unitario` | DECIMAL(8,2) | | Precio real aplicado en la transacción |

---

### 2.7 Tabla: `interacciones`
Seguimiento de contactos, encargo de tallas agotadas o incidencias.

| Campo | Tipo de Dato | Clave | Descripción |
| :--- | :--- | :---: | :--- |
| `id_interaccion` | INT / UUID | **PK** | Identificador de la interacción |
| `id_cliente` | INT / UUID | **FK** | Relación con la tabla `clientes` |
| `tipo` | VARCHAR(50) | | Ej. Aviso Talla Agotada, WhatsApp, Reclamación |
| `comentarios` | TEXT | | Detalle del contacto realizado |
| `fecha` | TIMESTAMP | | Fecha y hora de la gestión |

---

### 2.8 Tabla: `reglas_scoring`
Baremo configurable para el cálculo automático de puntos.

| Campo | Tipo de Dato | Clave | Descripción |
| :--- | :--- | :---: | :--- |
| `id_regla` | INT / UUID | **PK** | Identificador de la regla |
| `criterio` | VARCHAR(50) | | Criterio evaluado (`RECENCIA`, `FRECUENCIA`, `MONTO`) |
| `rango_min` | DECIMAL(10,2) | | Valor mínimo del rango |
| `rango_max` | DECIMAL(10,2) | | Valor máximo del rango |
| `puntos_asignados` | INT | | Puntos otorgados (1 a 5) |
| `descripcion` | VARCHAR(100) | | Explicación descriptiva del nivel |

---

## 3. Modelo de Scoring RFM para Zapatería

El modelo evalúa la frecuencia de compra, la fecha de la última transacción y el importe gastado por el cliente.

### A. Recencia (Días desde la última compra)
* **5 puntos:** Últimos 90 días *(Cliente Activo)*
* **4 puntos:** De 91 a 180 días
* **3 puntos:** De 181 a 365 días *(Cambio de temporada)*
* **1 punto:** Más de 365 días *(Cliente en Riesgo)*

### B. Frecuencia (Compras totales en el último año)
* **5 puntos:** Más de 6 compras
* **4 puntos:** De 3 a 5 compras
* **2 puntos:** 2 compras
* **1 punto:** 1 compra

### C. Monto (Gasto acumulado total)
* **5 puntos:** Más de $400 / 400 €
* **4 puntos:** De $200 a $399 / 200 € a 399 €
* **2 puntos:** De $100 a $199 / 100 € a 199 €
* **1 punto:** Menos de $100 / 100 €

### D. Clasificación y Estrategia Comercial

$$\text{Score Total} = \text{puntos\_recencia} + \text{puntos\_frecuencia} + \text{puntos\_monto}$$

| Score Total | Categoría | Estrategia y Acción Comercial |
| :---: | :--- | :--- |
| **13 a 15 pts** | **VIP / Cliente TOP** | Venta privada anticipada, eventos exclusivos y atención prioritaria. |
| **10 a 12 pts** | **Cliente Frecuente** | Avisos automatizados al recibir stock nuevo de su marca y talla preferida. |
| **7 a 9 pts** | **Cliente Dormido** | Notificaciones al inicio de temporada (primavera/otoño) con incentivo suave. |
| **3 a 6 pts** | **En Riesgo / Ocasional**| Cupón directo de descuento para fomentar el retorno a la tienda. |

---

## 4. Diagrama de Relaciones Clave
* `clientes` (1) ─── (N) `preferencias_cliente`
* `clientes` (1) ─── (N) `ventas`
* `clientes` (1) ─── (N) `interacciones`
* `productos` (1) ─── (N) `variantes_stock`
* `ventas` (1) ─── (N) `detalles_venta`
* `variantes_stock` (1) ─── (N) `detalles_venta`