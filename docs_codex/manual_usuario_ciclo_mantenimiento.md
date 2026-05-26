# Manual de usuario - Ciclo de mantenimiento de vehiculos

Modulo: **Barca Mantenimiento**  
Menu raiz en Odoo: **Mantencion Barca**  
Version revisada: Odoo 18, modulo `zmm_ajustes`

Este manual explica el uso funcional del ciclo de mantenimiento implementado en el modulo: registro de origenes, generacion de avisos, evaluacion, creacion de Ordenes de Trabajo, ejecucion, revision, materiales, cierre y alertas documentales de flotilla.

## 1. Vista general del ciclo

El flujo completo funciona asi:

```text
Origen del aviso
  - Plan de Mantenimiento
  - Solicitud de Mantencion
  - Checklist
        |
        v
Aviso de mantencion
        |
        v
Orden de Trabajo
        |
        v
Ejecucion de actividades
        |
        v
Revision / aprobacion
        |
        v
Cierre de aviso y actualizacion de medidores
```

Los **Avisos** concentran la necesidad de mantenimiento. La **Orden de Trabajo** es donde se ejecuta el trabajo real, se notifican actividades y se controlan materiales.

## 2. Menus principales

Al entrar a **Mantencion Barca**, el sistema abre **Calendario Mantenimiento**.

| Menu | Uso |
|---|---|
| Origenes Avisos | Crear fuentes de avisos: planes, solicitudes y checklist. |
| Mantenimiento | Operacion diaria: odometros, avisos, ordenes de trabajo y calendario. |
| Informes | Analisis de solicitudes/ordenes de mantenimiento. |
| Equipos | Equipos de mantenimiento vinculados a vehiculos. |
| Configuracion | Catalogos maestros y reglas de distribucion. |

Submenus destacados:

| Ruta | Uso |
|---|---|
| Origenes Avisos > Planes de Mantenimiento | Definir mantenimiento preventivo por km, dias u horas. |
| Origenes Avisos > Solicitud de Mantencion | Registrar requerimientos simples de usuarios. |
| Origenes Avisos > Checklist | Registrar checklist operativo con respuestas Si/No. |
| Mantenimiento > Odometros | Registrar lecturas de odometro de vehiculos. |
| Mantenimiento > Avisos | Evaluar avisos y generar OT. |
| Mantenimiento > Orden de Trabajo | Gestionar OT estandar de Odoo con campos Barca. |
| Mantenimiento > Calendario Mantenimiento | Revisar OT programadas en calendario. |
| Configuracion > Checklist | Mantener catalogo de puntos de control. |
| Configuracion > Alertas | Mantener listas de correo de flotilla. |

## 3. Roles principales

| Rol | Uso funcional |
|---|---|
| Barca / Conductor | Puede crear solicitudes y checklist; consulta avisos, equipos, odometros y catalogos necesarios. |
| Barca / Programador | Configura planes, evalua avisos, genera OT, revisa y aprueba/devoluciona OT. |
| Barca / Ejecutor | Ejecuta actividades de OT, notifica avance y envia a revision. |
| Barca / Bodega | Consulta planes/materiales y puede trabajar con datos de materiales segun permisos. |
| Barca / Administrador | Acceso completo a configuracion y operacion del modulo. |

La visibilidad de botones depende del rol y del estado del documento.

## 4. Datos maestros

### 4.1 Vehiculos y equipos

Cada vehiculo de Flotilla (`fleet.vehicle`) tiene un equipo de mantenimiento asociado (`maintenance.equipment`). El modulo crea automaticamente un equipo cuando se crea un vehiculo nuevo. Si se cambia el nombre del vehiculo, tambien se sincroniza el nombre del equipo.

