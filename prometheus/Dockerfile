FROM prom/prometheus:v2.45.0

COPY prometheus.yaml /etc/prometheus/prometheus.yaml
COPY alert.rules.yaml /etc/prometheus/alert.rules.yaml

EXPOSE 9090

CMD ["--config.file=/etc/prometheus/prometheus.yaml"]