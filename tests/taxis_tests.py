from .skeleton import Skeleton
import APITaxi_models as models
from json import dumps, loads
from copy import deepcopy
from .fake_data import dict_vehicle, dict_ads, dict_driver, dict_taxi
from APITaxi.extensions import redis_store
import time
from datetime import datetime, timedelta
from flask import current_app

class TaxiGet(Skeleton):
    url = '/taxis/'

    def add(self, lat=2.3, lon=48.7, float_=False, post_second=False, custom_ads=None):
        self.init_zupc()
        self.init_dep()
        taxi = self.post_taxi_and_locate(lat=lat, lon=lon, float_=float_,
                post_second=post_second, custom_ads=custom_ads)
        id_taxi = taxi['id']
        taxi_db = models.Taxi.query.get(id_taxi)
        taxi_db.set_free()
        current_app.extensions['sqlalchemy'].db.session.commit()
        return id_taxi


class TestTaxiGet(TaxiGet):
    role = 'operateur'

    def test_get_taxi(self):
        id_taxi = self.add()
        r = self.get('/taxis/{}/'.format(id_taxi))
        self.assert200(r)
        assert(len(r.json['data']) == 1)
        assert('nb_seats' in r.json['data'][0]['vehicle'])
        assert('rating' in r.json['data'][0])
        assert(isinstance(r.json['data'][0]['rating'], float))
        assert(isinstance(r.json['data'][0]['last_update'], int))

    def test_get_taxi_other_op(self):
        id_taxi = self.add()
        r = self.get('/taxis/{}/'.format(id_taxi), user='user_operateur_2')
        self.assert403(r)


class TestTaxisGet(TaxiGet):
    role = 'moteur'

    def test_get_taxis_lonlat(self):
        self.add()
        r = self.get('/taxis/?lat=2.3&lon=48.7')
        self.assert200(r)
        assert len(r.json['data']) == 1
        taxi = r.json['data'][0]
        for key in ['id', 'operator', 'position', 'vehicle', 'last_update',
                'crowfly_distance', 'ads', 'driver', 'rating']:
            assert key in taxi.keys()
            assert taxi[key] is not None
        for key in ['insee', 'numero']:
            assert key in taxi['ads']
            assert taxi['ads'][key] is not None
        for key in ['departement', 'professional_licence']:
            assert key in taxi['driver']
            assert taxi['driver'][key] is not None
        for key in ['characteristics', 'color', 'licence_plate', 'model',
                    'nb_seats', 'type', 'cpam_conventionne']:
            assert taxi['vehicle'][key] is not None

    def test_get_taxis_lonlat_favorite_operator(self):
        self.add()
        r = self.get('/taxis/?lat=2.3&lon=48.7&favorite_operator=user_operateur')
        self.assert200(r)
        assert len(r.json['data']) == 1
        taxi = r.json['data'][0]
        for key in ['id', 'operator', 'position', 'vehicle', 'last_update',
                'crowfly_distance', 'ads', 'driver', 'rating']:
            assert key in taxi.keys()
            assert taxi[key] is not None
        for key in ['insee', 'numero']:
            assert key in taxi['ads']
            assert taxi['ads'][key] is not None
        for key in ['departement', 'professional_licence']:
            assert key in taxi['driver']
            assert taxi['driver'][key] is not None
        for key in ['characteristics', 'color', 'licence_plate', 'model',
                    'nb_seats', 'type', 'cpam_conventionne']:
            assert taxi['vehicle'][key] is not None

    def test_get_taxis_limited_zone(self):
        from flask import current_app
        from APITaxi.extensions import redis_store
        from shapely.geometry import Polygon
        current_app.config['LIMITED_ZONE'] = Polygon([
            (43.7, 3.7), (43.7, 4.4), (43.4, 4.4), (43.4, 3.7)])
#One in Paris
        self.add()