| Campo | Significado |
|---|---|
| Codigo interno | Calculado desde los dos ultimos digitos presentes en la patente. |
| Odometro ultimo servicio | Km del ultimo servicio cerrado. |
| Proximo servicio (km) | Calculado como ultimo servicio + 5000. |
| Horas de operacion | Horometro actual del vehiculo. |
| Horas operacion ultimo servicio | Horas registradas al ultimo servicio. |
| Ultima entrada a taller | Fecha de ingreso a taller. |
| Ultima salida a taller | Fecha de salida/cierre de servicio. |
| Documentacion | Permiso de circulacion, revision tecnica, tarjeta combustible, TAG y dias de alerta. |
| Seguro | Calculado si existe contrato cuyo subtipo contiene "seguro". |

### 4.2 Ubicaciones tecnicas

Ruta: **Mantencion Barca > Configuracion > Ubicaciones tecnicas**.

Representan partes o sistemas del vehiculo donde se realizan actividades. Pueden tener jerarquia padre/hijo y se filtran por categoria de vehiculo.

| Campo | Uso |
|---|---|
| Nombre | Nombre visible de la ubicacion. |
| Codigo | Codigo unico usado tambien para importaciones. |
| Categoria de vehiculo | Categoria a la que aplica. |
| Ubicacion padre | Permite armar arboles de ubicaciones. |
| Ruta completa | Calculada con la jerarquia. |
| Kit sugerido | Kit asociado como referencia. |
| Vida util estimada | Dato informativo. |
| Proveedor referencia | Proveedor asociado a esa ubicacion. |

### 4.3 Tipos de intervencion

Ruta: **Mantencion Barca > Configuracion > Tipos de intervencion**.

Catalogo simple para clasificar el tipo de trabajo, por ejemplo inspeccion, cambio, ajuste o reparacion.

### 4.4 Actividades

Ruta: **Mantencion Barca > Configuracion > Actividades**.

Define tareas reutilizables que luego se copian a planes, avisos y OT.

| Campo | Uso |
|---|---|
| Nombre actividad | Nombre de la tarea. |
| Codigo | Codigo interno opcional. |
| Categoria de vehiculo | Categoria donde aplica. |
| Ubicacion tecnica | Parte/sistema del vehiculo donde se realiza. |
| Duracion estimada | Tiempo esperado en horas. |
| Instrucciones tecnicas | Texto guia para ejecucion. |
| Materiales / Repuestos / Kits estandar | Productos sugeridos para la actividad. |

Los materiales estandar de una actividad son una plantilla. Al copiarlos a un plan, quedan como lineas propias del plan; cambiar la actividad despues no cambia planes ya configurados.

### 4.5 Kits

Ruta: **Mantencion Barca > Configuracion > Kits**.

Permiten agrupar productos como referencia funcional. En los flujos actuales, los kits se tratan como productos normales cuando se agregan a materiales; no se explotan automaticamente en componentes.

### 4.6 Catalogo de Checklist

Ruta: **Mantencion Barca > Configuracion > Checklist**.

Administra los puntos de control que se cargan en los checklist operativos.

| Campo | Uso |
|---|---|
| Tipo de vehiculo | Tipo de checklist: camion, camion y equipo AP, camion y equipo AV, vehiculo. |
| Tipo de Control | Agrupador del punto de control. |
| Item de Control | Punto concreto a revisar. |
| Secuencia | Orden en que aparece en el checklist. |
| Activo | Indica si se debe cargar en nuevos checklist. |

## 5. Planes de Mantenimiento

Ruta: **Mantencion Barca > Origenes Avisos > Planes de Mantenimiento**.

Un plan define mantenimiento preventivo por categoria de vehiculo, vehiculos especificos o ambos.

| Campo | Uso |
|---|---|
| Nombre del plan | Nombre funcional del plan. |
| Categoria | Categoria de vehiculo afectada. |
| Vehiculos especificos | Vehiculos puntuales incluidos. |
| Actividades del plan | Actividades que se ejecutaran cuando el plan genere aviso. |
| Intervalo km | Frecuencia por kilometraje. |
| Inicio km | Km desde donde comienza a aplicar. |
| Aviso anticipado km | Km antes del vencimiento donde se genera aviso. |
| Intervalo dias | Frecuencia por dias. |
| Inicio dias | Dias desde fecha base en que empieza el plan. |
| Aviso anticipado dias | Dias antes del vencimiento donde se genera aviso. |
| Intervalo horas | Frecuencia por horas de operacion. |
| Inicio horas | Horas desde donde comienza a aplicar. |
| Activo | Si el cron debe considerar el plan. |

