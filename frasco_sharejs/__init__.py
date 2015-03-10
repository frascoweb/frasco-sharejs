from frasco import Feature, action, current_app, Markup, hook, session
from werkzeug.local import LocalProxy
from .api import ShareJsApi
from redis import StrictRedis
import os
import hashlib
import uuid


class SharejsFeature(Feature):
    name = 'sharejs'
    ignore_attributes = ['current_token']
    defaults = {"mongodb_url": "mongodb://localhost:27017/sharejs?auto_reconnect",
                "server_url": None,
                "server_port": 3000,
                "server_host": "127.0.0.1",
                "api_url": None,
                "token_ttl": 3600,
                "rest_api": False,
                "use_websocket": False,
                "local_rest_api": False,
                "local_rest_api_port": 3100,
                "redis_host": "localhost",
                "redis_port": 6379}

    def init_app(self, app):
        sharejs_path = os.path.join(os.path.dirname(__file__), 'sharejs')
        self.serverjs_path = os.path.join(sharejs_path, 'server.js')

        args = ["--mongodb-url", self.options['mongodb_url'],
                "--redis-host", self.options['redis_host'],
                "--redis-port", self.options['redis_port']]

        sharejs_args = ["node", self.serverjs_path, "--port",
            self.options['server_port'], "--host", self.options['server_host']] + args
        if self.options['rest_api']:
            sharejs_args.append('--rest')
        if self.options['use_websocket']:
            sharejs_args.append('--websocket')
        app.processes.append(("sharejs", sharejs_args))

        if self.options['server_url'] is None:
            self.options['server_url'] = 'http://%s:%s/channel' % (
                app.config.get('SERVER_NAME') or 'localhost',
                self.options['server_port'])

        if self.options['local_rest_api']:
            app.processes.append(("sharejs_api", ["node", self.serverjs_path,
                "--rest-only", "--port", self.options['local_rest_api_port']] + args))

        if self.options['api_url'] is None:
            self.options['api_url'] = 'http://localhost:%s' % \
                self.options['local_rest_api_port']
        self.api = ShareJsApi(self.options['api_url'])
        self.redis = StrictRedis(self.options['redis_host'], self.options['redis_port'])

        app.jinja_env.globals['current_sharejs_token'] = current_sharejs_token
        app.jinja_env.globals['sharejs_js_vars'] = LocalProxy(
            lambda: self.get_sharejs_js_vars())

        if app.features.exists('assets'):
            app.features.assets.expose_package('sharejs', __name__)
            assets = ['sharejs/bcsocket.js', 'sharejs/text.js', 'sharejs/json0.js',
                'sharejs/share.js', 'sharejs/connect.js']
            if self.options['use_websocket']:
                assets.append('sharejs/reconnecting-websocket.js')
            app.assets.register('sharejs', {
                "contents": [{"filters": "jsmin", "contents": assets}],
                "output": 'sharejs'})

    @hook()
    def before_request(self):
        current_app.config['EXPORTED_JS_VARS'].update({
            'SHAREJS_SERVER_URL': self.options['server_url'],
            'SHAREJS_TOKEN': self.current_token,
            'SHAREJS_USE_WEBSOCKET': self.options['use_websocket']
        })

    @action('create_sharejs_token', default_option='doc_id', as_='sharejs_token')
    def create_token(self, doc_id=None, *docs):
        token = hashlib.sha1(str(uuid.uuid4())).hexdigest()
        self.authorize_docs(doc_id or 0, *docs, token=token)
        return token

    @property
    def current_token(self):
        if 'sjstoken' not in session:
            token = self.create_token()
            session['sjstoken'] = token
        else:
            self.redis.expire('sharejs:%s' % session['sjstoken'],
                self.options["token_ttl"])
        return session['sjstoken']

    @action('authorize_sharejs_doc', default_option='doc_id')
    def authorize_docs(self, doc_id, *docs, **kwargs):
        token = kwargs.get('token') or self.current_token
        key = 'sharejs:%s' % token
        self.redis.sadd(key, *map(str, list([doc_id], *docs)))
        self.redis.expire(key, self.options["token_ttl"])
        return token


current_sharejs_token = LocalProxy(lambda: current_app.features.sharejs.current_token)
