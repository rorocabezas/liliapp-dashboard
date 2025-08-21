| Segmentación por Región/Comuna | Agrupar clientes por ubicación geográfica. | COUNT(pedidos) GROUP BY serviceAddress.region, serviceAddress.commune | Pedido.serviceAddress.region, Pedido.serviceAddress.commune |
| Segmentación por Antigüedad | Agrupar clientes por fecha de registro/cohorte. | COUNT(users) GROUP BY createdAt (mes/año) | User.createdAt |
| Segmentación por Ticket Promedio | Agrupar clientes por nivel de gasto. | AVG(Pedido.montoTotal) GROUP BY customerId | Pedido.montoTotal, Pedido.customerId |
# 🛠️  Implementación de Perfiles de Clientes en LiliApp (Versión Pedidos)

---

> **Este documento es una copia actualizada del documento técnico original, adaptada para que todos los KPIs, queries y dashboards apunten a la colección `pedidos` en Firestore, aprovechando su mayor riqueza y calidad de datos.**

---

# 🛠️  Implementación de Perfiles de Clientes en LiliApp

## 📌 Visión General

LiliApp está evolucionando para incluir perfiles de clientes, permitiendo a los usuarios no solo registrarse, sino también comprar servicios y gestionar su experiencia en la aplicación de manera similar a MercadoLibre. Este documento describe las mejoras necesarias para habilitar esta funcionalidad, proporcionando detalles tanto para el equipo de UX/UI como para el de desarrollo.

## 🌟 ¿Qué queremos lograr?

En esta nueva etapa, vamos a habilitar el acceso a los **clientes finales**. El objetivo es que puedan registrarse, comprar servicios, gestionar sus pedidos y calificar a los profesionales directamente desde la aplicación, transformando a LiliApp en un marketplace de servicios completo.

Para lograrlo, implementaremos una nueva estructura en nuestra base de datos y diseñaremos flujos de usuario intuitivos, enfocados en la confianza y la facilidad de uso. Si ya tenemos una excelente experiencia para los **profesionales**, ahora es el turno de crear una experiencia igual de sólida para los **clientes**.

Construir un marketplace de servicios completo donde los clientes puedan:
1.  Registrarse y gestionar su perfil.
2.  Comprar servicios de un catálogo estándar.
3.  Solicitar, recibir y aceptar presupuestos para trabajos personalizados.
4.  Gestionar y calificar sus órdenes.

## 🎨 Guía para el Equipo de UX/UI

### Pantalla de Perfil de Usuario 

...existing code...

##  💻Guía para el Equipo de Desarrollo  
### Modelo de Base de Datos en Firestore

...existing code...

## 📊 Guía para el Equipo de Data Science y BI (Versión Pedidos)

> **Todos los KPIs y queries ahora apuntan a la colección `pedidos` en Firestore.**

### 📈 Métricas de Adquisición y Crecimiento

| KPI                          | Fórmula                                                                 | Campos Requeridos                                                                 | Ejemplo Chile                          |
|------------------------------|-------------------------------------------------------------------------|----------------------------------------------------------------------------------|----------------------------------------|
| Nuevos Usuarios              | `COUNT(users) WHERE createdAt BETWEEN [fecha_inicio] AND [fecha_fin]`  | `User.createdAt`                                                                 | "2,345 registros en Septiembre"       |
| Tasa de Conversión a Primer Pedido | `(COUNT(users con ≥1 pedido) / COUNT(total usuarios)) * 100`         | `User.createdAt`, `Pedido.userId`                                             | "38% en últimos 30 días"              |
| Pedidos por Canal de Adquisición | `COUNT(pedidos) GROUP BY acquisitionInfo.source` | `Pedido.acquisitionInfo.source` | "Google: 45%, Referidos: 30%"   |
| Validación RUT               | `(COUNT(customer_profiles WHERE rutVerified=true) / COUNT(total)) * 100` | `CustomerProfile.rutVerified`                                                    | "62% de usuarios verificados"         |
| Pedidos por Región           | `COUNT(pedidos) GROUP BY region`             | `Pedido.region`                                               | "Metropolitana: 58%, Valparaíso: 22%" |
| Tasa de Onboarding |  `(COUNT(users WHERE onboardingCompleted=true) / COUNT(total)) * 100` | `User.onboardingCompleted` | "78% de usuarios nuevos completan su perfil" |

### 🛒 Métricas de Engagement y Conversión

