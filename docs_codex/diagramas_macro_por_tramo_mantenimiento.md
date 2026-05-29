# Diagramas macro por tramo - Ciclo de mantenimiento

Modulo: **Barca Mantenimiento**  
Base funcional: 8 tramos del ciclo operativo de mantenimiento.

## 1. Diagrama macro

```mermaid
flowchart LR
    T1["1. Plan PM<br/>Plan activo"] --> A1{"Cumple trigger<br/>y no hay duplicado?"}
    A1 -->|Si| AV["Aviso nuevo"]
    A1 -->|No| S1["Sin aviso PM"]

    T2["2. Solicitud<br/>Nueva"] --> A2{"Programador/Admin<br/>genera aviso?"}
    A2 -->|Si| AV
    A2 -->|No| S2["Cancelada o pendiente"]

    T3["3. Checklist<br/>Nuevo"] --> A3{"Tiene al menos<br/>un No?"}
    A3 -->|Si| AV
    A3 -->|No| S3["Cerrado sin aviso<br/>o sin aviso"]

    AV --> T4["4. Aviso<br/>Nuevo"]
    T4 --> A4{"Evaluacion"}
    A4 -->|Rechazar| R4["Aviso rechazado"]
    A4 -->|Tomar para evaluacion| E4["Aviso en evaluacion"]
    E4 --> A5{"Fecha programada<br/>y equipo OK?"}
    A5 -->|No| E4
    A5 -->|Si| OT["Orden de Trabajo<br/>En ejecucion"]

    OT --> T5["5. OT<br/>Ejecucion y revision"]
    T5 --> ACT["6. Actividades OT"]
    ACT --> A6{"Todas notificadas?"}
    A6 -->|No| ACT
    A6 -->|Si| REV["OT en revision"]
    REV --> A7{"Decision<br/>Programador/Admin"}
    A7 -->|Devolver| OT
    A7 -->|Aprobar| AP["OT aprobada"]

    OT --> MAT["7. Materiales OT"]
    MAT --> MATF["Reserva / entrega / consumo / cierre"]
    MATF --> AP

    AP --> CIERRE["Cerrar etapa estandar OT"]
    CIERRE --> A8{"OT terminada?"}
    A8 -->|No| CIERRE
    A8 -->|Si| CAV["Cerrar aviso"]
    CAV --> FIN["Fin ciclo mantenimiento"]

    FLOT["8. Flotilla<br/>Cambio documental o cron"] --> AF{"Hay vencimientos/cambios<br/>y destinatarios?"}
    AF -->|Si| MAIL["Enviar correo"]
    AF -->|No| NMAIL["Sin envio"]
```

## 2. Tramo 1 - Plan PM

Documento: **Planes de Mantenimiento**  
Estado inicial: **Plan activo**  
Estado final esperado: **Aviso PM nuevo** o **sin aviso por no cumplir trigger/duplicado**

```mermaid
flowchart TD
    A["Plan activo"] --> B["Alcance: categoria y/o vehiculos"]
    B --> C["Actividades y materiales definidos"]
    C --> D{"Ejecucion"}
    D -->|Boton Generar avisos| E["Evaluar vehiculos"]
    D -->|Cron PM| E
    E --> F{"Plan tiene actividades?"}
    F -->|No| Z1["Omitir plan"]
    F -->|Si| G{"Vehiculo cumple trigger<br/>km, dias u horas?"}
    G -->|No| Z2["No genera aviso"]
    G -->|Si| H{"Existe aviso PM abierto<br/>para el vehiculo?"}
    H -->|Si| Z3["Omitir por duplicado"]
    H -->|No| I["Crear aviso origen PM"]
    I --> J["Copiar actividades del plan"]
    J --> K["Copiar materiales por actividad"]
    K --> L["Aviso PM Nuevo"]
```

## 3. Tramo 2 - Solicitud de Mantencion

Documento: **Solicitud de Mantencion**  
Estado inicial: **Nueva**  
Estado final esperado: **Aviso creado** o **Cancelada**

