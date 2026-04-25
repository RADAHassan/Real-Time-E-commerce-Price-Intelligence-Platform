FROM apache/airflow:2.9.1-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER airflow
# Install project deps (scrapy, bigtable, analytics) + Airflow provider extras
COPY requirements.txt /tmp/requirements.txt
COPY airflow/requirements.txt /tmp/airflow-requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/requirements.txt \
    -r /tmp/airflow-requirements.txt

# Bake in project code so the image works without volume mounts in production.
# In local dev, docker-compose mounts override these copies at runtime.
COPY --chown=airflow:root scrapers/     /opt/airflow/scrapers/
COPY --chown=airflow:root scrapy.cfg    /opt/airflow/scrapy.cfg
COPY --chown=airflow:root bigtable/     /opt/airflow/bigtable/
COPY --chown=airflow:root dbt_project/  /opt/airflow/dbt_project/
COPY --chown=airflow:root airflow/dags/ /opt/airflow/dags/