Reglas:

- Debe tener categoria o vehiculos especificos.
- Debe tener al menos un trigger: km, dias u horas.
- Los intervalos deben ser mayores que cero.
- El aviso anticipado debe ser menor que el intervalo.

Cada linea de actividad del plan contiene ubicacion tecnica, tipo de intervencion, actividad, duracion estimada, observaciones y materiales.

Boton **Cargar materiales estandar**:

- Copia los materiales definidos en la actividad maestra hacia la linea del plan.
- No se ejecuta si la actividad no tiene materiales estandar.
- No se ejecuta si la linea del plan ya tiene materiales, para evitar sobrescribir ajustes manuales.

Boton **Generar avisos**:

1. Evalua los vehiculos del plan.
2. Revisa si se cumple algun trigger activo: km, dias u horas.
3. Evita duplicados: no crea un nuevo aviso PM si el vehiculo ya tiene un aviso PM abierto.
4. Crea un aviso con origen **PM**.
5. Copia las actividades y materiales del plan al aviso.
6. Muestra una notificacion con cantidad de avisos creados y duplicados omitidos.

El cron **Generar avisos PM** ejecuta esta misma logica automaticamente sobre planes activos.

## 6. Solicitud de Mantencion

Ruta: **Mantencion Barca > Origenes Avisos > Solicitud de Mantencion**.

La solicitud es un requerimiento simple inicial. No es la OT. Sirve para que un usuario reporte una necesidad, que luego un programador puede convertir en aviso.

| Campo | Uso |
|---|---|
| N Solicitud | Secuencia automatica. |
| Fecha de solicitud | Fecha/hora actual, bloqueada. |
| Solicitado por | Usuario solicitante. |
| Prioridad sugerida | Baja, Media o Alta. |
| Estado del vehiculo | Operativo o No operativo. |
| Vehiculo | Vehiculo afectado. |
| Equipo de mantenimiento | Se carga automaticamente desde el vehiculo y queda bloqueado. |
| Planta y Lugar detallado | Ubicacion fisica reportada por el usuario. |
| Descripcion de la necesidad | Detalle de lo solicitado. |
| Aviso generado | Vinculo al aviso creado, si existe. |

Estados:

| Estado | Significado |
|---|---|
| Nueva | Solicitud editable y pendiente de convertir. |
| Aviso creado | Ya genero un aviso. |
| Cancelada | Se cancelo antes de generar aviso. |

Botones:

| Boton | Disponible cuando | Funcion |
|---|---|---|
| Generar aviso | Estado Nueva, para Programador/Admin | Crea un aviso con origen Solicitud y copia datos principales. |
| Ver aviso | Existe aviso generado | Abre el aviso vinculado. |
| Cancelar | Estado Nueva | Cancela la solicitud si aun no genero aviso. |

Restricciones:

- No se puede cancelar una solicitud que ya genero aviso.
- No se puede generar aviso desde una solicitud cancelada.
- No se puede generar mas de un aviso desde la misma solicitud.

## 7. Checklist

Ruta: **Mantencion Barca > Origenes Avisos > Checklist**.

El checklist carga puntos de control desde el catalogo por tipo de vehiculo y permite responder **Si** o **No**.

