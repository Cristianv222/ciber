# Imagen de desarrollo con hot-reload (Vite dev server)
FROM node:20-bookworm-slim

WORKDIR /app

# Instala dependencias primero (capa cacheable)
COPY package.json ./
RUN npm install

# El código se monta por bind-mount en docker-compose (hot-reload);
# esta copia sirve para construir la imagen de forma autónoma.
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
