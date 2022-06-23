import pendulum
from datetime import timedelta
from airflow.models import Variable


start_date = Variable.get("START_DATE")
end_date = Variable.get("END_DATE", None)
tz = Variable.get("START_END_DATE_TIMEZONE")

if end_date is not None:
    end_date = pendulum.from_format(
        end_date,
        fmt='YYYY-MM-DD HH:mm:ss',
        tz=tz
    )

default_dag_args = {
    "start_date": pendulum.from_format(
        start_date,
        fmt='YYYY-MM-DD HH:mm:ss',
        tz=tz
    ),
    "end_date": end_date,
    "max_active_runs": 5,
    'dagrun_timeout': timedelta(minutes=10),
}

default_task_args = {
    "owner": "mis.stf08",
    'depends_on_past': False,
    'email': Variable.get('MAIN_NOTIF_TARGET_MAIL', "").split(","),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    "sla": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=7)
}
