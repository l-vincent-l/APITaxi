#coding: utf-8
from flask import current_app
from ..models.hail import Hail
from ..descriptors.hail import hail_model
from ..extensions import db
import celery, requests, json

@celery.task
def send_request_operator(hail_id, operator):
    hail = Hail.query.get(hail_id)
    try:
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        if operateur.operator_header_name is not None and operateur.operator_header_name != '':
            headers[operateur.operator_header_name] = operateur.operator_api_key
        r = requests.post(operateur.hail_endpoint,
                data=json.dumps(marshal({"data": [hail]}, hail_model)),
            headers=headers)
    except requests.exceptions.MissingSchema:
        pass
    if not r or r.status_code < 200 or r.status_code >= 300:
        current_app.error("Unable to reach hail's endpoint {} of operator {}"\
            .format(operateur.hail_endpoint, operateur.email))
        hail.status = 'failure'
        db.session.commit()
        return
    r_json = None
    try:
        r_json = r.json()
    except ValueError:
        pass

    if r_json and 'data' in r_json and len(r_json['data']) == 1\
            and 'taxi_phone_number' in r_json['data'][0]:
        hail.taxi_phone_number = r_json['data'][0]['taxi_phone_number']

    hail.status = 'received_by_operator'
    db.session.commit()
