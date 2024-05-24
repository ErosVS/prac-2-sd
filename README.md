## Distributed storage systems and the CAP theorem 
Authors:
- Roger Massana 
- Eros Vilar

Para ejecutar la práctica:
1. Si se quiere ejecutar el test de centralized.py, ejecutar el test y automáticament ya arranca los servidores master y esclavos (centralized.py)
2. Si se quiere ejecutar el test de decentralized.py, ejecutar el test y automáticament ya arranca los servidores nodo (decentralized.py)

En caso de no funcionar correctamente, volver a compilar el fichero `store.proto`:

```protobuf
-I
.
--python_out=.
--grpc_python_out=.
--pyi_out=.
./proto/store.proto
```

Otro posible problema puede ser que no estén creados los directorios de la 'base de datos'.
- Debe existir tambien una carpeta llamada `db`, con los siguientes subdirectorios:
  - `/centralized` -> Guarda un fichero JSON con los datos del master_node y slave_node (uno por cada uno, identificado con su respectivo id)
  - `/decentralized` -> Guarda un fichero JSON con los datos de cada nodo (cada uno, identificado con su respectivo id))