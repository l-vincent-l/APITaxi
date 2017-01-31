# -*- coding: utf-8 -*-
from APITaxi_utils.resource_metadata import ResourceMetadata
from APITaxi_utils.request_wants_json import request_wants_json
from APITaxi_utils.populate_obj import create_obj_from_json
from APITaxi_utils.reqparse import DataJSONParser
from APITaxi_utils.resource_file_or_json import ResourceFileOrJSON
import APITaxi_models as models
from flask_security import login_required, roles_accepted, current_user
from . import api, ns_administrative
from ..descriptors.ads import ads_model, ads_expect, ads_post
from flask_restplus import reqparse, abort, marshal
from flask import jsonify, request, current_app
from .extensions import documents
from APITaxi_utils.slack import slack as slacker
from datetime import datetime

parser = reqparse.RequestParser()
parser.add_argument('numero', type=unicode, help=u"Numero de l'ADS", required=False,
                    location='values')
parser.add_argument('insee', type=unicode,
        help=u"Code INSEE de la commune d\'attribution de l'ADS", required=False,
                    location='values')

@ns_administrative.route('ads/', endpoint="ads")
class ADS(ResourceMetadata, ResourceFileOrJSON):
    model = models.ADS
    filetype = 'ADS'
    documents = documents

    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture', 'stats')
    @api.hide
    @api.doc(parser=parser, responses={200: ('ADS', ads_model)})
    def get(self):
        args = parser.parse_args()
        if not args["numero"] or not args["insee"]:
            abort(400, message="Message and insee field are required")
        filters = {
                "numero": str(numero),
                "insee": str(insee)
                }
        ads = models.ADS.query.filter_by(**filters).all()
        if not ads:
            abort(404, error="Unable to find this couple INSEE/numero")
        ads = ads[0]
        d = models.ADS.__dict__
        keys_to_show = ads.showable_fields(current_user)
        is_valid_key = lambda k: hasattr(k, "info") and k.info.has_key("label")\
                                 and k.info['label'] and k.key in keys_to_show
        return jsonify({(k[0],
                getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])})


    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.expect(ads_expect)
    @api.response(200, 'Success', ads_post)
    def post(self):
        return super(ADS, self).post()

    def post_json(self):
        data_parser = DataJSONParser(max_length=250)
        new_ads = []
        db = current_app.extensions['sqlalchemy'].db
        for ads in data_parser.get_data():
            if not ads.get('vehicle_id', None) or ads['vehicle_id'] == 0:
                ads['vehicle_id'] = None
            if ads['vehicle_id'] and\
              not models.Vehicle.query.get(ads['vehicle_id']):
                abort(400, message="Unable to find a vehicle with the id: {}"\
                        .format(ads['vehicle_id']))
            ads_db = create_obj_from_json(models.ADS, ads)
            zupc = models.ZUPC.query.filter_by(insee=ads_db.insee).first()
            if zupc is None:
                abort(400, message="Unable to find a ZUPC for insee: {}".format(
                    ads_db.insee))
            ads_db.zupc_id = zupc.parent_id
            db.session.add(ads_db)
            new_ads.append(ads_db)
        db.session.commit()
        for ads in new_ads:
            cur = db.session.connection().connection.cursor()
            cur.execute("""
                UPDATE taxi set ads_id = %s WHERE ads_id IN (
                    SELECT id FROM "ADS"  WHERE numero = %s
                    AND insee = %s
                )""",
                (ads.id, ads.numero, ads.insee)
            )
        db.session.commit()
        return marshal({"data": new_ads}, ads_post), 201