| KPI                          | Fórmula                                                                 | Campos Requeridos                                                                 | Uso en Chile                           |
|------------------------------|-------------------------------------------------------------------------|----------------------------------------------------------------------------------|----------------------------------------|
| Tasa de Abandono de Carrito  | `(COUNT(carts abandonados) / COUNT(carts creados)) * 100`              | `Cart.status`, `Cart.updatedAt`                                                  | "Abandono promedio: 42%"              |
| Conversión por Servicio      | `(COUNT(pedidos WHERE categoria='X') / COUNT(pedidos)) * 100`                    | `Pedido.categoria`                         | "Gasfitería: 25%, Electricidad: 18%"  |
| Ticket Promedio (CLP)        | `AVG(Pedido.montoTotal) WHERE status='finalizada'`                            | `Pedido.montoTotal`, `Pedido.status`                                                    | "$58,700 CLP último trimestre"        |
| Frecuencia de Compra         | `COUNT(pedidos) / COUNT(DISTINCT Pedido.userId)`                           | `Pedido.userId`                                                               | "1.8 compras/cliente semestral"       |
| Métodos de Pago Populares | `COUNT(pedidos) GROUP BY metodoPago` | `Pedido.metodoPago` | "Mercado Pago: 68%, Webpay: 30%" |
| Pedidos con Fotos Adjuntas | `COUNT(pedidos WHERE fotosInicio IS NOT NULL OR fotosTermino IS NOT NULL)` | `Pedido.fotosInicio`, `Pedido.fotosTermino` | "68% de pedidos tienen evidencia fotográfica" |
| Pedidos con Feedback/Resumen | `COUNT(pedidos WHERE resumen IS NOT NULL)` | `Pedido.resumen` | "85% de pedidos tienen feedback del profesional" |
| Pedidos por Especialidad | `COUNT(pedidos) GROUP BY specialties` | `Pedido.specialties` | "Electricidad: 30%, Gasfitería: 25%" |

### ⚙️ Métricas de Operaciones y Calidad

| KPI                          | Fórmula                                                                 | Campos Requeridos                                                                 | Aplicación Local                      |
|------------------------------|-------------------------------------------------------------------------|----------------------------------------------------------------------------------|---------------------------------------|
| Tiempo Promedio por Etapa    | `AVG(tiempo entre status) usando Pedido.statusHistory`                   | `Pedido.statusHistory`                                                            | "Promedio 'Pagado' a 'Agendado': 1.5 hrs" |
| Tiempo Promedio de Ejecución | `AVG(Pedido.fechaFinalizacion - Pedido.fechaCreacion)`                   | `Pedido.fechaFinalizacion`, `Pedido.fechaCreacion`                                | "1.2 días promedio" |
| Tasa de Cancelación          | `(COUNT(pedidos WHERE status='cancelled') / COUNT(total)) * 100`         | `Pedido.status`                                                                   | "Cancelaciones: 12% últimos 30 días" |
| Pedidos por Comuna           | `COUNT(pedidos) GROUP BY serviceAddress.commune`                         | `Pedido.serviceAddress.commune`                                                   | "Providencia: 23%, Las Condes: 18%"  |
| Satisfacción por Región      | `AVG(Pedido.rating.stars) GROUP BY serviceAddress.region`                | `Pedido.rating.stars`, `Pedido.serviceAddress.region`                             | "RM: 4.2 estrellas, V Región: 4.0"   |
| Horarios Preferidos          | `COUNT(pedidos) GROUP BY HOUR(Pedido.createdAt)`                         | `Pedido.createdAt`                                                                | "Peak: 14:00-16:00 hrs"              |
| Análisis de Zonas            | `COUNT(pedidos) GROUP BY serviceAddress.zone`                            | `Pedido.serviceAddress.zone`                                                      | "Zona Oriente concentra el 45% de los servicios" |
| Pedidos con Boleta Adjunta   | `COUNT(pedidos WHERE boletaUrl IS NOT NULL)`                             | `Pedido.boletaUrl`                                                                | "60% de pedidos tienen boleta digital" |
| Pedidos por Estado de Ejecución | `COUNT(pedidos) GROUP BY estadoEjecucion`                              | `Pedido.estadoEjecucion`                                                          | "Finalizada: 92%, Pendiente: 8%" |
| Pedidos por Profesional      | `COUNT(pedidos) GROUP BY nombreProfesional`                              | `Pedido.nombreProfesional`                                                        | "Martín Lucero Palma: 18 pedidos" |
| Pedidos por Cliente          | `COUNT(pedidos) GROUP BY nombreCliente`                                  | `Pedido.nombreCliente`                                                            | "Catalina Bustos: 5 pedidos" |

