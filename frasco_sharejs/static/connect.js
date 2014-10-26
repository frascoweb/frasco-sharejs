
sharejs.connect = function(server_url, token) {
    if (!server_url) {
        server_url = SHAREJS_SERVER_URL;
    }
    if (!token) {
        token = SHAREJS_TOKEN;
    }
    if (SHAREJS_USE_WEBSOCKET) {
        var qs = '?token=' + encodeURIComponent(token);
        var WSClass = ReconnectingWebSocket ? ReconnectingWebSocket : WebSocket;
        var socket = new WSClass(SHAREJS_SERVER_URL + qs);
    } else {
        var bc_opts = {
            reconnect: true
        };
        if (token) {
            bc_opts['extraHeaders'] = {'X-Sharejs-Token': token};
        }
        var socket = new BCSocket(SHAREJS_SERVER_URL, bc_opts);
    }
    return new window.sharejs.Connection(socket);
};