import tempfile
import requests
from airflow.decorators import task
from airflow.models.taskinstance import TaskInstance
from airflow.providers.google.common.hooks.base_google import GoogleBaseHook
# from oauth2client import service_account
from google.oauth2.service_account import IDTokenCredentials
import google.auth.transport.requests


@task
def invoke_https_cloud_run(
    url: str,
    params: dict,
    gcp_conn_id: str = 'gcp_default',
    airflow_token: str = None,
    **context
):
    """
    Invoke a cloud run service to run a task.

    Args:
        url (str): The url of the cloud run service.
        params (dict): The parameters to pass to the cloud run service.
        gcp_conn_id (str): The connection id of the GCP connection.

    Returns:
        dict: The response from the cloud run service.
    """
    ti: TaskInstance = context['ti']
    keyfile_dict = GoogleBaseHook(gcp_conn_id=gcp_conn_id)\
        ._get_field('keyfile_dict', None)

    conf_file = tempfile.NamedTemporaryFile(mode='w+t')
    conf_file.write(keyfile_dict)
    conf_file.flush()

    credentials = IDTokenCredentials.from_service_account_file(
        conf_file.name,
        target_audience=url
    )

    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    access_token = credentials.token

    conf_file.close()
    print(f'Invoking {url} with params {params}')
    resp: requests.Response = requests.get(
        url,
        params=params,
        headers={
            'Authorization': 'Bearer {}'.format(access_token),
            'X-AIRFLOW-TOKEN': airflow_token
        }
    )

    ti.xcom_push('response_json', resp.json())
    ti.xcom_push('response_status_code', resp.status_code)
    ti.xcom_push('response_headers', resp.headers)
    ti.xcom_push('response_raw', str(resp.raw))

    if resp.status_code != 200:
        raise Exception(
            'Failed to invoke cloud run service. '
            'Status code: {}. '
            'Response: {}'
            'Check XCom for more details.'.format(resp.status_code, resp.text)
        )

    print("Successfully invoked a cloud run service. "
          "Check XCom tab in Airflow for more details.")

    return True
