# The DAG object; we'll need this to instantiate a DAG
from datetime import timedelta, datetime
import json
import os
from time import sleep
from airflow import DAG, XComArg
from airflow.models.variable import Variable
import pytz
# from lnk.common.sql import MSSQLToPostgresTransfer
from lnk import default_dag_args, default_task_args
from airflow.decorators import task
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.operators.python import PythonOperator
from airflow.models.taskinstance import TaskInstance
from lnk.common.cloud_run import invoke_https_cloud_run


TABLE_PREFIX = f"{ Variable.get('ENVIRONMENT_PREFIX', '') }" + '_'
if TABLE_PREFIX in ("prod_", '_'):
    TABLE_PREFIX = ""

DEFAULT_TIMEZONE_IANA = Variable.get('START_END_DATE_TIMEZONE', 'UTC')
COIN_INVOKE_URL = Variable.get('COIN_INVOKE_URL')
JOBS_COLLECTION = Variable.get('JOBS_COLLECTION')


@task
def mongo_sense_collection(
    mongo_conn_id: str,
    collection: str,
    query: str = {},
    sort: str = {},
    **context
):
    from pymongo.collection import Collection
    from airflow.models.taskinstance import TaskInstance
    from airflow.providers.mongo.sensors.mongo import MongoHook
    from datetime import datetime

    # Load MongoDB connection hook
    hook = MongoHook(conn_id=mongo_conn_id)
    schema = hook.connection.schema
    ti: TaskInstance = context['ti']

    # Get MongoDB collection as a pandas DataFrame
    print(f'Getting {collection} collection from {schema} database')
    coll_obj: Collection = hook.get_collection(collection, schema)

    for _, value in query.items():
        if type(value) == dict:
            for key_2 in value.keys():
                if key_2 in ('$gt', '$gte', '$lt', '$lte'):
                    try:
                        value[key_2] = datetime.strptime(
                            value[key_2],
                            '%Y-%m-%dT%H:%M:%S%z'
                        )
                    except Exception:
                        value[key_2] = datetime.strptime(
                            value[key_2],
                            '%Y-%m-%dT%H:%M:%S.%f%z'
                        )
                    print(
                        f"Converted {key_2} to datetime. "
                        f"Converted value: {value[key_2]}"
                    )

    cursor = coll_obj.find(query)

    if sort:
        cursor = cursor.sort(sort)
    
    i = 0
    list_cursor = []
    for x in cursor:
        list_cursor.append(
            {
                **x,
                'index': 0,
                "_id": str(x["_id"])
            }
        )
        i+=1
    list_cursor = [
        {
            **x,
            'length_mapped_instance': len(list_cursor)
        }
        for x in list_cursor
    ]
    ti.xcom_push('_id', [x['_id'] for x in list_cursor])
    ti.xcom_push('app', [x['app'] for x in list_cursor])
    ti.xcom_push('created_at', [x['created_at'] for x in list_cursor])
    return list_cursor


@task
def trigger_cloud_run_dag(
    kwargs,
    **context
):
    ti: TaskInstance = context['ti']
    for kwarg in ('_id', 'app', 'created_at'):
        if kwarg not in kwargs.keys():
            raise Exception(f"Error kwarg: {kwarg} is required")

    index, _id, app, created_at, length = (
        kwargs['index'],
        kwargs['_id'],
        kwargs['app'],
        kwargs['created_at'],
        kwargs['length_mapped_instance']
    )

    delay_before_scheduling = float(index)/float(length)

    sleep(delay_before_scheduling)

    TriggerDagRunOperator(
        task_id='trigger_task',
        trigger_dag_id=f"trigger-cloud-run-app-{app}",
        conf={"_id": _id},
        wait_for_completion=False,
        execution_date=pytz.utc.localize(created_at),
        reset_dag_run=True
    ).execute(context=context)

    pass


cloud_run_default_dag_args = {
    **default_dag_args,
    "max_active_runs": 1,
}

cloud_run_default_task_args = {
    **default_task_args,
    "depends_on_past": True,
    "sla": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=7)
}

with DAG(
    "trigger-cloud-run-app-coin",
    description="Airflow DAG that run project coin calculation",
    default_args=cloud_run_default_task_args,
    schedule_interval=None,
    tags=['coin', 'cloud-run'],
    **cloud_run_default_dag_args
) as coin_dag:
    task = invoke_https_cloud_run(
        url=COIN_INVOKE_URL,
        params={
            "_id": (
                "{{"
                "   dag_run.conf['_id']"
                "   if dag_run and '_id' in dag_run.conf.keys()"
                "    else ''"
                "}}"
            ),
        },
        gcp_conn_id='gcp_service_account',
        airflow_token=Variable.get('AIRFLOW_TOKEN', None),
    )


with DAG(
    "airflow-sensor-mongodb",
    description="""
        Airflow DAG that fetch a pending
        job from MongoDB collection: `cloud_run_jobs`
    """,
    default_args=dict(default_task_args, **{"sla": None, "retries": 1}),
    schedule_interval='*/5 * * * *',
    tags=['sensor'],
    **default_dag_args
) as sensor_dag:

    task = mongo_sense_collection(
        mongo_conn_id='coin_mongo_db',
        collection=JOBS_COLLECTION,
        query={
            "created_at": {
                "$gte": '{{ data_interval_start }}',
                "$lt": '{{ data_interval_end }}'
            },
            "status": "scheduled"
        }
    )

    trigger_cloud_run_dag.partial(max_active_tis_per_dag=1).expand(kwargs=task)
