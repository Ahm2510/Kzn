FROM node:20-alpine AS frontend_build

WORKDIR /app

# Build the primary frontend app
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci

COPY frontend/ ./frontend/
RUN cd frontend && npm run build


FROM nginx:1.27-alpine

COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/conf.d/ /etc/nginx/conf.d/

RUN rm -rf /usr/share/nginx/html/*
COPY --from=frontend_build /app/frontend/dist/ /usr/share/nginx/html/
