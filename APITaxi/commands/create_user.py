# -*- coding: utf-8 -*-
from ..extensions import user_datastore
from flask_script import prompt_pass
from . import manager
from flask import current_app

def create_user(email, commit=False, password=None):
    "Create a user"
#    if not validate_email(email):
#        print("email is not valid")
#        return
    user = user_datastore.find_user(email=email)
    if user:
        print("User has already been created")
        return user
    password = password or prompt_pass("Type a password")
    user = user_datastore.create_user(email=email, password=password)
    if commit:
        current_app.extensions['sqlalchemy'].db.session.commit()
    return user

def create_user_role(email, role_name, password=None):
    user = create_user(email, password=password)
    role = user_datastore.find_or_create_role(role_name)
    user_datastore.add_role_to_user(user, role)
    current_app.extensions['sqlalchemy'].db.session.commit()
    return user

@manager.command
def create_operateur(email):
    create_user_role(email, 'operateur')

@manager.command
def create_moteur(email):
    create_user_role(email, 'moteur')

@manager.command
def create_admin(email):
    user = create_user_role(email, 'admin')
    user_datastore.add_role_to_user(user,
            user_datastore.find_role('operateur'))
    user_datastore.add_role_to_user(user,
            user_datastore.find_role('moteur'))
    current_app.extensions['sqlalchemy'].db.session.commit()

@manager.command
def create_mairie(email):
    create_user_role(email, 'mairie')

@manager.command
def create_prefecture(email):
    create_user_role(email, 'prefecture')

@manager.command
def create_stats(email):
    create_user_role(email, 'stats')

@manager.command
def create_aeroport(email):
    create_user_role(email, 'aeroport')
