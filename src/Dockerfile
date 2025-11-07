FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia a pasta 'src' inteira para dentro do container
COPY src/ ./src/

# Define o ponto de entrada padrão (será sobrescrito pelo Docker Compose)
ENTRYPOINT ["python3"]