### 💖 Métricas de Retención y Lealtad

| KPI                          | Fórmula                                                                 | Campos Requeridos                                                                 | Impacto Chile                         |
|------------------------------|-------------------------------------------------------------------------|----------------------------------------------------------------------------------|---------------------------------------|
| Retención 30/60/90 días      | `% usuarios que repiten compra en X días`                              | `User.createdAt`, `Pedido.userId`, `Pedido.fechaCreacion`                          | "Retención a 30 días: 28%"           |
| Valor Vida del Cliente (CLP) | `SUM(Pedido.montoTotal) / COUNT(DISTINCT Pedido.userId)`                        | `Pedido.montoTotal`, `Pedido.userId`                                                | "CLV 6 meses: $124,500 CLP"          |
| Usuarios Activos Mensuales   | `COUNT(DISTINCT users WHERE lastLoginAt >= [fecha_inicio_mes])`        | `User.lastLoginAt`                                                               | "MAU: 12,340 usuarios"               |
| Tasa de Recompra             | `COUNT(users con ≥2 pedidos) / COUNT(total usuarios)`                  | `Pedido.userId`                                                               | "32% de clientes recurrentes"        |
| Pedidos Promedio por Cliente (por Comuna) | `COUNT(pedidos) / COUNT(DISTINCT Pedido.userId) GROUP BY comuna` | `Pedido.userId`, `Pedido.comuna` | "Vitacura: 2.3 compras/cliente" |
| Cohortes de Retención        | Mapa de calor de % de usuarios que vuelven a comprar por mes de registro| User.createdAt, Pedido.fechaCreacion, Pedido.userId | "Retención cohortes: ver gráfico" |
| Segmentación RFM             | Algoritmo que asigna segmento por Recencia, Frecuencia, Monetario       | Pedido.fechaFinalizacion, Pedido.userId, Pedido.montoTotal | "Segmentos: Campeones, Leales, etc." |
| Programa de Referidos        | % de clientes referidos y su retención                                  | User.acquisitionInfo.referredBy, Pedido.userId | "% referidos y retención" |

### 🎯 Métricas de Segmentación y Marketing
| KPI | Propósito | Fórmula / Lógica | Campos Requeridos |
| :--- | :--- | :--- | :--- |
| Segmentación por Especialidad | Agrupar clientes por tipo de trabajo solicitado. | `COUNT(pedidos) GROUP BY specialties` | `Pedido.specialties` |
| Segmentación RFM | Agrupar clientes por Recencia, Frecuencia y Valor Monetario para campañas dirigidas. | Algoritmo que asigna un puntaje basado en `Pedido.fechaFinalizacion`, `Pedido.userId`, `Pedido.montoTotal`. | `Pedido.fechaFinalizacion`, `Pedido.userId`, `Pedido.montoTotal` |
| Efectividad de Campañas | Medir el ROI de las campañas de marketing digital. | `COUNT(pedidos) GROUP BY acquisitionInfo.campaign` | `Pedido.acquisitionInfo` |
| Programa de Referidos | Analizar el crecimiento viral. | `COUNT(Users) WHERE acquisitionInfo.source = 'referral'` | `User.acquisitionInfo.referredBy` |
| Predicción de Churn | Identificar clientes en riesgo de abandono. | Modelo que analiza lastLoginAt, Pedido.fechaFinalizacion, frecuencia y otros patrones. | `User.lastLoginAt`, `Pedido.fechaFinalizacion`, etc. |

---

## 🚀 Recomendación Estratégica
**Exportar datos a BigQuery** para:
- Consultas complejas sin afectar rendimiento
- Análisis avanzados
- Visión 360° del negocio

[Extensión Firebase → BigQuery](https://firebase.google.com/products/extensions/firebase-firestore-bigquery-export)

## ✅ Beneficios Clave

-   **Mayor granularidad y calidad**: La colección `pedidos` permite KPIs más ricos y dashboards más completos.
-   **Trazabilidad y evidencia**: Fotos, feedback, profesional y cliente en cada pedido.
-   **Organización y Escalabilidad**: El uso de colecciones de nivel superior para pedidos, servicios y categorías garantiza un rendimiento óptimo y una gestión sencilla.
-   **Integración UI/UX**: Las interfaces y el modelo de datos son consistentes con las pantallas propuestas, facilitando la colaboración.
-   **Control de privacidad**: La configuración granular permite al usuario gestionar su privacidad de forma efectiva.

## 📖 Glosario de Términos

...existing code...
