# Documentacion práctica 2

[Link GitHub](https://github.com/ErosVS/prac-2-sd)

## 1. Resumen

Este proyecto implementa un sistema de almacenamiento distribuido de clave-valor con arquitecturas centralizadas y descentralizadas, utilizando gRPC para la comunicación entre nodos.
El sistema centralizado emplea una configuración maestro-esclavo, mientras que el sistema descentralizado utiliza un enfoque basado en quórum.
Cada enfoque se evalúa en términos de rendimiento, consistencia y tolerancia a fallos (critical failure, recovery after failure, ...).
El objetivo del proyecto consiste en explorar las compensaciones entre estas arquitecturas en términos de tiempos de respuesta y fiabilidad bajo diferentes condiciones.

## 2. Diseño del Sistema y Discusión
### Gestión de hilos y base de datos (BBDD)

Para gestionar distintos hilos, hemos usado locks tanto en el sistema centralizado como en el sistema descentralizado, para que las operaciones de lectura y escritura que hagan distintos threads a un mismo valor sean consistentes.
Para lograr esto hemos creado un lock para cada nodo, ya sea maestro, esclavo 1 y esclavo 2 para la arquitectura maestro-esclavo, y nodo 1, nodo 2, y nodo 3 para la descentralizada.
Hemos inicializado el lock antes de crear la clase, y entonces todos los distintos threads de un mismo nodo usaran la misma referencia al lock.  También para tener datos consistentes entre todos los hilos de un mismo nodo, hemos inicializado los datos de forma global, antes de inicializar las clases de cada nodo, por el mismo motivo que el de inicializar el lock.

### Estructura

En cada tipo de sistema distribuido, hemos estructurado el código de la misma forma:
1. Script de configuración interna de cada nodo (master_node, slave_node y quorum_server), para crear la 'API' en un lugar diferente al script de inicialización del sistema.
2. Script de inicialización del sistema distribuido (centralized.py, decentralized.py).
Hemos abstraído estos dos conceptos para dar una mayor legibilidad al código y para nosotros poder gestionar mejor los bugs que han ido apareciendo durante el desarrollo de la práctica.
En el caso del sistema centralizado:
3. **master_node.py** y **slave_node.py**, contiene:
   - Los datos cargados de la base de datos, pasados por parámetro.
   - El lock comentado anteriormente para evitar problemas de consistencia entre distintos hilos.
   - Los segundos de delay aplicados a las distintas operaciones.
   - En el caso de master node también tiene los canales y los stubs de cada esclavo.
   - El master node también tiene la ip y el puerto de los distintos esclavos.
4. **quorum_server.py**, contiene:

   - El identificador del nodo actual.
   - El peso del nodo para las distintas operaciones de lectura y escritura.
   - Los datos cargados de la base de datos, pasados por parámetro.
   - La url de conexión del propio nodo, para no enviar-se las operaciones de votación a él mismo.
   - La url de conexión de los demás nodos.
   - El lock comentado anteriormente para evitar problemas de consistencia entre distintos hilos.

## 3. Comparación de Sistemas

Antes de ver los resultados de las pruebas, queremos hacer un análisis sobre las ventajas y desventajas de cada enfoque:

### Sistema Centralizado

Las principales decisiones de diseño incluyen:

- **Fortalezas**: Alta consistencia, resolución de conflictos simplificada.
- **Limitaciones**: Punto único de fallo, posible cuello de botella en el maestro.

### Sistema Descentralizado

Las principales decisiones de diseño incluyen:
- **Fortalezas**: Mejor tolerancia a fallos, distribución equilibrada de la carga.
- **Limitaciones**: Mayor complejidad, posibilidad de estados inconsistentes durante particiones de red.

### Resultados de Evaluación
#### Sistema Centralizado

- **Operaciones Normales**: 1.06 segundos para 400 operaciones.
- **Ralentización del Maestro**: 41.38 segundos para 400 operaciones.
- **Ralentización del Esclavo**: 21.17 segundos para 400 operaciones.

#### Sistema Descentralizado

- **Operaciones Normales**: 1.62 segundos para 400 operaciones.
- **Ralentización del Nodo**: 28.92 segundos para 400 operaciones.

### Comparación y Razonamiento

- **Rendimiento**: 
  - El sistema centralizado funciona un poco mejor en condiciones normales (sin mucha carga de trabajo), pero se degrada significativamente cuando se ralentiza el maestro. Esto ocurre ya que del nodo master dependen la resta de nodos, ya que és el único que puede realizar operaciones PUT y, si este se ralentiza, todos los demás nodos se quedan esperando a que se desbloquee para saber si pueden realizar la accion doCommit o, por lo contrario, doAbort. Cuando se degradan los esclavos, este no pierde tanto su potencial, ya que estos solamente responden ante peticiones GET y su lógica no es tan compleja como la del master.
  - El sistema descentralizado mantiene un rendimiento más consistente bajo estrés debido al control distribuido. Como se utiliza un enfoque basado en quórum, este proporciona diversas ventajas, como la distribución de la carga y la tolerancia a fallos cuando un nodo está sobrecargado, ya que los otros nodos contestan antes ante una peticion, y el nodo sobrecargado no realiza ninguna nueva acción.
- **Consistencia**: 
  - El sistema centralizado ofrece una fuerte consistencia debido a la arquitectura maestro-esclavo.
  - El sistema descentralizado proporciona una consistencia eventual, ya que si los nodos con los datos actualizados estan saturados, y se lee de un nodo aún no actualizado, los datos pueden no ser consistentes..
- **Tolerancia a Fallos**:
  - El sistema descentralizado sobresale en tolerancia a fallos, ya que el mecanismo de quórum puede continuar funcionando a pesar de fallos en nodos individuales.

## 4. Preguntas
### 4.1. Q1 Justifique el nivel de consistencia de su implementación centralizada.
La implementación centralizada mantiene una fuerte consistencia, ya que todas las operaciones son coordinadas a través del nodo maestro. Esto asegura que todos los esclavos tengan el mismo estado, ya que las actualizaciones se propagan desde el maestro utilizando el protocolo 2PC (Two-Commit Phase Protocol). Cualquier operación de lectura siempre devuelve la escritura más reciente.

### 4.2. Q2 Caracterice cada una de sus implementaciones según el teorema CAP.
- **Implementación Centralizada**:
  - **Consistencia (C)**: Se mantiene una fuerte consistencia, ya que todas las actualizaciones pasan por el maestro.
  - **Disponibilidad (A)**: Menor disponibilidad debido a la dependencia del nodo maestro.
  - **Particiones (P)**: Tolerancia a particiones limitada; si el nodo maestro falla, el sistema se vuelve inoperativo.

- **Implementación Descentralizada**:
  - **Consistencia (C)**: Ofrece consistencia eventual; las operaciones basadas en quórum aseguran la consistencia de los datos con el tiempo.
  - **Disponibilidad (A)**: Mayor disponibilidad, ya que el sistema puede funcionar incluso si algunos nodos fallan.
  - **Particiones (P)**: Alta tolerancia a particiones; puede manejar particiones de red continuando operando con los nodos disponibles.