| Campo | Uso |
|---|---|
| N Checklist | Secuencia automatica. |
| Solicitante | Usuario que registra el checklist. |
| Fecha | Fecha actual, bloqueada. |
| Tipo de vehiculo | Tipo de checklist que determina los puntos de control. |
| Estado del vehiculo | Operativo o No operativo. |
| Equipo | Vehiculo/equipo revisado. |
| Equipo de mantenimiento | Se carga automaticamente desde el vehiculo. |
| Hora carga combustible | Hora registrada, con formato horario. |
| Odometro | Lectura informada en el checklist. |
| Planta y lugar detallado | Ubicacion fisica. |
| Observaciones | Comentario general. |
| Puntos de control | Lineas Si/No cargadas desde el catalogo. |

Al cambiar **Tipo de vehiculo**, el sistema regenera los puntos de control. Si habia respuestas marcadas, se limpian para evitar mezclar tipos distintos.

Estados:

| Estado | Significado |
|---|---|
| Nuevo | Checklist editable. |
| Aviso generado | Al guardar habia al menos un punto marcado No y se creo aviso. |
| Cerrado sin aviso | Se cerro porque no tenia respuestas No. |
| Cancelado | Se cancelo antes de generar aviso. |

Cada punto permite marcar **Si** o **No**. Son excluyentes: una linea no puede tener ambas respuestas marcadas.

Botones y guardado:

| Boton | Funcion |
|---|---|
| Guardar | Guarda el checklist. Si existe al menos un No, genera automaticamente un aviso. |
| Ver Aviso | Abre el aviso vinculado cuando existe. |

Logica automatica al guardar:

- Si hay al menos un **No**, crea aviso con origen **Checklist**.
- Si no hay ningun **No**, no crea aviso.
- La descripcion del aviso usa las observaciones; si estan vacias, usa un texto automatico.
- Los puntos de control no se copian como actividades al aviso.

## 8. Avisos

Ruta: **Mantencion Barca > Mantenimiento > Avisos**.

El aviso representa una necesidad de mantenimiento detectada desde PM, Solicitud o Checklist. Desde aqui se evalua y se genera una OT.

| Campo | Uso |
|---|---|
| N Aviso | Secuencia automatica. |
| Origen | PM, Checklist o Solicitud. |
| Referencia de origen | Numero del documento origen. |
| Plan / Solicitud / Checklist origen | Vinculos tecnicos segun origen. |
| Vehiculo | Vehiculo afectado. |
| Equipo de mantenimiento | Equipo asociado al vehiculo. |
| Odometro | Km registrado al generar aviso. |
| Horas de operacion | Horas registradas al generar aviso. |
| Prioridad | Baja, Media o Alta. |
| Fecha programada | Obligatoria antes de generar OT. |
| Actividades | Actividades copiadas desde plan o editadas en aviso segun permisos. |
| Materiales | Productos copiados por actividad. |
| Descripcion | Descripcion del aviso. |
| Observacion de origen | Resumen del documento origen. |
| OT asociada | Orden de Trabajo creada desde el aviso. |

Estados:

| Estado | Significado |
|---|---|
| Nuevo | Aviso recien creado, pendiente de evaluacion. |
| En evaluacion | Tomado por Programador/Admin para analizar y preparar OT. |
| Con OT creada | Ya se genero una OT. La ejecucion ocurre en la OT. |
| Rechazado | Aviso descartado. |
| Cerrado | Aviso terminado, normalmente despues de cerrar/aprobar la OT. |
| En revision (legado) | Estado historico de compatibilidad. |

Botones:

| Boton | Disponible cuando | Funcion |
|---|---|---|
| Tomar para evaluacion | Estado Nuevo, Programador/Admin | Cambia a En evaluacion, registra usuario y fecha. |
| Rechazar | Estado Nuevo o En evaluacion, Programador/Admin | Cambia a Rechazado. |
| Generar OT | Estado En evaluacion, sin OT, Programador/Admin | Crea una Orden de Trabajo estandar. Requiere fecha programada y equipo. |
| Ver OT | Estado Con OT creada y con OT asociada | Abre la OT vinculada. |
| Cerrar aviso | Estado Con OT creada, Programador/Admin | Cierra el aviso si la OT esta en una etapa terminada. |

