FROM apache/airflow:2.3.0-python3.8
USER root

ENV TZ=Asia/Jakarta
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

USER airflow

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY dags/ /opt/airflow/dags
