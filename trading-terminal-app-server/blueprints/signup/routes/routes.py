from flask import json, g, request, jsonify
from .. import signup_bp
from ..schemas.schemas import ApplicationUserSchema
from ..services.services import Service as UserService
from flask_cors import cross_origin

def json_response(payload, status=200):
  return (json.dumps(payload), status, {'content-type': 'application/json'})

@signup_bp.route('/signup', methods=['POST'])
@cross_origin()
def register():
    """An endpoint to create a new user in the database"""

    input_user = ApplicationUserSchema().load(json.loads(request.data))
    if input_user is None or not input_user:
        return json_response({'error': 'Invalid input user data'}, 422)
    
    user = UserService().create_user(input_user)
    return jsonify(user)

@signup_bp.route('/create-admin', methods=['GET', 'POST'])
@cross_origin()
def add_admin_user():
    """An endpoint to create a new admin user in the database, this will be private route"""

    input_admin_user = ApplicationUserSchema().load(json.loads(request.data))
    if input_admin_user.errors:
        return json_response({'error': input_admin_user.errors}, 422)
    # get email id of current user from session/context
    input_admin_user['is_admin'] = True
    user = UserService(g.oidc_token_info['sub']).create_user(input_admin_user)
    return json_response(user)