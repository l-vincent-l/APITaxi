# -*- coding: utf-8 -*-
from .skeleton import Skeleton
from .fake_data import dict_driver, dict_vehicle, dict_ads, dict_taxi
from APITaxi_models import Driver
from json import dumps, loads
from copy import deepcopy
from io import BytesIO

class TestDriverPost(Skeleton):
    url = '/drivers/'
    role = 'operateur'


    def test_null(self):
        r = self.post([])
        self.assert201(r)

    def test_simple(self):
        self.init_dep()
        dict_ = deepcopy(dict_driver)
        r = self.post([dict_])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], dict_)
        self.assertEqual(len(Driver.query.all()), 1)

    def test_no_data(self):
        self.init_dep()
        r = self.post({}, envelope_data=False)
        self.assert400(r)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_too_many_drivers(self):
        self.init_dep()
        r = self.post([dict_driver for x in range(0, 251)])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_no_departement(self):
        r = self.post([dict_driver])
        self.assert404(r)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_pas_de_nom(self):
        dict_ = deepcopy(dict_driver)
        del dict_['first_name']
        r = self.post([dict_])
        self.assert400(r)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_bad_date(self):
        self.init_dep()
        dict_ = deepcopy(dict_driver)
        dict_['birth_date'] = 'bad'
        r = self.post([dict_])
        self.assert400(r)

    def test_no_date(self):
        self.init_dep()
        dict_ = deepcopy(dict_driver)
        del dict_['birth_date']
        r = self.post([dict_])
        self.assert201(r)

    def test_two_inserts(self):
        self.init_dep()
        r = self.post([dict_driver for x in range(0, 2)])
        self.assert201(r)
        self.assertEqual(len(Driver.query.all()), 1)

    def test_post_file(self):
        r = self.post(dict(file=(BytesIO(b'test file'), 'test.csv'),),
                content_type=None, envelope_data=False, accept='text/html')
        self.assert200(r)

    def test_post_after_taxi_post(self):
        self.init_zupc()
        self.init_dep()
        dict_ = deepcopy(dict_driver)
        r = self.post([dict_])
        self.assert201(r)
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        r = self.post([dict_taxi], url='/taxis/')
        self.assert201(r)

        dict_ = deepcopy(dict_driver)
        r = self.post([dict_])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], dict_)
        self.assertEqual(len(Driver.query.all()), 1)

    def test_datetime(self):
        self.init_dep()
        dict_ = deepcopy(dict_driver)
        dict_['birth_date'] = '1962-07-26T00:00:00'
        r = self.post([dict_])
        self.assert201(r)
        dict_['birth_date'] = '1962-07-26' #postgres cuts the time
        self.check_req_vs_dict(r.json['data'][0], dict_)
        self.assertEqual(len(Driver.query.all()), 1)

    def test_departement(self):
        self.init_dep()
        dict_ = deepcopy(dict_driver)
        dict_['departement']['nom'] = 'MAYENNE'
        r = self.post([dict_])
        self.assert201(r)
        dict_['departement']['nom'] = 'MAYENNE'.capitalize()
        self.check_req_vs_dict(r.json['data'][0], dict_)
        self.assertEqual(len(Driver.query.all()), 1)
