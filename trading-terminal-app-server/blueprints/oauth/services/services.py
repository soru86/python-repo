from datetime import datetime
from ...signup.repositories import UserRepository
from ...signup.repositories.repositories import MongoRepository
from ...signup.schemas.schemas import ApplicationUserSchema
from shared.utils.redis_db import redis_db
from shared.utils.common_utils import generate_unique_user_id

class Service(object):
  def __init__(self, email_id, repo_client=UserRepository(adapter=MongoRepository)):
    self.repo_client = repo_client
    self.email_id = email_id

    if not email_id:
      raise Exception("email id not provided")

  def find_user(self, email=None):
    """
    Handles find user with email_id.
    """
    user = self.repo_client.find({'email_id': email, 'is_active': True})
    return self.dump(user)
  
  def create_oauth_user(self, user):
    """Handles saving an oauth user in db collection."""

    if not user.get('user_id'):
      user['user_id'] = generate_unique_user_id()
    if not user.get('created_at'):
      user['created_at'] = datetime.now().astimezone()
    if not user.get('updated_at'):
      user['updated_at'] = datetime.now().astimezone()
    if not user.get('is_active'):
      user['is_active'] = True
    if not user.get('is_admin'):
      user['is_admin'] = False
    
    self.repo_client.create(user)
    return self.dump(user)
  
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

  def dump(self, data):
    return ApplicationUserSchema().dump(data)
