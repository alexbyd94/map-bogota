# GPS y rutas: bug y plan de implementación

Estado: **bug identificado, no implementado**.
Fecha: 2026-10-11.

## Síntoma

El botón "🗺 Ruta" del popup de cada pin siempre muestra el toast
`📍 Activa tu GPS primero`, incluso cuando el usuario ya interactuó con
el mapa. Y el navegador nunca pide permiso de ubicación.

## Causa raíz

Hay dos causas independientes que se combinan:

### Causa 1 — `userLocation` solo se llena al abrir el formulario

En `app/static/js/map.js`:

```javascript
let userLocation = null;

function obtenerGPS() {
    // ... llena userLocation si el navegador da permiso
}

function abrirSheet() {
    // ...
    obtenerGPS();   // ← solo se llama aquí
    // ...
}

function iniciarRuta(id, lat, lng, nombre) {
    if (!userLocation) {
        showToast('📍 Activa tu GPS primero');
        return;
    }
    // ...
}
```

`obtenerGPS()` **solo** se invoca dentro de `abrirSheet()`, que corre
cuando el usuario abre el formulario de publicación. Si el usuario:

1. Abre la app.
2. Hace click en un pin.
3. Le da a "Ruta".

…nunca pasó por `abrirSheet`, `userLocation` sigue `null`, y el botón
muestra el error. **El mensaje es engañoso**: dice "Activa tu GPS" cuando
en realidad el GPS nunca se intentó activar.

### Causa 2 — macOS no tiene permiso de localización para el navegador

En macOS, aunque el navegador tenga `localhost` como contexto seguro,
el sistema operativo tiene que permitir la localización a la aplicación
(navegador) a nivel de sistema:

**Configuración del Sistema → Privacidad y Seguridad → Localización**

Si Chrome (o el navegador usado) no está en la lista, o está desactivado,
`navigator.geolocation.getCurrentPosition` falla **silenciosamente** sin
mostrar prompt.

## Diagnóstico manual

En la consola del navegador (F12):

```javascript
navigator.geolocation.getCurrentPosition(
    pos => console.log('OK', pos.coords.latitude, pos.coords.longitude),
    err => console.log('ERROR', err.code, err.message)
);
```

Códigos de error posibles:

| Código | Significado | Causa |
|---|---|---|
| 1 | `PERMISSION_DENIED` | Usuario o SO negó el permiso |
| 2 | `POSITION_UNAVAILABLE` | El SO no tiene ubicación |
| 3 | `TIMEOUT` | No llegó en el tiempo esperado |

## Plan de implementación

### Cambio 1 — Llamar `obtenerGPS()` al arrancar la app

En `map.js`, añadir una llamada a `obtenerGPS()` cuando el mapa termina
de cargar, no solo cuando se abre el sheet:

```javascript
map.on('load', () => {
    // ... lo que ya hay
    obtenerGPS();   // ← intentar obtener ubicación al arrancar
});
```

**Resultado:** si el usuario da permiso al abrir la app, `userLocation`
ya está listo cuando hace click en un pin. El botón "Ruta" funciona.

**Nota:** esta llamada debe ser **no bloqueante** y **silenciosa**. Si el
usuario no da permiso, no debe aparecer un error en el mapa. Solo se
guarda `userLocation = null` y se sigue.

### Cambio 2 — Mejorar el mensaje de error

Si `obtenerGPS()` falla al arrancar, el botón "Ruta" debe decir algo más
útil que "Activa tu GPS primero":

```javascript
function iniciarRuta(id, lat, lng, nombre) {
    if (!userLocation) {
        showToast('📍 Necesitamos tu ubicación para calcular la ruta. ' +
                  'Revisa los permisos del navegador.');
        return;
    }
    // ...
}
```

El mensaje actual asume que el usuario sabe qué es "activar el GPS" y
dónde hacerlo. El nuevo mensaje dirige a la acción correcta.

### Cambio 3 — Pedir ubicación solo cuando sea necesaria

