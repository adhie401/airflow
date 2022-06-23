import json
import os
import random
from time import sleep

from flask import Flask, request, Response
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s: %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello!"

@app.route("/execute_job", methods=['POST'])
def job():
    if request.method == 'POST':
        _id = None
        try:
            data = request.form
            _id = data.get('_id')
            if _id is not None:
                logging.info(f"Running job with related id job {_id}")
            else:
                logging.info(f"Running job without id job")
            
            logging.info("Running calculation job")
            sleep(random.randint(100, 180))
            logging.info("Successfully run a calculation job")
            return Response(
                response=json.dumps({
                    'job_id': _id,
                    'status': 'success',
                    'message': 'Calculate job successfully run!'
                }),
                status=200,
                mimetype='application/json'
            )
        except Exception as e:
            return Response(
                response=json.dumps({
                    'job_id': _id,
                    'status': 'error',
                    'message': (
                        'Error during performing calculation job.'
                        f' Error message: {e}'
                    )
                }),
                status=408,
                mimetype='application/json'
            )
    else:
        return Response(
            response=json.dumps({
                'job_id': None,
                'status': 'error',
                'message': "Forbidden. Method not allowed"
            })
        )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
