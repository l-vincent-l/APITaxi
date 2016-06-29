#coding: utf-8
from APITaxi_utils.redis_geo import GeoRedis
from flask.ext.redis import FlaskRedis
redis_store = FlaskRedis.from_custom_provider(GeoRedis)
redis_store_haillog = FlaskRedis()

from flask.ext.celery import Celery
celery = Celery()

from APITaxi_utils.cache_user_datastore import CacheUserDatastore
user_datastore = CacheUserDatastore()
