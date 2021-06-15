"""
    Testing registration, retrieving user info, logging out and logging in.

    Each test must contain registering a new user. This is because we can't save values
    between each test case. Each test case must be independent of other tests. This framework
    rolls back the changes to the test database after each test is run. Because of this, it is
    okay to use the same username and email in each test case since the user gets deleted after
    each test.
"""

from rest_framework.test import APITestCase
from rest_framework import status
import json


class AuthenticationTestCase(APITestCase):

    def test_register(self):
        creds = {
            'username': 'test_user',
            'email': 'testing@test.com',
            'password': 'verysecurepwd'
        }

        response = self.client.post('/api/auth/register', data=creds)
        response_data = json.loads(response.content)

        self.assertEqual(response_data['user']['username'], 'test_user')
        self.assertEqual(response_data['user']['email'], 'testing@test.com')

    def test_get_user(self):
        creds = {
            'username': 'test_user',
            'email': 'testing@test.com',
            'password': 'verysecurepwd'
        }

        # register first to get a token
        reg_resp = self.client.post('/api/auth/register', data=creds)
        resp_data = json.loads(reg_resp.content)
        token = resp_data['token']

        # Don't expect this to work like the requests module. See below how I have to pass the authorization header
        response = self.client.get('/api/auth/user', content_type='application/json', HTTP_AUTHORIZATION=f'Token {token}')
        resp_data = json.loads(response.content)

        self.assertEqual(resp_data['username'], 'test_user')
        self.assertEqual(resp_data['email'], 'testing@test.com')

    # test the flow of registering for an account, logging out, then logging back in
    def test_register_logout_login(self):
        creds = {
            'username': 'test_user',
            'email': 'testing@test.com',
            'password': 'verysecurepwd'
        }

        # register first to get a token
        reg_resp = self.client.post('/api/auth/register', data=creds)
        resp_data = json.loads(reg_resp.content)
        token = resp_data['token']

        # logout
        logout_resp = self.client.post('/api/auth/logout', content_type='application/json', HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(logout_resp.status_code, status.HTTP_204_NO_CONTENT)

        # login and make sure it returns the same user info used for registration
        login_creds = {
            'username': 'test_user',
            'password': 'verysecurepwd'
        }
        login_resp = self.client.post('/api/auth/login', data=login_creds)
        login_data = json.loads(login_resp.content)

        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(login_data['user']['username'], login_creds['username'])
        self.assertEqual(login_data['user']['email'], creds['email'])

