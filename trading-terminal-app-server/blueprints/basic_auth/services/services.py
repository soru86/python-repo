from flask import jsonify
from ...signup.repositories import UserRepository
from ...signup.repositories.repositories import MongoRepository
from ..schemas.schemas import LoginDetailsSchema
from ...signup.schemas.schemas import ApplicationUserSchema
from shared.utils.common_utils import base64_to_text
from shared.utils.redis_db import redis_db

class Service(object):
  def __init__(self, email_id, repo_client=UserRepository(adapter=MongoRepository)):
    self.repo_client = repo_client
    self.email_id = email_id

    if not email_id:
      raise Exception("user id not provided")

  def find_user(self, email=None):
    """
    Handles find user with email_id.
    """
    user = self.repo_client.find({'email_id': email, 'is_active': True})
    return self.dump(ApplicationUserSchema(), user)
  
  def authenticate_user(self, email_id, password, db_user=None):
    """
    Handles user authentication.
    """
    if not db_user:
      db_user = self.find_user(email_id)

    if not db_user:
      return False

    encrypted_password = db_user.get('password')
    if not encrypted_password:
      return False
    
    plain_password = base64_to_text(encrypted_password)
    if not plain_password:
      return False

    if db_user.get('email_id') == email_id and plain_password == password:
      return True
    return False

  def set_user_auth_data(self, user_id, auth_data):
    """
    Handles setting auth data for user.
    """
    if not user_id:
      raise Exception("user_id not provided")

    if not auth_data:
      raise Exception("auth data not provided")

    result = redis_db.set_current_user_auth_data(user_id, auth_data)
    return result
    
  def get_user_auth_data(self, user_id):
    """
    Handles getting auth data for user.
    """

    if not user_id:
      raise Exception("user_id not provided")
    
    user_auth_data = redis_db.get_current_user_auth_data(user_id)

    if not user_auth_data:
      raise Exception("User is not authenticated")
    
    return user_auth_data
  
  def delete_user_auth_data(self, user_id):
    """
    Handles deleting auth data for user.
    """
    if not user_id:
      raise Exception("user_id not provided")
    
    result = redis_db.delete_current_user_auth_data(user_id)
    return result

  def dump(self, schema, data):
    return schema.dump(data)