```mermaid
flowchart TD
    A["Nueva solicitud"] --> B["Usuario completa datos"]
    B --> C["Fecha se fija automaticamente"]
    C --> D["Selecciona vehiculo"]
    D --> E["Equipo de mantenimiento se carga automatico"]
    E --> F["Completa prioridad, estado, ubicacion y descripcion"]
    F --> G{"Decision"}
    G -->|Cancelar| H{"Ya genero aviso?"}
    H -->|Si| H1["No permite cancelar"]
    H -->|No| H2["Estado Cancelada"]
    G -->|Generar aviso| I{"Usuario Programador/Admin?"}
    I -->|No| I1["Boton no disponible"]
    I -->|Si| J{"Solicitud valida?"}
    J -->|Cancelada| J1["No permite generar aviso"]
    J -->|Ya tiene aviso| J2["No permite duplicado"]
    J -->|Valida| K["Crear aviso origen Solicitud"]
    K --> L["Guardar vinculo al aviso"]
    L --> M["Estado Aviso creado"]
    M --> N["Boton Ver aviso abre aviso vinculado"]
```

## 4. Tramo 3 - Checklist

Documento: **Checklist**  
Estado inicial: **Nuevo**  
Estado final esperado: **Aviso generado**, **Cerrado sin aviso** o **Cancelado**

```mermaid
flowchart TD
    A["Nuevo checklist"] --> B["Seleccionar tipo de vehiculo"]
    B --> C["Sistema carga puntos desde catalogo"]
    C --> D["Usuario registra datos generales"]
    D --> E["Usuario marca Si/No por punto"]
    E --> F{"Guardar"}
    F --> G{"Existe al menos un No?"}
    G -->|Si| H["Crear aviso origen Checklist"]
    H --> I["Vincular aviso al checklist"]
    I --> J["Estado Aviso generado"]
    J --> K["Boton Ver Aviso"]
    G -->|No| L["No genera aviso automatico"]
    L --> M{"Accion posterior"}
    M -->|Cerrar sin aviso| N["Estado Cerrado sin aviso"]
    M -->|Cancelar| O{"Tiene aviso?"}
    O -->|Si| O1["No permite cancelar"]
    O -->|No| O2["Estado Cancelado"]
    M -->|Guardar solamente| P["Permanece sin aviso"]
```

## 5. Tramo 4 - Aviso

Documento: **Avisos**  
Estado inicial: **Nuevo**  
Estado final esperado: **Con OT creada**, **Rechazado** o **Cerrado**

```mermaid
flowchart TD
    A["Aviso Nuevo"] --> B{"Programador/Admin decide"}
    B -->|Rechazar| C["Estado Rechazado"]
    B -->|Tomar para evaluacion| D["Estado En evaluacion"]
    D --> E["Registrar usuario y fecha de evaluacion"]
    E --> F["Revisar origen, vehiculo, equipo, prioridad"]
    F --> G["Completar Fecha programada"]
    G --> H["Revisar actividades y materiales"]
    H --> I{"Generar OT"}
    I -->|No| D
    I -->|Si| J{"Validaciones"}
    J -->|Sin equipo| J1["Error: debe existir equipo"]
    J -->|Sin fecha programada| J2["Error: completar fecha programada"]
    J -->|Ya tiene OT| J3["Error: aviso ya tiene OT"]
    J -->|OK| K["Crear Orden de Trabajo"]
    K --> L["Copiar actividades y materiales"]
    L --> M["Estado Con OT creada"]
    M --> N["Boton Ver OT"]
    M --> O{"Cerrar aviso"}
    O -->|OT no terminada| O1["No permite cerrar"]
    O -->|OT terminada| P["Estado Cerrado"]
```

## 6. Tramo 5 - Orden de Trabajo

Documento: **Orden de Trabajo**  
Estado inicial: **En progreso**  
Estado final esperado: **Cierre Total** o **Cierre Parcial**

