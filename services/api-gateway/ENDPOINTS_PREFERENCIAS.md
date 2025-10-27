# Test de Endpoints de Preferencias y Categorías

## 🔧 Configuración
BASE_URL="http://localhost:3000"
TOKEN="TU_TOKEN_AQUI"

## ✅ ENDPOINTS CREADOS

### 1. GET /api/auth/categories (PÚBLICO)
**Obtener todas las categorías disponibles de la BD**

```bash
curl -X GET http://localhost:3000/api/auth/categories
```

**Respuesta esperada:**
```json
{
  "success": true,
  "categories": [
    {
      "id": 1,
      "nombre": "Museos",
      "descripcion": "Museos y galerías de arte",
      "icono": "museum"
    },
    {
      "id": 2,
      "nombre": "Gastronomía",
      "descripcion": "Restaurantes y cafés",
      "icono": "restaurant"
    },
    {
      "id": 3,
      "nombre": "Lugares Históricos",
      "descripcion": "Sitios históricos y monumentos",
      "icono": "landmark"
    },
    {
      "id": 4,
      "nombre": "Entretenimiento",
      "descripcion": "Cines, teatros y entretenimiento",
      "icono": "theater"
    },
    {
      "id": 5,
      "nombre": "Monumentos",
      "descripcion": "Monumentos y esculturas",
      "icono": "monument"
    }
  ]
}
```

---

### 2. GET /api/auth/profile/preferences (PROTEGIDO)
**Obtener preferencias del usuario autenticado**

```bash
curl -X GET http://localhost:3000/api/auth/profile/preferences \
  -H "Authorization: Bearer ${TOKEN}"
```

**Respuesta esperada:**
```json
{
  "success": true,
  "preferences": [
    {
      "preferencia_id": 1,
      "categoria_id": 1,
      "categoria_nombre": "Museos",
      "categoria_descripcion": "Museos y galerías de arte",
      "categoria_icono": "museum",
      "le_gusta": true
    },
    {
      "preferencia_id": 2,
      "categoria_id": 2,
      "categoria_nombre": "Gastronomía",
      "categoria_descripcion": "Restaurantes y cafés",
      "categoria_icono": "restaurant",
      "le_gusta": true
    }
  ]
}
```

---

### 3. PUT /api/auth/profile/preferences (PROTEGIDO)
**Actualizar preferencias del usuario**

```bash
curl -X PUT http://localhost:3000/api/auth/profile/preferences \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "preferencias": [
      {
        "categoria_id": 1,
        "le_gusta": true
      },
      {
        "categoria_id": 2,
        "le_gusta": true
      },
      {
        "categoria_id": 3,
        "le_gusta": true
      }
    ]
  }'
```

**Respuesta esperada:**
```json
{
  "success": true,
  "message": "Preferences updated successfully",
  "preferences": [
    {
      "preferencia_id": 10,
      "categoria_id": 1,
      "categoria_nombre": "Museos",
      "categoria_descripcion": "Museos y galerías de arte",
      "categoria_icono": "museum",
      "le_gusta": true
    },
    {
      "preferencia_id": 11,
      "categoria_id": 2,
      "categoria_nombre": "Gastronomía",
      "categoria_descripcion": "Restaurantes y cafés",
      "categoria_icono": "restaurant",
      "le_gusta": true
    },
    {
      "preferencia_id": 12,
      "categoria_id": 3,
      "categoria_nombre": "Lugares Históricos",
      "categoria_descripcion": "Sitios históricos y monumentos",
      "categoria_icono": "landmark",
      "le_gusta": true
    }
  ]
}
```

---

## 📱 INTEGRACIÓN CON FRONTEND

### En el Login/Registro
```javascript
// Después del login exitoso, obtener categorías para mostrar en selección de preferencias
const response = await fetch('http://localhost:3000/api/auth/categories');
const data = await response.json();
const categories = data.categories;

// Mostrar categorías al usuario para que seleccione sus preferencias
// Usar categories.map() para renderizar opciones
```

### En el Perfil (Editar Preferencias)
```javascript
// 1. Obtener preferencias actuales del usuario
const token = await AsyncStorage.getItem('token');

const response = await fetch('http://localhost:3000/api/auth/profile/preferences', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const data = await response.json();
const currentPreferences = data.preferences;

// 2. Mostrar categorías con checkboxes (marcadas según preferencias actuales)
const allCategories = await fetch('http://localhost:3000/api/auth/categories');
const categoriesData = await allCategories.json();

// 3. Cuando el usuario actualice, enviar PUT
const selectedCategories = [1, 2, 3]; // IDs seleccionados por el usuario

const updateResponse = await fetch('http://localhost:3000/api/auth/profile/preferences', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    preferencias: selectedCategories.map(id => ({
      categoria_id: id,
      le_gusta: true
    }))
  })
});

const result = await updateResponse.json();
// result.preferences tendrá las preferencias actualizadas
```

---

## 🗂️ CATEGORÍAS EN LA BD

Las categorías reales en tu base de datos son:

1. **Museos** - ID: 1
2. **Gastronomía** - ID: 2
3. **Lugares Históricos** - ID: 3
4. **Entretenimiento** - ID: 4
5. **Monumentos** - ID: 5
6. **Eventos** - ID: 6 (si existe)

---

## 🔍 VERIFICACIÓN

Para verificar que los IDs de categorías sean correctos, ejecuta en la BD:

```sql
SELECT id, nombre, descripcion, icono 
FROM categorias 
ORDER BY nombre;
```

---

## 🎯 FLUJO COMPLETO

1. **Al hacer login/registro:**
   - Frontend llama `GET /api/auth/categories`
   - Muestra lista de categorías al usuario
   - Usuario selecciona sus preferencias
   - Frontend envía las preferencias seleccionadas

2. **Al editar perfil:**
   - Frontend llama `GET /api/auth/profile/preferences` para obtener actuales
   - Frontend llama `GET /api/auth/categories` para obtener todas las categorías
   - Muestra checkboxes con las categorías (marcadas según preferencias)
   - Usuario modifica selección
   - Frontend envía `PUT /api/auth/profile/preferences` con nuevas preferencias

3. **El recommendation service:**
   - Lee las preferencias de `preferencias_usuario` tabla
   - Usa solo las categorías donde `le_gusta = TRUE`
   - Aplica el bonus de +0.6 para POIs de esas categorías
   - Aplica el bonus de +1.0 para POIs imperdibles de esas categorías

---

## ⚠️ IMPORTANTE

- Las preferencias se **reemplazan completamente** al hacer PUT (no se hace merge)
- Si quieres que el usuario pueda marcar "no me gusta", incluye `le_gusta: false` en las preferencias
- Actualmente el sistema solo usa preferencias con `le_gusta: true`

---

## 🧪 PRUEBA RÁPIDA

1. Inicia el servidor: `npm start` en api-gateway
2. Obtén un token haciendo login
3. Ejecuta los curl commands de arriba reemplazando `${TOKEN}`
4. Verifica que las respuestas sean correctas
