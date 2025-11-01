from flask import json, request, jsonify
from .. import basic_auth_bp
from ..services.services import Service as UserService
from flask_cors import cross_origin
from shared.utils.common_utils import get_supported_auth_types

def json_response(payload, status=200):
  return (json.dumps(payload), status, {'content-type': 'application/json'})

@basic_auth_bp.route('/login', methods=['POST'])
@cross_origin()
def login():
    """
    Handles user login.
    """
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return json_response({'error': 'No input data provided'}, 400)
        if 'password' not in data:
            return json_response({'error': 'Password not provided'}, 400)

        user_service = UserService(data.get('email_id'))
        user = user_service.find_user(data.get('email_id'))
        if not user:
            return json_response({'error': 'User not found'}, 404)

        authenticated = user_service.authenticate_user(data.get('email_id'), data.get('password'), db_user=user)
        if authenticated:
            return jsonify({
                'user_id': user['user_id'],
                'email_id': user['email_id'],
                'user_name': user['full_name'],
                'auth_type': 'basic',
                'authenticated': authenticated,
                'message': 'Login successful!',
            }, 200)
        else:
            return json_response({
                'email_id': user['email_id'],
                'authenticated': authenticated,
                'error': 'Login failed!'
            }, 401)

@basic_auth_bp.route("/redis/auth-data", methods=['POST', 'GET', 'DELETE'])
@cross_origin()
def handle_auth_data():
    """
    Handle Redis operations for  basic Auth data.
    """
    if request.method == 'POST':
        user_data = request.json
        if not user_data:
            return jsonify({'error': 'No user data provided'}), 400
    
        user = UserService(user_data.get('email_id')).find_user(user_data.get('email_id'))

        user_auth_data = {
            'user_id': user.get('user_id'),
            'email_id': user_data.get('email_id'),
            'user_name': user.get('full_name'),
            'auth_type': get_supported_auth_types()[2],  # Auth type - basic
            'password': user.get('password'),
            'authenticated': True
        }

        response = UserService(user_data.get('email_id')).set_user_auth_data(user.get('user_id'), user_auth_data)

        if response is False:
            return jsonify({'error': 'Failed to save user auth data'}), 500
        # Return success response
        if response is True:
            return jsonify({'message': 'User auth data saved successfully'}), 201

    elif request.method == 'GET':
        email_id = request.args.get('email')

        if not email_id:
            return jsonify({'error': 'Email ID not provided'}), 400

        user = UserService(email_id).find_user(email_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404    
        
        response = UserService(email_id).get_user_auth_data(user.get('user_id'))
        print("Response from Redis: ", response)
        if not response:
            return jsonify({'error': 'No auth token found for user'}), 404
        return jsonify({'user_auth_data': {
            'user_id': response.get('user_id'),
            'email_id': response.get('email_id'),
            'user_name': response.get('full_name'),
            'auth_type': response.get('auth_type'),
            'authenticated': response.get('authenticated')
        }}), 200

    elif request.method == 'DELETE':
        email_id = request.args.get('email')

        if not email_id:
            return jsonify({'error': 'Email ID not provided'}), 400

        user = UserService(email_id).find_user(email_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        response = UserService(email_id).delete_user_auth_data(user.get('user_id'))
        if response is False:
            return jsonify({'error': 'Failed to delete user auth data'}), 500
        
        # Return success response
        if response is True:
            return jsonify({'message': 'User auth data deleted successfully'}), 204