Restricciones:

- El estado del aviso no se debe cambiar manualmente; se cambia con botones.
- Para generar OT, la **Fecha programada** es obligatoria.
- Para generar OT, debe existir equipo de mantenimiento.
- El aviso solo puede cerrarse si tiene OT asociada y la etapa de la OT esta marcada como terminada en Odoo.

Cuando el aviso viene de un plan, hereda ubicacion tecnica, tipo de intervencion, actividad, duracion, observaciones y materiales. Es una copia propia: cambiar el plan despues no cambia avisos ya generados.

## 9. Orden de Trabajo

Ruta: **Mantencion Barca > Mantenimiento > Orden de Trabajo**.

La OT corresponde al modelo estandar `maintenance.request`, mostrado funcionalmente como **Orden de Trabajo**. El modulo agrega actividades, materiales y revision usando la misma barra de etapas estandar que controla el Kanban.

Al presionar **Generar OT** en el aviso:

1. Se crea una OT con nombre igual al numero de aviso.
2. Se copia la fecha programada del aviso a la OT.
3. Se asigna el equipo de mantenimiento.
4. Se copia la descripcion del aviso.
5. Se copian las actividades del aviso como actividades ejecutables de OT.
6. Se copian los materiales de cada actividad.
7. El aviso queda en estado **Con OT creada**.

Etapas principales de la OT:

| Estado | Significado |
|---|---|
| En progreso | OT en trabajo operativo. |
| Reparado | Ejecutor/Admin envio la OT para revision del programador. |
| Cierre Total | Programador/Admin cerro totalmente la OT. |
| Cierre Parcial | Programador/Admin cerro parcialmente la OT. |

Botones principales:

| Boton | Disponible cuando | Funcion |
|---|---|---|
| Enviar a revision | Etapa En progreso, Ejecutor/Admin | Valida actividades notificadas y cambia la OT a Reparado. |
| Cierre Total | Etapa Reparado, Programador/Admin | Cierra totalmente la OT y notifica al responsable. |
| Cierre Parcial | Etapa Reparado, Programador/Admin | Cierra parcialmente la OT y notifica al responsable. |
| Devolver a progreso | Etapa Reparado, Programador/Admin | Requiere motivo; vuelve a En progreso y notifica al responsable. |
| Reservar materiales | Sin reserva previa | Crea picking interno de reserva y asigna stock disponible. |
| Entregar materiales | Materiales no entregados ni cerrados | Registra entrega al tecnico. |
| Cerrar materiales | Materiales entregados y no cerrados | Calcula consumos, devoluciones y costos. |
| Smart button Reserva | Existe reserva | Abre el picking de reserva. |

## 10. Actividades de OT

Las actividades estan en la pestaña **Actividades**.

| Campo | Uso |
|---|---|
| Secuencia | Orden de trabajo de la actividad. |
| Ubicacion tecnica | Parte del vehiculo. |
| Tipo de intervencion | Clasificacion. |
| Actividad | Tarea a realizar. |
| Descripcion | Instruccion copiada desde la actividad. |
| Duracion estimada | Horas estimadas. |
| Estado operativo | Estado de ejecucion de la actividad. |
| Descripcion de lo realizado | Informe del ejecutor. |
| Resultado | Resuelto, Parcial o No resuelto. |
| Materiales | Productos usados/estimados para la actividad. |

Estados operativos:

| Estado | Significado |
|---|---|
| Pendiente | Actividad aun no iniciada. |
| En ejecucion | Actividad iniciada por el ejecutor. |
| Notificada | Ejecutor informo lo realizado y resultado. |
| Cerrada | Actividad cerrada despues de notificar. |

Botones:

| Boton | Disponible cuando | Funcion |
|---|---|---|
| Iniciar | Pendiente | Cambia la actividad a En ejecucion. |
| Notificar | En ejecucion | Abre/ejecuta notificacion. Requiere descripcion y resultado. |
| Cerrar linea | Notificada | Cambia la actividad a Cerrada. |
| Reabrir a pendiente | En ejecucion, Notificada o Cerrada; Programador/Admin | Limpia fecha/usuario de notificacion y vuelve a Pendiente. |

