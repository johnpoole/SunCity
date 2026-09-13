FROM nginx:1.27-alpine
COPY index.html chapters.json /usr/share/nginx/html/
COPY audio /usr/share/nginx/html/audio
