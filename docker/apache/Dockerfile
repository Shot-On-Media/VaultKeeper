FROM httpd:2.4-alpine

RUN sed -i \
    -e 's/^#LoadModule proxy_module/LoadModule proxy_module/' \
    -e 's/^#LoadModule proxy_http_module/LoadModule proxy_http_module/' \
    -e 's/^#LoadModule rewrite_module/LoadModule rewrite_module/' \
    /usr/local/apache2/conf/httpd.conf

COPY docker/apache/vaultkeeper.conf /usr/local/apache2/conf/extra/vaultkeeper.conf
RUN printf '\nInclude conf/extra/vaultkeeper.conf\n' >> /usr/local/apache2/conf/httpd.conf

EXPOSE 80