Para enviar la OT a revision, todas las actividades deben estar **Notificadas** o **Cerradas**.

## 11. Revision de OT

```text
En progreso -> Reparado -> Cierre Total / Cierre Parcial
             \-> Devuelta a En progreso
```

**Enviar a revision**

- Solo se permite en etapa **En progreso**.
- Requiere al menos una actividad.
- Todas las actividades deben estar notificadas o cerradas.
- El revisor se resuelve automaticamente: usuario que tomo el aviso para evaluacion; si no existe, el creador de la OT.
- Cambia la OT a **Reparado**, publica mensaje en el chatter y notifica al revisor.

**Cierre Total / Cierre Parcial**

- Solo desde **Reparado**.
- Disponible para Programador/Admin.
- Cambia a la etapa de cierre seleccionada.
- Limpia marcas de actividades agregadas/modificadas tras devolucion.
- Notifica al responsable de ejecucion de la OT.

**Devolver a progreso**

- Solo desde **Reparado**.
- Disponible para Programador/Admin.
- Requiere completar **Motivo de devolucion**.
- Cambia a **En progreso**.
- Incrementa contador de devoluciones.
- Notifica al responsable de ejecucion.

Si despues de una devolucion un Programador/Admin agrega o modifica actividades de planificacion, estas quedan marcadas como agregadas/modificadas tras devolucion hasta que la OT tenga cierre total o parcial.

## 12. Materiales de la OT

Los materiales se gestionan por actividad de OT.

| Campo | Uso |
|---|---|
| Repuesto / Kit / Material | Producto de Odoo. |
| UdM | Unidad de medida compatible con el producto. |
| Cantidad estimada | Cantidad planificada. |
| Cantidad reservada | Cantidad asignada desde reserva. |
| Cantidad retirada | Cantidad entregada al tecnico. |
| Cantidad consumida | Cantidad realmente usada. |
| Cantidad devuelta | Sobrante calculado al cerrar materiales. |
| Observacion | Nota libre. |

Las cantidades no pueden ser negativas y la unidad debe pertenecer a la misma categoria de la unidad base del producto.

### 12.1 Reservar materiales

Boton: **Reservar materiales**.

1. Lee todos los materiales de actividades con producto y cantidad estimada mayor que cero.
2. Agrupa por producto y unidad de medida.
3. Crea un `stock.picking` interno.
4. Crea movimientos de stock por producto/unidad.
5. Confirma y asigna el picking.
6. No valida el picking; no descuenta stock fisico.
7. Distribuye la cantidad reservada en las lineas de materiales.
8. Actualiza el estado de materiales.

Estados de materiales:

| Estado | Significado |
|---|---|
| Pendiente reserva | Estado inicial. |
| Sin materiales | No hay lineas validas para reservar. |
| Reservado | Todo lo solicitado fue reservado. |
| Reserva parcial | Se reservo algo, pero no todo. |
| Sin stock suficiente | No se logro reservar cantidad. |

Restricciones:

- No se permite crear una segunda reserva si ya existe un picking activo.
- Si la reserva previa fue cancelada o eliminada, el sistema limpia el vinculo y permite reservar de nuevo.
- Requiere almacen, ubicacion de stock, tipo de operacion interna y ubicacion destino valida.

### 12.2 Entregar materiales

Boton: **Entregar materiales**.

- Si una linea tiene cantidad reservada, usa esa cantidad como retirada.
- Si no tiene reserva, usa la cantidad estimada como retirada.
- Marca la OT con materiales entregados.
- Registra fecha y usuario de entrega.
- Publica resumen en chatter.
- No crea picking adicional.

### 12.3 Registrar consumo real

