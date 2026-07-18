# syntax=docker/dockerfile:1

# ---------- deps: instala dependencias en una capa cacheable ----------
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

# ---------- dev: servidor de Vite con hot-reload para docker-compose ----------
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---------- build: compila el bundle estático de producción ----------
FROM deps AS build
COPY . .
# VITE_API_BASE_URL se hornea en el bundle en build-time (Vite no soporta env
# vars en runtime): en Cloud Run se pasa como --build-arg al hacer el build,
# ver infra/terraform y README → "Despliegue".
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# ---------- production: nginx sirviendo el bundle estático ----------
FROM nginx:1.27-alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

# Cloud Run inyecta PORT (por defecto 8080); nginx.conf usa la variable de
# entorno vía envsubst en el entrypoint por defecto de la imagen oficial.
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD wget -q --spider http://localhost:${PORT}/ || exit 1
