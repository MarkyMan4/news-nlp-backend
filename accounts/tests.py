from rest_framework.test import APITestCase
from rest_framework import status
import json
import os


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
