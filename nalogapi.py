import requests
import json
import random
import string
from datetime import datetime, timezone


class ConfigurationError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class NalogAPI():

    apiUrl = 'https://lknpd.nalog.ru/api/v1'
    username = None
    password = None
    autologin = False
    inn = None
    token = None
    tokenExpireIn = None
    refreshToken = None
    sourceDeviceId = None

    def __init__(self):
        if self.username is None or self.password is None:
            raise ConfigurationError("username and password are required")
        if self.sourceDeviceId is None:
            self.sourceDeviceId = self.createDeviceId()
        if self.autologin:
            self.auth(self.login, self.password)

    @staticmethod
    def configure(username, password, autologin = False):
        NalogAPI.username = username
        NalogAPI.password = password
        NalogAPI.autologin = autologin

    @staticmethod
    def createDeviceId():
        return ''.join(random.choice(string.digits) for i in range(21))

    @staticmethod
    def getUtcDateTime(timestr):
        return datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

    @staticmethod
    def getTimeString(dt):
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def auth(self, login, password):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'referrer': 'https://lknpd.nalog.ru/',
            'referrerPolicy': 'strict-origin-when-cross-origin',
        }
        payload = {
            'username': login,
            'password': password,
            'deviceInfo': {
                'sourceDeviceId': self.sourceDeviceId,
                'sourceType': 'WEB',
                'appVersion': '1.0.0',
                'metaDetails': {
                    'userAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36'
                }
            }
        }
        s = requests.Session()
        retries = requests.adapters.Retry(total=3, backoff_factor=0.5, status_forcelist=[ 502, 503, 504 ])
        s.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
        url = self.apiUrl + '/auth/lkfl'
        try:
            r = s.post(url, data=json.dumps(payload), headers=headers, timeout=5)
        except requests.ConnectionError:
            raise AuthenticationError("Can't connect to authentication server")
        res = r.json()
        if not res['refreshToken']:
            raise AuthenticationError("Authentication failure")
        self.inn = res['profile']['inn']
        self.token = res['token']
        self.tokenExpireIn = self.getUtcDateTime(res['tokenExpireIn'])
        self.refreshToken = res['refreshToken']

    def getToken(self):
        if self.token and self.tokenExpireIn and self.tokenExpireIn > datetime.now().replace(tzinfo=timezone.utc):
            return self.token

        if self.refreshToken is None:
            self.auth(self.username, self.password)
            return self.token

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'referrer': 'https://lknpd.nalog.ru/sales',
            'referrerPolicy': 'strict-origin-when-cross-origin',
        }
        payload = {
            'deviceInfo': {
                'sourceDeviceId': self.sourceDeviceId,
                'sourceType': 'WEB',
                'appVersion': '1.0.0',
                'metaDetails': {
                    'userAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36'
                }
            },
            'refreshToken': self.refreshToken
        }
        s = requests.Session()
        retries = requests.adapters.Retry(total=3, backoff_factor=0.5, status_forcelist=[ 502, 503, 504 ])
        s.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
        url = self.apiUrl + '/auth/token'
        try:
            r = s.post(url, data=json.dumps(payload), headers=headers, timeout=5)
        except requests.ConnectionError:
            raise Exception("Failed to fetch token")
        res = r.json()
        if res['refreshToken']:
            self.refreshToken = res['refreshToken']
        self.token = res['token']
        self.tokenExpireIn = res['tokenExpireIn']
        return self.token

    def call(self, endpoint, payload=None):
        post = True if payload is not None else False
        headers = {
            'authorization': str('Bearer ' + self.getToken()),
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'referrer': 'https://lknpd.nalog.ru/sales/create',
            'referrerPolicy': 'strict-origin-when-cross-origin',
        }
        s = requests.Session()
        retries = requests.adapters.Retry(total=3, backoff_factor=0.5, status_forcelist=[ 502, 503, 504 ])
        s.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
        url = self.apiUrl + '/' + endpoint
        r = None
        if post:
            try:
                r = s.post(url, data=json.dumps(payload), headers=headers, timeout=5)
            except requests.ConnectionError:
                raise Exception("Failed to call")
        else:
            try:
                r = s.get(url, headers=headers, timeout=5)
            except requests.ConnectionError:
                raise Exception("Failed to call")
        res = r.json()
        return res

    @classmethod
    def addIncome(cls, date, amount, name):
        self = cls()
        payload = {
            'paymentType': 'CASH',
            'ignoreMaxTotalIncomeRestriction': False,
            'client': {
                'contactPhone': None,
                'displayName': None,
                'incomeType': 'FROM_INDIVIDUAL',
                'inn': None
            },
            'requestTime': self.getTimeString(datetime.utcnow()),
            'operationTime': self.getTimeString(date),
            'services': [{
            'name': name, # 'Предоставление информационных услуг #970/2495',
            'amount': str(amount),
            'quantity': 1
            }],
            'totalAmount': str(amount)
        }
        res = self.call('income', payload)
        if not res or not 'approvedReceiptUuid' in res:
            return {'error': res}
        return "{}/receipt/{}/{}/print".format(self.apiUrl, self.inn, res['approvedReceiptUuid'])

    @classmethod
    def userInfo(cls):
        self = cls()
        print(self.call('user'))

    @classmethod
    def paymentsInfo(cls):
        self = cls()
        print(self.call('keys'))

def main():
    NalogAPI.configure("INN", "password") #Пароль от личного кабинета налогоплательщика lkfl
    NalogAPI.userInfo()
    # NalogAPI.addIncome(datetime.utcnow(), 1.0, "Предоставление информационных услуг #970/2495")

if __name__ == '__main__':
    main()