#One in Montpellier
        self.add(3.8, 43.6, post_second=True)
        r = self.get('/taxis/?lat=2.1&lon=48.5')
        self.assert200(r)
        assert len(r.json['data']) == 0
        r = self.get('/taxis/?lat=3.8&lon=43.6')
        self.assert200(r)
        assert len(r.json['data']) == 1
        current_app.config['LIMITED_ZONE'] = None

    def test_get_taxis_lonlat_timestamp_float(self):
        self.add(float_=True)
        r = self.get('/taxis/?lat=2.3&lon=48.7')
        self.assert200(r)
        assert len(r.json['data']) == 1
        taxi = r.json['data'][0]
        for key in ['id', 'operator', 'position', 'vehicle', 'last_update',
                'crowfly_distance', 'ads', 'driver', 'rating', 'status']:
            assert key in taxi.keys()
            assert taxi[key] is not None
        for key in ['insee', 'numero']:
            assert key in taxi['ads']
            assert taxi['ads'][key] is not None
        for key in ['departement', 'professional_licence']:
            assert key in taxi['driver']
            assert taxi['driver'][key] is not None
        for key in ['model', 'constructor', 'color', 'licence_plate',
                'characteristics', 'nb_seats']:
            assert key in taxi['vehicle']
            assert taxi['vehicle'][key] is not None

    def test_get_taxi_out_of_zupc(self):
        self.add(1, 1)
        r = self.get('/taxis/?lat=2.2&lon=48.7')
        self.assert200(r)
        assert len(r.json['data']) == 0

    def test_sorted_taxi(self):
        #Add a taxi at 1.1 kmeters from 29 rue de Meaux
        id_closer_taxi = self.add(2.370483, 48.870767)
        #Add a taxi at 10 kmeters
        custom_ads = deepcopy(dict_ads)
        custom_ads["numero"] = "2"
        id_farer_taxi = self.add(2.29344, 48.835864,
                custom_ads=custom_ads)
        r = self.get('/taxis/?lat=2.372027635574341&lon=48.87979158428683')
        self.assert200(r)
        assert len(r.json['data']) == 2
        assert r.json['data'][0]['id'] == id_closer_taxi
        assert r.json['data'][1]['id'] == id_farer_taxi

    def test_one_taxi_one_desc(self):
        pass

    def test_two_taxis_one_desc(self):
        pass

    def test_one_taxi_out_of_the_scope(self):
        pass

    def test_one_taxi_timeout(self):
        pass

    def test_one_taxi_two_desc_ok(self):
        pass

    def test_one_taxi_two_desc_one_non_free(self):
        self.add()
        id_taxi = self.post_taxi_and_locate(user='user_operateur_2', lat=2.3, lon=48.7)['id']
        r = self.put([{"status": "off"}], '/taxis/{}/'.format(id_taxi),
                user='user_operateur_2', role='operateur')
        self.assert200(r)
        r = self.get('/taxis/?lat=2.3&lon=48.7')
        self.assert200(r)
        assert len(r.json['data']) == 0

    def test_one_taxi_two_desc_one_non_free_but_timeout(self):
        self.add()
        id_taxi = self.post_taxi_and_locate(user='user_operateur_2', lat=2.3, lon=48.7)['id']
#This taxi is now not fresh for operateur_2
        redis_store.zadd(current_app.config['REDIS_TIMESTAMPS'],
                **{'{}:user_operateur_2'.format(id_taxi):0.0})
        from APITaxi.tasks import clean_geoindex_timestamps
        clean_geoindex_timestamps()
        r = self.put([{"status": "off"}], '/taxis/{}/'.format(id_taxi),
                user='user_operateur_2', role='operateur')
        self.assert200(r)
        r = self.get('/taxis/?lat=2.3&lon=48.7')
        self.assert200(r)
#So we should have a taxi
        assert len(r.json['data']) == 1

    def test_one_taxi_two_desc_one_non_free_favorite_operator(self):
        first_taxi = self.add()
        id_taxi = self.post_taxi_and_locate(user='user_operateur_2', lat=2.3, lon=48.7)['id']
        assert first_taxi == id_taxi
        r = self.put([{"status": "off"}], '/taxis/{}/'.format(id_taxi),
                user='user_operateur_2', role='operateur')
        self.assert200(r)
        r = self.get('/taxis/?lat=2.3&lon=48.7&favorite_operator=user_operateur_2')
        self.assert200(r)
        assert len(r.json['data']) == 0

    def test_one_taxi_two_desc_one_non_free_favorite_operator_one_no_location(self):
        first_taxi = self.add()
        id_taxi = self.post_taxi(user='user_operateur_2')['id']
        assert first_taxi == id_taxi
        r = self.put([{"status": "off"}], '/taxis/{}/'.format(id_taxi),
                user='user_operateur_2', role='operateur')
        self.assert200(r)
        r = self.get('/taxis/?lat=2.3&lon=48.7&favorite_operator=user_operateur_2')
        self.assert200(r)
        assert len(r.json['data']) == 1
        assert r.json['data'][0]['status'] == 'free'