El consumo real se ingresa manualmente en **Cantidad consumida** de cada material. Ese dato representa lo efectivamente usado por el tecnico.

### 12.4 Cerrar materiales

Boton: **Cerrar materiales**.

1. Valida que los materiales hayan sido entregados.
2. Valida que la cantidad consumida no supere la retirada.
3. Calcula cantidad devuelta = retirada - consumida.
4. Registra fecha y usuario de cierre.
5. Calcula costo estimado y costo real con `standard_price`.
6. Publica resumen en chatter.

No crea picking de devolucion.

## 13. Cierre del aviso

Despues de ejecutar y revisar la OT, el aviso debe cerrarse desde **Mantenimiento > Avisos** con el boton **Cerrar aviso**.

Condiciones:

- El aviso debe estar en **Con OT creada**.
- Debe tener OT asociada.
- La OT debe estar en una etapa estandar marcada como terminada en Odoo.

Al cerrar un aviso de origen **PM**, el sistema actualiza el vehiculo:

| Campo actualizado | Regla |
|---|---|
| Odometro ultimo servicio | Usa el odometro del aviso si es mayor al actual. |
| Ultima salida a taller | Usa la fecha de cierre si no retrocede la fecha existente. |
| Horas operacion ultimo servicio | Usa las horas del aviso si son mayores al valor actual. |

Nunca retrocede medidores.

## 14. Odometros, calendario e informes

**Odometros**  
Ruta: **Mantencion Barca > Mantenimiento > Odometros**. Permite registrar lecturas de odometro de vehiculos. Estas lecturas alimentan el odometro actual usado por planes PM por kilometraje.

**Calendario Mantenimiento**  
Ruta: **Mantencion Barca > Mantenimiento > Calendario Mantenimiento**. Muestra las OT programadas. Al abrir el modulo desde el menu raiz, Odoo entra directamente a esta accion.

**Informes**  
Ruta: **Mantencion Barca > Informes > Solicitudes de mantenimiento**. Usa el modelo estandar `maintenance.request` en vistas grafico, pivote, lista y formulario para analizar solicitudes/OT por estado, equipo, responsable u otros criterios.

## 15. Flotilla y documentacion

El modulo amplia Flotilla con campos documentales y alertas por correo.

En el formulario del vehiculo se muestra una pestaña **Documentacion** con:

- Vencimiento permiso de circulacion.
- Vencimiento revision tecnica.
- Tarjeta combustible.
- TAG.
- Dias alerta vencimiento.
- Boton **Enviar Avisos**.

Tambien se calcula el vencimiento de licencia de conducir desde el empleado vinculado al conductor y la marca **Seguro** desde contratos de flotilla cuyo subtipo contenga "seguro".

### 15.1 Boton Enviar Avisos

Que hace:

1. Revisa todos los vehiculos, no solo el vehiculo abierto.
2. Evalua vencimientos dentro de la ventana configurada por **Dias alerta vencimiento**.
3. Considera licencia de conducir, permiso de circulacion y revision tecnica.
4. Busca destinatarios en la regla **Vencimientos**.
5. Envia correo si hay vencimientos y destinatarios.
6. Muestra notificacion con cantidad enviada o advertencia si no hay datos/destinatarios.

El cron **Enviar avisos vencimientos flotilla** ejecuta la misma logica.

### 15.2 Alertas por modificaciones documentales

Si se modifica **Tarjeta combustible** o **TAG**, el sistema envia correo a destinatarios de la regla **Modificaciones**.

Si no hay destinatarios configurados, no se envia correo.

### 15.3 Reglas de distribucion

Ruta: **Mantencion Barca > Configuracion > Alertas**.

| Regla | Uso |
|---|---|
| Modificaciones | Correos por cambios en tarjeta combustible o TAG. |
| Vencimientos | Correos por vencimientos documentales proximos. |

El campo **Nombres de correo** acepta varios correos separados por coma, punto y coma, espacios o saltos de linea.

## 16. Contratos de flotilla

