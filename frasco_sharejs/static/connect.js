
sharejs.connect = function(server_url, token) {
    if (!server_url) {
        server_url = SHAREJS_SERVER_URL;
    }
    if (!token) {
        token = SHAREJS_TOKEN;
    }
    var bc_opts = {
        reconnect: true
    };
    if (token) {
        bc_opts['extraHeaders'] = {'X-Sharejs-Token': token};
    }
    var bc_socket = new BCSocket(SHAREJS_SERVER_URL, bc_opts);
    return new window.sharejs.Connection(bc_socket);
};