class UserRepository(object):
  def __init__(self, adapter=None):
    self.client = adapter()

  def find_all(self, selector):
    return self.client.find_all(selector)
 
  def find(self, selector):
    return self.client.find(selector)
 
  def create(self, user):
    return self.client.create(user)
  
  def update(self, selector, user):
    return self.client.update(selector, user)
  
  def delete(self, selector):
    return self.client.delete(selector)
