function proxyport(req) {
    var vars;

    vars = req.variables;
    req.log("host = " + vars.host + " path = " +vars.uri);
    return "http://192.168.0.14:8001";
}
