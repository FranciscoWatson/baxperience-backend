# Data Processor

Este microservicio es responsable de procesar los datos crudos que provienen de diversas fuentes dentro de la plataforma BAXperience. Su objetivo principal es transformar, limpiar y estructurar la información para que pueda ser utilizada de manera eficiente por otros componentes del sistema.

## Funciones principales

- Procesar y normalizar datos provenientes de:
  - Scraping de sitios oficiales
  - APIs públicas (como las del GCBA)
  - Datasets abiertos en formatos como CSV o JSON
- Aplicar validaciones, enriquecimiento semántico y limpieza de datos.
- Almacenar los resultados procesados en su propia base de datos.