# -*- coding: utf-8 -*-
from flask import request, redirect, url_for, current_app, g
from flask.ext.restplus import Resource, reqparse, fields, abort, marshal
from flask.ext.security import (login_required, roles_required,
        roles_accepted, current_user)
from ..extensions import db, redis_store
from ..api import api
from ..models.hail import Hail as HailModel, Customer as CustomerModel
from ..models.taxis import  Taxi as TaxiModel
from ..models import security as security_models
import requests, json
from ..descriptors.hail import hail_model
from ..utils.request_wants_json import json_mimetype_required
from ..utils.cache_refresh import cache_refresh
from ..utils import fields as customFields
from ..utils.validate_json import ValidatorMixin

ns_hail = api.namespace('hails', description="Hail API")
argument_names = ['customer_id', 'customer_lon', 'customer_lat',
    'customer_address', 'status']
dict_hail =  dict(filter(lambda f: f[0] in argument_names,
        HailModel.marshall_obj().items()))
for k in dict_hail.keys():
    dict_hail[k].required = False

hail_expect_put_details = api.model('hail_expect_put_details', dict_hail)
hail_expect_put = api.model('hail_expect_put',
        {'data': fields.List(fields.Nested(hail_expect_put_details))})
@ns_hail.route('/<string:hail_id>/', endpoint='hailid')
class HailId(Resource, ValidatorMixin):
    list_fields = ['status', 'incident_taxi_reason',
        'reporting_customer', 'reporting_customer_reason', 'customer_lon',
        'customer_lat', 'customer_address', 'customer_phone_number', 'rating_ride',
        'rating_ride_reason', 'incident_customer_reason']
    model = hail_expect_put

    @classmethod
    def filter_access(cls, hail):
        if not current_user.id in (hail.operateur_id, hail.added_by) and\
                not current_user.has_role('admin'):
            abort(403, message="You don't have the authorization to view this hail")


    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    @api.marshal_with(hail_model)
    @json_mimetype_required
    def get(self, hail_id):
        hail = HailModel.get(hail_id)
        if not hail:
            abort(404, message="Unable to find hail: {}".format(hail_id))
        self.filter_access(hail)
        return {"data": [hail]}

    @login_required
    @roles_accepted('admin', 'moteur', 'operateur')
    @api.marshal_with(hail_model)
    @api.expect(hail_expect_put)
    @json_mimetype_required
    def put(self, hail_id):
        hail = HailModel.query.get_or_404(hail_id)
        self.filter_access(hail)
        if hail.status.startswith("timeout"):
            return {"data": [hail]}
        hj = request.json
        self.validate(hj)
        hj = hj['data'][0]

        #We change the status
        if hj['status'] == 'accepted_by_taxi':
            if g.version == 1:
                hail.taxi_phone_number = ''
            elif g.version == 2:
                if not 'taxi_phone_number' in hj or hj['taxi_phone_number'] == '':
                    abort(400, message='Taxi phone number is needed')
                else:
                    hail.taxi_phone_number = hj['taxi_phone_number']
        for ev in self.list_fields:
            value = hj.get(ev, None)
            if value is None:
                continue
            try:
                setattr(hail, ev, value)
            except AssertionError, e:
                abort(400, message=e.args[0])
            except RuntimeError, e:
                abort(403)
            except ValueError, e:
                abort(400, e.args[0])
        cache_refresh(db.session(),
            {'func': HailModel.get.refresh, 'args': [HailModel, hail_id]},
            {'func': TaxiModel.getter_db.refresh, 'args': [TaxiModel, hail.taxi_id]},
        )
        db.session.commit()
        return {"data": [hail]}


argument_names = ['customer_id', 'customer_lon', 'customer_lat',
    'customer_address', 'customer_phone_number', 'taxi_id', 'operateur']
dict_hail =  dict(filter(lambda f: f[0] in argument_names,
        HailModel.marshall_obj().items()))
dict_hail['operateur'] = fields.String(attribute='operateur.email', required=True)
dict_hail['taxi_id'] = fields.String(required=True)
hail_expect_post_details = api.model('hail_expect_post_details', dict_hail)
hail_expect = api.model('hail_expect_post',
        {'data': customFields.List(fields.Nested(hail_expect_post_details))})
@ns_hail.route('/', endpoint='hail_endpoint')
class Hail(Resource, ValidatorMixin):
    model = hail_expect

    @login_required
    @roles_accepted('admin', 'moteur')
    @api.marshal_with(hail_model)
    @api.expect(hail_expect)
    @json_mimetype_required
    def post(self):
        hj = request.json
        self.validate(hj)
        hj = hj['data'][0]

        taxi = TaxiModel.query.get(hj['taxi_id'])
        if not taxi:
            return abort(404, message="Unable to find taxi")
        operateur = security_models.User.filter_by_or_404(
                email=hj['operateur'], message='Unable to find the taxi\'s operateur')
        desc = taxi.vehicle.get_description(operateur)
        if not desc:
            abort(404, message='Unable to find taxi\'s description')
        if not taxi.is_free() or not taxi.is_fresh(hj['operateur']):
            abort(403, message="The taxi is not available")
        customer = CustomerModel.query.filter_by(id=hj['customer_id'],
                operateur_id=current_user.id).first()
        if not customer:
            customer = CustomerModel(hj['customer_id'])
            db.session.add(customer)
        hail = HailModel()
        hail.customer_id = hj['customer_id']
        hail.customer_lon = hj['customer_lon']
        hail.customer_lat = hj['customer_lat']
        hail.customer_address = hj['customer_address']
        hail.customer_phone_number = hj['customer_phone_number']
        hail.taxi_id = hj['taxi_id']
        hail.operateur_id = operateur.id
        db.session.add(hail)
        db.session.commit()
        hail.status = 'emitted'
        hail.status = 'received'
        hail.status = 'sent_to_operator'
        db.session.commit()
        r = None

        def finish_and_abort(message):
            current_app.logger.info(message)
            hail.status  = 'failure'
            db.session.commit()
            return {"data": [hail]}, 201

        try:
            headers = {'Content-Type': 'application/json'}
            if operateur.operator_header_name is not None and operateur.operator_header_name != '':
                headers[operateur.operator_header_name] = operateur.operator_api_key
            r = requests.post(operateur.hail_endpoint,
                    data=json.dumps(marshal({"data": [hail]}, hail_model)),
                headers=headers)
        except requests.exceptions.MissingSchema:
            pass
        if not r or r.status_code < 200 or r.status_code >= 300:
            return finish_and_abort("Unable to reach hail's endpoint {} of operator {}"\
                    .format(operateur.hail_endpoint, operateur.email))
        r_json = None
        try:
            r_json = r.json()
        except ValueError:
            pass
            #return finish_and_abort('Response from endpoint doesn\'t contain json')

        if r_json and 'data' not in r_json or len(r_json['data']) != 1:
            pass
            #return finish_and_abort('Response is mal formated')
        else:
            if 'taxi_phone_number' in r_json['data'][0]:
                hail.taxi_phone_number = r_json['data'][0]['taxi_phone_number']

        hail.status = 'received_by_operator'
        db.session.commit()
        return {"data": [hail]}, 201
