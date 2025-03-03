FROM nginx:mainline

RUN apt update && apt install openssl -y

RUN mkdir -p /home/web/www
RUN openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048 &&\
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/ssl/certs/self.key -out /etc/ssl/certs/self.crt \
    -subj "/C=RU/ST=Moscow/L=Kremlin/O=clockify-x-youtrack admin/OU=Org/CN=330729.simplecloud.ru"

COPY nginx.conf /etc/nginx/conf.d/default.conf