class TestTaxiPut(Skeleton):
    url = '/taxis/'
    role = 'operateur'

    def post_taxi(self):
        self.init_zupc()
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/')
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')
        r = self.post([dict_taxi])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], dict_taxi)
        self.assertEqual(len(models.Taxi.query.all()), 1)
        self.url = '{}{}/'.format(self.__class__.url, r.json['data'][0]['id'])
        return r.json['data'][0]['id']

    def test_no_data(self):
        self.post_taxi()
        r = self.put({}, self.url, envelope_data=False)
        self.assert400(r)

    def test_no_status(self):
        self.post_taxi()
        r = self.put({'data':[{'nostatus':None}]}, self.url,
                envelope_data=False)
        self.assert400(r)

    def test_too_many(self):
        self.post_taxi()
        r = self.put([{'status': 'free'}, {'status':'free'}], self.url)
        self.assertEqual(r.status_code, 400)

    def good_taxi(self, status):
        id_ = self.post_taxi()
        dict_ = {'status': status}
        r = self.put([dict_], self.url)
        self.assert200(r)
        taxi = r.json['data'][0]
        assert taxi['id'] == id_
        assert taxi['status'] == status
        statuses = [desc.status for desc in models.Taxi.query.get(id_).vehicle.descriptions]
        assert all(map(lambda st: st == status, statuses))
        r = self.get(self.url)
        assert r.json['data'][0]['status'] == status

    def test_good_statuses(self):
        for status in ['free', 'occupied', 'oncoming', 'off']:
            self.good_taxi(status)

    def test_set_answering(self):
        self.post_taxi()
        dict_ = {'status': 'answering'}
        r = self.put([dict_], self.url)
        self.assert400(r)

    def test_bad_user(self):
        self.post_taxi()
        dict_ = {'status': 'free'}
        r = self.put([dict_], self.url, user='user_operateur_2')
        self.assert403(r)

    def test_two_descriptions(self):
        r = self.post([dict_vehicle], url='/vehicles/', user='user_operateur_2')
        id_ = self.post_taxi()
        dict_ = {'status': 'off'}
        r = self.put([dict_], self.url, user='user_operateur_2')
        self.assert200(r)
        statuses = [desc.status for desc in models.Taxi.query.get(id_).vehicle.descriptions]
        assert any(map(lambda st: st == 'free', statuses))
        assert any(map(lambda st: st == 'off', statuses))
        r = self.get(self.url)
        self.assert200(r)
        assert r.json['data'][0]['status'] == 'free'
        r = self.get(self.url, user='user_operateur_2')
        self.assert200(r)
        assert r.json['data'][0]['status'] == 'off'

    def test_taxi_update_ttl(self):
        id_ = self.post_taxi()
        cur = current_app.extensions['sqlalchemy'].db.session.\
                connection().connection.cursor()
        #We are lying, it wasn't updated five hours ago
        cur.execute("UPDATE taxi set last_update_at = %s WHERE id = %s",
                (datetime.now() - timedelta(hours=5), id_)
        )
        current_app.extensions['sqlalchemy'].db.session.commit()
        cur.execute("SELECT last_update_at from taxi where id = %s", (id_,))
        c = cur.fetchall()
        assert (datetime.now() - c[0][0]) > timedelta(hours=4)
        dict_ = {'status': 'free'}
        r = self.put([dict_], self.url)
        self.assert200(r)
        #Oh it was updated more than four hours ago, last_update should
        #be almost now
        cur.execute("SELECT last_update_at from taxi where id = %s", (id_,))
        c = cur.fetchall()
        assert (datetime.now() - c[0][0]) < timedelta(minutes=2)

    def test_taxi_update_empty(self):
        id_ = self.post_taxi()
        cur = current_app.extensions['sqlalchemy'].db.session.\
                connection().connection.cursor()
        #We are setting it to something that shouldn't happen, but does happen
        cur.execute("UPDATE taxi set last_update_at = %s WHERE id = %s",
                (None, id_)
        )
        current_app.extensions['sqlalchemy'].db.session.commit()
        cur.execute("SELECT last_update_at from taxi where id = %s", (id_,))
        c = cur.fetchall()
        assert c[0][0] is None
        dict_ = {'status': 'free'}
        r = self.put([dict_], self.url)
        self.assert200(r)
        #It should be updated no matter what
        cur.execute("SELECT last_update_at from taxi where id = %s", (id_,))
        c = cur.fetchall()
        assert (datetime.now() - c[0][0]) < timedelta(minutes=2)


