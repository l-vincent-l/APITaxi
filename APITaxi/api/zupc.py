# -*- coding: utf-8 -*-
from . import api, ns_administrative
from APITaxi_utils.resource_metadata import ResourceMetadata
from APITaxi_utils.request_wants_json import request_wants_json
from flask_restplus import reqparse, abort, marshal
from flask import current_app
from werkzeug.exceptions import BadRequest
import json
from psycopg2.extras import RealDictCursor
import APITaxi_models as models

@ns_administrative.route('zupc/')
class ZUPC(ResourceMetadata):
    def get(self):
        if not request_wants_json():
            abort(400, message="request needs JSON")
        parser = reqparse.RequestParser()
        parser.add_argument('lon', type=float, required=True, location='args')
        parser.add_argument('lat', type=float, required=True, location='args')
        try:
            args = parser.parse_args()
        except BadRequest as e:
            return json.dumps(e.data), 400, {"Content-Type": "application/json"}

        cur = current_app.extensions['sqlalchemy'].db.session.connection()\
                .connection.cursor(cursor_factory=RealDictCursor)
        cur.execute("""SELECT active, nom, insee FROM "ZUPC"
            WHERE ST_Intersects(shape, ST_POINT(%s, %s)::geography)""",
            (args['lon'], args['lat']))
        to_return = []
        ZUPC = models.ZUPC
        for zupc in cur.fetchall():
            if any(map(lambda z: zupc['insee'] == z['insee'], to_return)):
                continue
            to_return.append(marshal(zupc, ZUPC.marshall_obj(filter_id=True,
                level=1, api=api)))
        return {"data": to_return}, 200


@ns_administrative.route('/zupc/autocomplete')
@api.hide
class ZUPCAutocomplete(ResourceMetadata):
    def get(self):
        #@TODO: have some identification here?
        term = request.args.get('q')
        like = "%{}%".format(term)

        response = models.ZUPC.query.filter(
                models.ZUPC.nom.ilike(like)).all()
        return jsonify(suggestions=map(lambda zupc:{'name': zupc.nom, 'id': int(zupc.id)},
                                            response))

@ns_administrative.route('zupc/<int:zupc_id>/_show_temp_geojson')
@api.hide
class ZUPCShowTemp(ResourceMetadata):
    def get(self, zupc_id):
        cur = current_app.extensions['sqlalchemy'].db.session.connection()\
                .connection.cursor()
        cur.execute('SELECT ST_AsGeoJSON(shape) FROM "zupc_temp" WHERE id = %s;',
                (zupc_id,)
        )
        geojson = cur.fetchall()
        if not geojson:
            return {"data": None}
        else:
            return {"data": json.loads(geojson[0][0])}

