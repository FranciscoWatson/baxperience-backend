# Scraper Service

Este microservicio es responsable de obtener datos públicos desde portales del Gobierno de la Ciudad de Buenos Aires, como parte de la plataforma BAXperience.

## Estructura

- `main.py`: Punto de entrada del servicio.
- `scraper/turismo.py`: Contiene la lógica específica para scrapear actividades de turismo.
- `.env`: Configuración de entorno (por ejemplo, conexión a base de datos o Kafka).

## Dependencias principales

- `requests`
- `beautifulsoup4`
- `lxml`

## Instrucciones básicas

1. Crear y activar el entorno virtual:

```bash
python -m venv venv
source venv/bin/activate
