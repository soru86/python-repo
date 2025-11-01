from . import google_oauth_bp
from flask import jsonify, request
from flask_cors import cross_origin
from ..services.services import Service as AuthService
from shared.utils.common_utils import get_supported_auth_types, generate_unique_user_id

@google_oauth_bp.route("/redis/tokens", methods=['POST', 'GET', 'DELETE'])
@cross_origin()
def handle_token():
    """
    Handle Redis operations for OAuth tokens.
    """
    if request.method == 'POST':
        token_data = request.json
        if not token_data:
            return jsonify({'error': 'No token data provided'}), 400
        
        db_user = AuthService(token_data.get('email_id')).find_user(token_data.get('email_id'))

        user = None
        if 'user_id' not in db_user:
            # Create a new user if not found
            print("I am here: ", db_user)
            user = AuthService(token_data.get('email_id')).create_oauth_user({
                'email_id': token_data.get('email_id'),
                'full_name': token_data.get('user_name'),
            })

        userId = db_user.get('user_id') if 'user_id' in db_user else user.get('user_id')

        user_auth_data = {
            'user_id': userId,
            'email_id': token_data.get('email_id'),
            'user_name': token_data.get('user_name'),
            'auth_type': get_supported_auth_types()[0],  # Auth type - google
            'access_token': token_data.get('credential').get('access_token'),
            'expires_in': token_data.get('credential').get('expires_in'),
            'token_type': token_data.get('credential').get('token_type'),
            'authenticated': True
        }

        response = AuthService(token_data.get('email_id')).set_user_auth_data(userId, user_auth_data)

        if response is False:
            return jsonify({'error': 'Failed to save user auth data'}), 500
        # Return success response
        if response is True:
            return jsonify({'user_auth_data' : {
            'user_id': userId,
            'email_id': token_data.get('email_id'),
            'user_name': token_data.get('user_name'),
            'auth_type': get_supported_auth_types()[0],  # Auth type - google
            'authenticated': True                
            }}), 201

    elif request.method == 'GET':
        email_id = request.args.get('email')

        if not email_id:
            return jsonify({'error': 'Email ID not provided'}), 400

        user = AuthService(email_id).find_user(email_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404    
        
        response = AuthService(email_id).get_user_auth_data(user.get('user_id'))

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

        user = AuthService(email_id).find_user(email_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        response = AuthService(email_id).delete_user_auth_data(user.get('user_id'))
        if response is False:
            return jsonify({'error': 'Failed to delete user auth data'}), 500
        
        # Return success response
        if response is True:
            return jsonify({'message': 'User auth data deleted successfully'}), 204
    