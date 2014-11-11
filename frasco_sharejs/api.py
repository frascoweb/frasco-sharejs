import requests
import json


class ShareJsApi(object):
    TEXT_TYPE = 'http://sharejs.org/types/textv1'
    JSON_TYPE = 'http://sharejs.org/types/json0'

    def __init__(self, server_url):
        self.server_url = server_url

    def request(self, method, action, data=None, **kwargs):
        url = self.server_url + action
        kwargs.setdefault('timeout', 3)
        if data:
            data = json.dumps(data)
        print method, url, data
        return requests.request(method, url, data=data, **kwargs)

    def create_doc(self, collection, name, content=None, ottype=TEXT_TYPE):
        url = '/%s/%s' % (collection, name)
        self.request('PUT', url, data={
            "type": ottype,
            "data": content or ""})

    def delete_doc(self, collection, name):
        url = '/%s/%s' % (collection, name)
        self.request('DELETE', url)

    def get_doc_content(self, collection, name):
        url = '/%s/%s' % (collection, name)
        r = self.request('GET', url)
        r.encoding = 'UTF-8'
        return r.text