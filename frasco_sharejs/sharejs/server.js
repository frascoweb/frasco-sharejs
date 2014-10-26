express = require('express');
yaml = require('js-yaml');
fs = require('fs');
parseArgs = require('minimist');
redis = require('redis');


function createBackend(url) {
  var db = require('livedb-mongo')(url, {safe: true});
  return require('livedb').client(db);
}


function ShareJsAuthHandler(redis) {
  return function(token, collection, doc, callback) {
    var key = 'sharejs:' + token;
    redis.sismember(key, collection + '/' + doc, function(err, success) {
      callback(!err && success);
    });
  };
}


function createShareClient(backend, auth) {
  var share = require('share').server.createClient({backend: backend});

  share.use('connect', function(req, next) {
    // initializes the session
    req.agent.session.token = req.stream.token;
    req.agent.session.allowedDocs = {};
    next();
  });

  share.use(function(req, next) {
    if (req.action === 'connect' || typeof(req.collection) === 'undefined' ||
        typeof(req.docName) === 'undefined') {
          return next();
    }

    var doc = req.collection + '/' + req.docName;
    var allowed = req.agent.session.allowedDocs[doc];

    if (typeof(allowed) === 'undefined') {
      var token = req.agent.session.token;
      if (auth) {
        auth(token, req.collection, req.docName, function(success) {
          req.agent.session.allowedDocs[doc] = success;
          if (success) {
            console.log('Authorized access to ' + doc + ' for ' + token);
            next();
          } else {
            console.log('Rejected access to ' + doc + ' for ' + token);
            next('403: Not Allowed');
          }
        });
      } else {
        req.agent.session.allowedDocs[doc] = true;
        next();
      }
    } else if (!allowed) {
      next('403: Not Allowed');
    } else {
      next();
    }

  });

  return share;
}


function createShareBrowserChannelServer(shareClient) {
  var Duplex = require('stream').Duplex;
  var browserChannel = require('browserchannel').server
  var app = express();

  var corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Sharejs-Token'
  };
  var options = {
    webserver: app,
    headers: corsHeaders
  };

  app.use(function(req, res, next) {
    if (req.method === 'OPTIONS') {
      // must intercept OPTIONS method that is triggered
      // because of the Access-Control-Allow-Headers header
      // and it is not handled by browserchannel
      res.set(corsHeaders);
      res.sendStatus(200);
    } else {
      next();
    }
  });

  app.use(browserChannel(options, function (client) {
    var stream = new Duplex({objectMode: true});
    var token = client.headers['x-sharejs-token'];
    if (!token) {
      return client.stop(function() {
        client.close();
      });
    }
    stream.token = token;

    stream._read = function() {};
    stream._write = function(chunk, encoding, callback) {
      if (client.state !== 'closed') {
        client.send(chunk);
      }
      callback();
    };

    client.on('message', function(data) {
      stream.push(data);
    });

    client.on('close', function(reason) {
      stream.push(null);
      stream.emit('close');
    });

    stream.on('end', function() {
      client.close();
    });

    shareClient.listen(stream);
  }));

  return app;
}


function createShareWebsocketServer(shareClient) {
  var Duplex = require('stream').Duplex;
  var WebSocketServer = require('ws').Server;
  var url = require('url');
  var app = require('http').createServer(function (req, res) {
    res.writeHead(200, {'Content-Type': 'text/plain'});
    res.end('okay');
  });

  app.wss = new WebSocketServer({server: app});
  app.wss.on('connection', function (client) {
    var stream = new Duplex({objectMode: true});
    var parsed_url = url.parse(client.upgradeReq.url, true);
    var token = parsed_url.query.token;
    if (!token) {
      return client.close();
    }
    stream.token = token;
    stream.headers = client.upgradeReq.headers;
    stream.remoteAddress = client.upgradeReq.connection.remoteAddress;

    stream._read = function() {};
    stream._write = function(chunk, encoding, callback) {
      client.send(JSON.stringify(chunk));
      callback();
    };

    client.on('message', function(data) {
      stream.push(JSON.parse(data));
    });

    client.on('error', function(msg) {
      client.close(msg);
    });

    client.on('close', function(reason) {
      stream.push(null);
      stream.emit('close');
      client.close(reason);
    });

    stream.on('end', function() {
      client.close();
    });

    shareClient.listen(stream);
  });

  return app;
}


function attachRESTmiddleware(app, backend) {
  app.use('/', require('livedb-rest')(backend));
}


function createRESTServer(backend) {
  var app = express();
  attachRESTmiddleware(app, backend);
  return app;
}


function startShareBrowserChannelServer(options, backend) {
  var redisClient = redis.createClient(options['redis-port'], options['redis-host']),
      shareClient = createShareClient(backend, ShareJsAuthHandler(redisClient)),
      app = createShareBrowserChannelServer(shareClient);

  if (options['rest']) {
    attachRESTmiddleware(app, backend);
  }

  app.listen(options.port, options.host);
  console.log("ShareJS Server (browserchannel) listening on " + options.host + ":" + options.port);
}


function startShareWebsocketServer(options, backend) {
  var redisClient = redis.createClient(options['redis-port'], options['redis-host']),
      shareClient = createShareClient(backend, ShareJsAuthHandler(redisClient)),
      app = createShareWebsocketServer(shareClient);

  app.listen(options.port, options.host);
  console.log("ShareJS Server (websocket) listening on " + options.host + ":" + options.port);
}


function startRESTServer(options, backend) {
  var app = createRESTServer(backend);
  app.listen(options.port, options.host);
  console.log('ShareJS REST server listening on port ' + options.port);
}


function parseCmdArgs(defaults) {
  var argv = parseArgs(process.argv.slice(2));
  Object.keys(defaults).forEach(function(k) {
    if (typeof(argv[k]) == 'undefined') {
      argv[k] = defaults[k];
    }
  });
  return argv;
}


function loadConfig(filename, defaults) {
  if (!fs.existsSync(filename)) {
    return defaults;
  }
  var config = yaml.safeLoad(fs.readFileSync(filename, 'utf8'));
  if (defaults) {
    Object.keys(defaults).forEach(function(k) {
      if (typeof(config[k]) == 'undefined') {
        config[k] = defaults[k];
      }
    });
  }
  return config;
}


function main() {
  var argv = parseCmdArgs({
    'config': 'config.yml',
    'port': 3000,
    'host': '127.0.0.1',
    'mongodb-url': 'mongodb://localhost:27017/sharejs?auto_reconnect',
    'redis-host': 'localhost',
    'redis-port': 6379,
    'rest': false,
    'rest-only': false,
    'websocket': false
  });

  var config = loadConfig(argv['config'], argv);
  var backend = createBackend(config['mongodb-url']);

  if (config['rest-only']) {
    startRESTServer(config, backend);
  } else if (config['websocket']) {
    startShareWebsocketServer(config, backend);
  } else {
    startShareBrowserChannelServer(config, backend);
  }
}


main()