Una alternativa al Cambio 1: **no** pedir ubicación al arrancar, sino
cuando el usuario **hace click en "Ruta"** por primera vez:

```javascript
function iniciarRuta(id, lat, lng, nombre) {
    if (!userLocation) {
        // Pedir ubicación ahora, y cuando llegue, calcular la ruta.
        navigator.geolocation.getCurrentPosition(
            pos => {
                userLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                targetCasa = { id, lat, lng, nombre };
                calcularRuta('driving');
            },
            () => {
                showToast('❌ No pudimos obtener tu ubicación.');
            },
            { enableHighAccuracy: true, timeout: 10000 }
        );
        return;
    }
    targetCasa = { id, lat, lng, nombre };
    calcularRuta('driving');
}
```

**Ventajas:**
- El navegador solo pide permiso cuando el usuario **realmente** quiere
  la ruta. No hay prompt intrusivo al abrir la app.
- No hay llamada `obtenerGPS()` inútil si el usuario nunca pide rutas.
- El error es claro: "no pudimos obtener tu ubicación" en vez de "activa
  tu GPS primero".

**Desventajas:**
- Un poco más de código en `iniciarRuta`.
- El usuario ve el prompt de permiso justo cuando toca "Ruta", lo cual
  puede sentirse intrusivo si no entiende por qué.

**Esta opción es la recomendada.** Combina lo mejor de las dos anteriores:
no pide permiso al arrancar, y el mensaje de error es claro.

### Cambio 4 — Documentar el permiso de macOS en el README

Añadir una sección en `README.md` sobre requisitos de macOS:

```markdown
### Requisitos de GPS en macOS

Para que el botón "Ruta" funcione en `localhost`, macOS debe permitir
la localización al navegador:

1. Configuración del Sistema → Privacidad y Seguridad → Localización.
2. Activar "Servicios de localización".
3. Buscar el navegador (Chrome, Safari, Firefox) y activarlo.

Si el navegador no aparece en la lista, abrir la app en `localhost`,
hacer click en "Ruta" una vez, y el sistema debería pedir permiso.
Si no pide, verificar los permisos del navegador en el candado 🔒 de la
barra de direcciones.
```

### Cambio 5 (opcional) — Fallback a una ubicación por defecto

Si el usuario deniega el permiso, se puede ofrecer un fallback: centrar
la ruta desde el centro de Bogotá (`4.61, -74.082`) en vez de fallar:

```javascript
const BOGOTA_CENTER = { lat: 4.6100, lng: -74.0820 };

function iniciarRuta(id, lat, lng, nombre) {
    if (!userLocation) {
        // ... pedir ubicación ...
        // Si falla, usar el centro de Bogotá como origen.
    }
    // ...
}
```

**No recomendado.** La ruta desde el centro de Bogotá no tiene sentido
para el usuario. Mejor fallar con un mensaje claro.

## Decisión pendiente

Elegir entre:

- **Cambio 1** (pedir GPS al arrancar).
- **Cambio 3** (pedir GPS al hacer click en "Ruta"). **Recomendado.**

Los cambios 2 y 4 son complementarios y se pueden aplicar en cualquier
caso.

## Fuera del alcance

- **Fallback a IP-based geolocation.** Si el usuario deniega el permiso,
  usar un servicio externo (ipapi, ipinfo) para aproximar la ubicación.
  Requiere llamada a un tercero y añade latencia. Solo si se necesita.
- **Precisión de la ubicación.** Hoy se usa `enableHighAccuracy: true`.
  Puede fallar en interiores. Si molesta, cambiar a `false`.
- **Guardar la última ubicación.** Persistir `userLocation` en
  `localStorage` para no pedir permiso en cada visita. Solo si molesta
  el prompt repetido.

## Referencias

- `app/static/js/map.js` — `iniciarRuta`, `obtenerGPS`, `abrirSheet`.
- `docs/PRIMERA_ITERACION.md` — contexto de la iteración.
