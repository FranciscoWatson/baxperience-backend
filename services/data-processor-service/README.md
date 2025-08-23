# Data Processor

Este microservicio es responsable de procesar los datos crudos que provienen de diversas fuentes dentro de la plataforma BAXperience. Su objetivo principal es transformar, limpiar y estructurar la información para que pueda ser utilizada de manera eficiente por otros componentes del sistema.

## Funciones principales

- Procesar y normalizar datos provenientes de:
  - Scraping de sitios oficiales
  - APIs públicas (como las del GCBA)
  - Datasets abiertos en formatos como CSV o JSON(VAMOS A LEER LOS DATASETS DESDE ARCHIVOS LOCALES, HACER CARPETA DE DATASETS. AL MOMENTO DE EJECUTARSE EL MAIN VA A LEER TODOS LOS DATASETS Y PROCESARLOS)
  HACER VARIAS FUNCIONES, UNA PARA CADA DATASET PORQUE CADA UNA TIENE INFO DISTINTA, POR EJEMPLO UNA FUNCION PARA EL DATASET DE MUSEOS, OTRA PARA EVENTOS CULTURALES, OTRA PARA EL SCRAPPER, 
  EJEC ALGORITMO DE CLUSTERING CADA VEZ QUE LLEGUE INFO NUEVA DEL SCRAPPER
- Aplicar validaciones, enriquecimiento semántico y limpieza de datos.
- Almacenar los resultados procesados en su propia base de datos.


18/8
sumarle datos de bdd operacional al proceso etl, agregar valorizacion de los users, itinerarios
ver como hacer para que el scrapper le mande al data processor y a la bdd operacional
implementar clustering
implementar kafka
hacer el api gateway

implementar el servicio de api de ciudad de bs as para transporte, etc
client_id: d5f408da192747d69a4297b3c7d6c341
client_secret: b010cd785E6c460898BA0AD91D562114
hacer front


ajustar datos de la tabla de pois, fijarse que algunos registros no traen la direccion desestructurada, otros si, tambien ajustar por ejemplo el CP a un formato solo, no que traiga formatos distintos