from shared.config.config import get_config
from pymongo import MongoClient

config = get_config('development')

COLLECTION_NAME = 'application_users'

class MongoRepository(object):
  def __init__(self):
    mongo_url = config.MONGO_URI
    self.db = MongoClient(mongo_url).app_db

  def find_all(self, selector):
    return self.db.application_users.find(selector)
 
  def find(self, selector):
    return self.db.application_users.find_one(selector)
 
  def create(self, user):
    return self.db.application_users.insert_one(user)

  def update(self, selector, user):
    return self.db.application_users.replace_one(selector, user).modified_count
 
  def delete(self, selector):
    return self.db.application_users.delete_one(selector).deleted_count