from marshmallow import Schema, fields

class LoginDetailsSchema(Schema):
  user_id = fields.Int()
  email_id = fields.Str(required=True)
  full_name = fields.Str(required=True)
  auth_type = fields.Str(required=True)
  authenticated = fields.Boolean(required=True)