```mermaid
flowchart TD
    A["OT En progreso"] --> B["Actividades copiadas desde aviso"]
    B --> C["Ejecutor trabaja actividades"]
    C --> D{"Enviar a revision"}
    D --> E{"Tiene actividades?"}
    E -->|No| E1["Error: debe tener al menos una actividad"]
    E -->|Si| F{"Todas notificadas?"}
    F -->|No| F1["Error: actividades pendientes"]
    F -->|Si| G["Resolver revisor automaticamente"]
    G --> H["Etapa En revisión"]
    H --> I{"Decision Programador/Admin"}
    I -->|Cierre Total| J["Etapa Cierre Total"]
    I -->|Cierre Parcial| J2["Etapa Cierre Parcial"]
    J --> K["Notificar responsable"]
    J2 --> K
    I -->|Devolver a ejecucion| L{"Motivo informado?"}
    L -->|No| L1["Error: completar motivo"]
    L -->|Si| M["Etapa En progreso"]
    M --> N["Incrementar contador de devoluciones"]
    N --> O["Notificar responsable"]
    O --> C
```

## 7. Tramo 6 - Actividades de OT

Documento: **Actividades de OT**  
Estado inicial: **Pendiente**  
Estado final esperado: **Notificada**

```mermaid
flowchart TD
    A["Actividad Pendiente"] --> B{"Boton Iniciar"}
    B --> C["Estado En ejecucion"]
    C --> D["Completar descripcion de lo realizado"]
    D --> E["Seleccionar resultado"]
    E --> F{"Boton Notificar"}
    F -->|Sin descripcion| F1["Error: completar descripcion"]
    F -->|Sin resultado| F2["Error: seleccionar resultado"]
    F -->|OK| G["Registrar fecha y usuario"]
    G --> H["Estado Notificada"]
    H --> I{"Actividad notificada?"}
    I -->|No| J["Queda Notificada"]
    H --> L{"Reabrir a pendiente?"}
    L -->|No| J
    L -->|Si, Programador/Admin| M["Limpiar fecha y usuario de notificacion"]
    M --> A
```

## 8. Tramo 7 - Materiales de OT

Documento: **Materiales de OT**  
Estado inicial: **Pendiente reserva**  
Estado final esperado: **Reservado/parcial/sin stock, entregado y cerrado**

```mermaid
flowchart TD
    A["Materiales en actividades de OT"] --> B{"Reservar materiales?"}
    B -->|No| G["Continuar sin reserva"]
    B -->|Si| C{"Hay materiales validos?"}
    C -->|No| C1["Estado Sin materiales"]
    C -->|Si| D["Crear picking interno"]
    D --> E["Confirmar y asignar stock"]
    E --> F{"Cantidad reservada"}
    F -->|Total| F1["Estado Reservado"]
    F -->|Parcial| F2["Estado Reserva parcial"]
    F -->|Cero| F3["Estado Sin stock suficiente"]
    F1 --> G
    F2 --> G
    F3 --> G
    G --> H["Bodega valida traslado interno en Inventario"]
    H --> I["Registrar consumo real"]
    I --> L{"Cerrar materiales"}
    L -->|Consumo > retirado| L1["Error: corregir consumo"]
    L -->|OK| M["Calcular devuelto"]
    M --> N["Calcular costo estimado y real"]
    N --> O["Ciclo de materiales cerrado"]
```

## 9. Tramo 8 - Flotilla

Documento: **Vehiculo / Flotilla**  
Estado inicial: **Cambio documental o revision programada**  
Estado final esperado: **Correo enviado** o **sin envio por falta de vencimientos/destinatarios**

```mermaid
flowchart TD
    A["Vehiculo de Flotilla"] --> B{"Evento"}
    B -->|Cambio Tarjeta combustible o TAG| C["Comparar valor anterior vs nuevo"]
    C --> D{"Hay cambio real?"}
    D -->|No| D1["No enviar correo"]
    D -->|Si| E["Buscar regla Modificaciones"]
    E --> F{"Hay destinatarios?"}
    F -->|No| F1["No enviar correo"]
    F -->|Si| G["Enviar correo de modificaciones"]

    B -->|Boton Enviar Avisos| H["Revisar todos los vehiculos"]
    B -->|Cron vencimientos| H
    H --> I["Evaluar licencia, permiso y revision tecnica"]
    I --> J["Usar dias alerta por vehiculo"]
    J --> K{"Hay vencimientos proximos?"}
    K -->|No| K1["No enviar correo"]
    K -->|Si| L["Buscar regla Vencimientos"]
    L --> M{"Hay destinatarios?"}
    M -->|No| M1["No enviar correo"]
    M -->|Si| N["Enviar correo de vencimientos"]
```