En contratos de vehiculo (`fleet.vehicle.log.contract`) se agrega el campo **Adjuntos** para cargar multiples respaldos despues de notas.

La marca **Seguro** del vehiculo se calcula automaticamente si existe un contrato relacionado cuyo subtipo de costo contiene la palabra "seguro".

## 17. Errores frecuentes y como resolverlos

| Mensaje / situacion | Causa probable | Accion recomendada |
|---|---|---|
| Debe ingresar la Fecha programada antes de generar la OT | El aviso esta en evaluacion pero no tiene fecha programada. | Completar Fecha programada en el aviso. |
| Debe existir un equipo de mantenimiento | El vehiculo no tiene equipo asociado. | Revisar equipos o sincronizacion de vehiculo. |
| La solicitud ya tiene un aviso generado | Se intento generar aviso dos veces. | Usar Ver aviso. |
| No hay puntos marcados como No | Checklist sin fallas. | Guardar sin aviso o cerrar sin aviso si la accion esta disponible. |
| Todas las actividades deben estar notificadas | La OT tiene actividades pendientes/en ejecucion. | Notificar o cerrar actividades antes de enviar a revision. |
| Debe ingresar motivo de devolucion | Programador intenta devolver OT sin comentario. | Completar Motivo de devolucion. |
| Esta OT ya tiene una reserva vinculada | Ya existe picking de reserva. | Usar smart button Reserva o cancelar la reserva previa si corresponde. |
| Consumo real mayor que cantidad entregada | La cantidad consumida supera la retirada. | Corregir Cantidad consumida. |
| No hay destinatarios configurados | Regla de flotilla sin correos. | Completar regla Modificaciones o Vencimientos. |

## 18. Recomendacion operativa por rol

**Conductor / solicitante**

1. Crear **Solicitud de Mantencion** cuando detecte una necesidad puntual.
2. Crear **Checklist** cuando corresponda control operativo.
3. Completar vehiculo, ubicacion, estado del vehiculo y descripcion clara.

**Programador**

1. Mantener planes, actividades y catalogos.
2. Revisar avisos nuevos.
3. Tomar aviso para evaluacion.
4. Completar fecha programada.
5. Generar OT.
6. Revisar OT enviadas por ejecutores.
7. Aprobar o devolver con motivo.
8. Cerrar aviso cuando la OT ya este terminada.

**Ejecutor**

1. Abrir la OT asignada.
2. Iniciar actividades.
3. Registrar descripcion de lo realizado y resultado.
4. Notificar actividades.
5. Cerrar lineas si corresponde.
6. Enviar OT a revision cuando todas las actividades esten notificadas.

**Bodega**

1. Revisar materiales planificados.
2. Apoyar reserva, entrega y cierre de materiales segun permisos operativos.
3. Validar diferencias entre estimado, consumido y devuelto.

**Administrador**

1. Mantener permisos, catalogos y reglas.
2. Revisar integridad de equipos asociados a vehiculos.
3. Configurar listas de correo de flotilla.
4. Supervisar crons de PM y vencimientos.

## 19. Resumen de estados

Solicitud de Mantencion:

```text
Nueva -> Aviso creado
Nueva -> Cancelada
```

Checklist:

```text
Nuevo -> Aviso generado
Nuevo -> Cerrado sin aviso
Nuevo -> Cancelado
```

Aviso:

```text
Nuevo -> En evaluacion -> Con OT creada -> Cerrado
Nuevo -> Rechazado
En evaluacion -> Rechazado
```

OT Barca:

```text
En progreso -> Reparado -> Cierre Total
En progreso -> Reparado -> Cierre Parcial
Reparado -> En progreso
```

Actividad de OT:

```text
Pendiente -> En ejecucion -> Notificada -> Cerrada
```

Materiales de OT:

```text
Pendiente reserva -> Reservado / Reserva parcial / Sin stock suficiente / Sin materiales
Entrega de materiales -> Cierre de materiales
```
