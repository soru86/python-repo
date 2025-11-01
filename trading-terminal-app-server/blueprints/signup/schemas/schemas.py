from marshmallow import Schema, fields
from shared.utils.common_utils import generate_unique_user_id

class SubscriptionSchema(Schema):
    id = fields.Int()
    name = fields.Str(required=True)
    price = fields.Float(required=True)
    duration = fields.Str(required=True)
    is_active = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class ApplicationUserSchema(Schema):
  user_id = fields.Int()
  full_name = fields.Str()
  email_id = fields.Str(required=True)
  mobile_num = fields.Str()
  password = fields.Str(required=True)
  subscription = fields.Nested(SubscriptionSchema)
  is_active = fields.Boolean(dump_default=True, load_default=True)
  is_admin = fields.Boolean(dump_default=False, load_default=False)
  created_at = fields.DateTime()
  updated_at = fields.DateTime()
  