class TestTaxiPost(Skeleton):
    url = '/taxis/'
    role = 'operateur'

    def init_taxi(self, user='user_operateur', role='operateur'):
        self.init_zupc()
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_vehicle], url='/vehicles/', user=user, role=role)
        self.assert201(r)
        vehicle_id = r.json['data'][0]['id']
        dict_ads_ = deepcopy(dict_ads)
        dict_ads_['vehicle_id'] = vehicle_id
        self.post([dict_ads_], url='/ads/')

    def test_no_data(self):
        r = self.post({}, envelope_data=False)
        self.assert400(r)

    def test_too_many(self):
        r = self.post([{'driver': None, 'ads': None, 'vehicle': None},
            {'driver': None, 'ads': None, 'vehicle': None}])
        self.assertEqual(r.status_code, 400)

    def test_missing_fields(self):
        dict_ = {
            'vehicle': None,
            'driver': {'professional_licence': 'a', 'deparement': '53'}
        }
        r = self.post([dict_])
        self.assert400(r)

    def test_missing_departement_in_db(self):
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_missing_driver_in_db(self):
        self.init_dep()
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_missing_vehicle_in_db(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_missing_ads_in_db(self):
        self.init_dep()
        self.post([dict_driver], url='/drivers/')
        self.post([dict_vehicle], url='/vehicles/')
        r = self.post([dict_taxi])
        self.assert404(r)

    def test_add_taxi(self):
        self.init_taxi()
        r = self.post([dict_taxi])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], dict_taxi)
        self.assertEqual(len(models.Taxi.query.all()), 1)

    def test_add_taxi_with_id_normal_user(self):
        self.init_taxi()
        dict_taxi_ = deepcopy(dict_taxi)
        dict_taxi_['id'] = 'a'
        r = self.post([dict_taxi_])
        self.assert201(r)
        del dict_taxi_['id']
        self.check_req_vs_dict(r.json['data'][0], dict_taxi_)
        self.assertNotEqual(r.json['data'][0]['id'], 'a')
        self.assertEqual(len(models.Taxi.query.all()), 1)

    def test_add_taxi_with_id_int_normal_user(self):
        self.init_taxi()
        dict_taxi_ = deepcopy(dict_taxi)
        dict_taxi_['id'] = 1
        r = self.post([dict_taxi_])
        self.assert201(r)
        del dict_taxi_['id']
        self.check_req_vs_dict(r.json['data'][0], dict_taxi_)
        self.assertNotEqual(r.json['data'][0]['id'], 'a')
        self.assertEqual(len(models.Taxi.query.all()), 1)

    def test_add_taxi_without_adding_vehicle(self):
        self.init_taxi()
        dict_taxi_ = deepcopy(dict_taxi)
        dict_taxi_['id'] = 'a'
        r = self.post([dict_taxi_], user='user_admin', role='admin')
        self.assert404(r)

    def test_add_taxi_with_admin_user(self):
        self.init_taxi(user='user_admin', role='admin')
        dict_taxi_ = deepcopy(dict_taxi)
        dict_taxi_['id'] = 'a'
        r = self.post([dict_taxi_], user='user_admin', role='admin')
        self.assert201(r)
        del dict_taxi_['status']
        self.check_req_vs_dict(r.json['data'][0], dict_taxi_)
        self.assertEqual(r.json['data'][0]['id'], 'a')
        self.assertEqual(len(models.Taxi.query.all()), 1)

    def test_add_taxi_internal(self):
        self.init_taxi()
        d = deepcopy(dict_taxi)
        d['internal_id']= 'INTERNAL_ID'
        r = self.post([d])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], d)
        taxis = models.Taxi.query.all()
        self.assertEqual(len(taxis), 1)
        r = self.get('/taxis/{}/'.format(taxis[0].id))
        self.assertEqual(r.json['data'][0]['internal_id'], 'INTERNAL_ID')
        first_id = r.json['data'][0]['id']

        r = self.post([dict_vehicle], url='/vehicles/',
                     user='user_operateur_2')
        d = deepcopy(dict_taxi)
        d['internal_id']= 'INTERNAL_ID_2'
        r = self.post([d], user='user_operateur_2')
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], d)
        assert r.json['data'][0]['id'] == first_id
        taxis = models.Taxi.query.all()
        self.assertEqual(len(taxis), 1)
        r = self.get('/taxis/{}/'.format(taxis[0].id), user='user_operateur_2')
        self.assertEqual(r.json['data'][0]['internal_id'], 'INTERNAL_ID_2')
        r = self.get('/taxis/{}/'.format(taxis[0].id))
        self.assertEqual(r.json['data'][0]['internal_id'], 'INTERNAL_ID')
        self.assertEqual(len(taxis[0].vehicle.descriptions), 2)
        assert any([d.internal_id == 'INTERNAL_ID' for d in taxis[0].vehicle.descriptions])
        assert any([d.internal_id =='INTERNAL_ID_2' for d in taxis[0].vehicle.descriptions])


    def missing_field(self, field):
        self.init_taxi()
        dict_taxi_d = deepcopy(dict_taxi)
        del dict_taxi_d[field]
        r = self.post([dict_taxi_d])
        self.assert400(r)

    def test_missing_ads_field(self):
        self.missing_field('ads')

    def test_missing_driver_field(self):
        self.missing_field('driver')

    def test_missing_vehicle_field(self):
        self.missing_field('vehicle')

    def inexistent_field(self, field, sub_field, value):
        self.init_taxi()
        dict_taxi_d = deepcopy(dict_taxi)
        dict_taxi_d[field][sub_field] = value
        r = self.post([dict_taxi_d])
        self.assert404(r)

    def test_bad_ads_field(self):
        self.inexistent_field('ads', 'numero', '2')

    def test_bad_driver_field(self):
        self.inexistent_field('driver', 'professional_licence', 'bad')

    def test_bad_vehicle_field(self):
        self.inexistent_field('vehicle', 'licence_plate', 'bad')

    def test_bad_status(self):
        self.init_taxi()
        dict_ = deepcopy(dict_taxi)
        dict_['status'] = 'string'
        r = self.post([dict_])
        self.assert400(r)
        assert('failed' in r.json['message'])

    def test_add_taxi_twice(self):
        self.init_taxi()
        r = self.post([dict_taxi])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], dict_taxi)
        self.assertEqual(len(models.Taxi.query.all()), 1)
        r = self.post([dict_taxi])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], dict_taxi)
        self.assertEqual(len(models.Taxi.query.all()), 1)

    def test_add_taxi_change_vehicle_description(self):
        self.init_taxi()
        r = self.post([dict_taxi])
        self.assert201(r)
        self.check_req_vs_dict(r.json['data'][0], dict_taxi)
        self.assertEqual(len(models.Taxi.query.all()), 1)
        taxi_id = r.json['data'][0]['id']
        dict_v = deepcopy(dict_vehicle)
        dict_v['color'] = 'red'
        self.post([dict_v], url='/vehicles/')
        r = self.get('/taxis/{}/'.format(taxi_id))
        self.assert200(r)
        self.assertEqual(r.json['data'][0]['vehicle']['color'], 'red')
        self.assertEqual(len(models.Taxi.query.all()), 1)

    def test_remove_ads(self):
        pass
        #No longer active
        #self.init_taxi()
        #r = self.post([dict_taxi])
        #self.assert201(r)
        #self.check_req_vs_dict(r.json['data'][0], dict_taxi)
        #ads_json = r.json['data'][0]['ads']
        #ads = current_app.extensions['sqlalchemy'].db.session.query(ADS)\
        #        .filter_by(numero=ads_json['numero']).first()
        #self.get('/ads/delete?id={}'.format(ads.id))
        #self.assertEqual(len(Taxi.query.all()), 0)

    def test_remove_driver(self):
        pass
        #No longer active
        #self.init_taxi()
        #r = self.post([dict_taxi])
        #self.assert201(r)
        #self.check_req_vs_dict(r.json['data'][0], dict_taxi)
        #driver_json = r.json['data'][0]['driver']
        #driver = current_app.extensions['sqlalchemy'].db.session.query(Driver).\
        #        filter_by(professional_licence=driver_json['professional_licence']).first()
        #r = self.get('/drivers/delete?id={}'.format(driver.id))
        #self.assertEqual(len(Taxi.query.all()), 0)


    def test_two_drivers_two_ads_one_taxi(self):
        self.assertEqual(len(models.Taxi.query.all()), 0)
        self.post_taxi()
        self.post_taxi()
        drivers = models.Driver.query.all()
        ads = models.ADS.query.all()
        self.assertEqual(len(drivers), 2)
        self.assertEqual(len(ads), 2)
        self.assertEqual(len(models.Taxi.query.all()), 1)
        self.assertEqual(models.Taxi.query.all()[0].driver_id,
                max(drivers, key=lambda d: d.added_at).id)
        self.assertEqual(models.Taxi.query.all()[0].ads_id,
                max(ads, key=lambda d: d.added_at).id)
