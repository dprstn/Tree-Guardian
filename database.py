from  flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role= db.Column(db.String(50), nullable=False)
    dob = db.Column(db.Date)
    hash_password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)
    token_created_at = db.Column(db.DateTime)

class Species(db.Model):
    species_id = db.Column(db.Integer, primary_key=True)
    species_name = db.Column(db.String(150), nullable=False)



class Tree(db.Model):
    tree_id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('species.species_id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    planting_date = db.Column(db.Date, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    tree_size = db.Column(db.Float, nullable=False)
    health_status = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(255), nullable=True) #stores path like "upload/trees/abc123.jpg"
    notes = db.Column(db.Text)



class Observation_type(db.Model):
    observation_type_id = db.Column(db.Integer, primary_key=True)
    observation_category = db.Column(db.String(50), nullable=False) ## Wildlife
    observation_report =  db.Column(db.String(100), nullable=False) # Disease/ report

class Observation(db.Model):
    observation_id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey('tree.tree_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    observation_type_id = db.Column(db.Integer, db.ForeignKey('observation_type.observation_type_id'), nullable=False)
    notes = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    observed_time = db.Column(db.DateTime, default=datetime.utcnow)


class Adoption(db.Model):
    adoption_id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey('tree.tree_id'), nullable=False, unique=True)
    user_id = db.Column(db.Integer,db.ForeignKey('user.user_id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

class Event(db.Model):
    event_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    event_date = db.Column(db.DateTime, nullable=False)
###############################################################################
class CareGuide(db.Model):
    care_guide_id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('species.species_id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    url = db.Column(db.String(255)) # merged url link



class LoyaltyLedger(db.Model):
    ledger_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False)

class Badge(db.Model):
    badge_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class UserBadge(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), primary_key=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.badge_id'), primary_key=True)
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)






