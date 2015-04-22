# -*- coding: utf8 -*-
from . import db
from flask.ext.security import login_required, roles_accepted,\
        roles_required
from datetime import datetime
from flask import abort
from ..utils import HistoryMixin, AsDictMixin


status_enum_list = [ 'emitted', 'received',
    'sent_to_operator', 'received_by_operator',
    'received_by_taxi', 'accepted_by_taxi',
    'declined_by_taxi', 'incident_customer',
    'incident_taxi', 'timeout_customer', 'timeout_taxi',
        'outdated_customer', 'outdated_taxi']#This may be redundant

class Customer(db.Model, AsDictMixin, HistoryMixin):
    id = db.Column(db.String, primary_key=True)
    operateur_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                             primary_key=True)
    nb_sanctions = db.Column(db.Integer, default=0)

class Hail(db.Model, AsDictMixin, HistoryMixin):
    id = db.Column(db.Integer, primary_key=True)
    creation_datetime = db.Column(db.DateTime, nullable=False)
    operateur_id = db.Column(db.Integer)
    customer_id = db.Column(db.String,
                            nullable=False)
    customer_lon = db.Column(db.Float, nullable=False)
    customer_lat = db.Column(db.Float, nullable=False)
    taxi_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(*status_enum_list,
        name='hail_status'), default='emitted', nullable=False)
    last_status_change = db.Column(db.DateTime)
    db.ForeignKeyConstraint(['operateur_id', 'customer_id'],
        ['customer.operateur_id', 'customer.id'])


    def status_changed(self):
        self.last_status_change = datetime.now().isoformat()

    def check_last_status(self, status_required):
        if self.status != status_required:
            abort(500)

    @login_required
    @roles_required('moteur')
    def received(self):
        self.status = 'received'
        self.status_changed()

    def sent_to_operator(self):
        self.status_required('received')
        self.status = 'sent_to_operator'
        self.status_changed()

    def received_by_operator(self):
        self.status_required('sent_to_operator')
        self.status = 'received_by_operator'
        self.status_changed()

    @login_required
    @roles_required('operateur')
    def received_by_taxi(self):
        self.status_required('received_by_operator')
        self.status = 'received_by_taxi'
        self.status_changed()

    @login_required
    @roles_required('operateur')
    def accepted_by_taxi(self):
        self.status_required('received_by_taxi')
        self.status = 'accepted_by_taxi'
        self.status_changed()

    @login_required
    @roles_required('operateur')
    def declined_by_taxi(self):
        self.status_required('received_by_taxi')
        self.status = 'declined_by_taxi'
        self.status_changed()

    @login_required
    @roles_required('operateur')
    def incident_taxi(self):
        self.status = 'incident_taxi'
        self.status_changed()

    @login_required
    @roles_required('moteur')
    def incident_customer(self):
        self.status = 'incident_customer'
        self.status_changed()

    def check_time_out(self):
        pass

    def to_dict(self):
        self.check_time_out()
        return self.as_dict()
