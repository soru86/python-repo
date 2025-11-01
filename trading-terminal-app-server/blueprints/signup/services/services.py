from datetime import datetime
from shared.utils.common_utils import generate_unique_user_id, text_to_base64
from ..repositories import UserRepository
from ..repositories.repositories import MongoRepository
from ..schemas.schemas import ApplicationUserSchema

class Service(object):
  def __init__(self, repo_client=UserRepository(adapter=MongoRepository)):
    """to initialize the repository instance"""

    self.repo_client = repo_client

  def find_all_users(self):
    """Handles find all users."""

    users  = self.repo_client.find_all()
    return [self.dump(user) for user in users]

  def find_user(self, email):
    """Handles find user with email_id."""

    user = self.repo_client.find({'email_id': email})
    return self.dump(user)

  def create_user(self, user):
    """Handles saving a new user in db collection."""

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
    if user.get('password'):
      user['password'] = text_to_base64(user.get('password'))
    
    self.repo_client.create(user)
    return self.dump(user)

  def update_user(self, user):
    """Handles updating an existing user in db collection."""

    records_affected = self.repo_client.update({'email_id': user.email_id}, user)
    return records_affected > 0

  def delete_user(self):
    """Handles deleting user with email_id."""

    records_affected = self.repo_client.delete({'email_id': self.email_id})
    return records_affected > 0

  def dump(self, data):
    """Handles the creation of JSON from data object."""
    
    return ApplicationUserSchema().dump(data)
