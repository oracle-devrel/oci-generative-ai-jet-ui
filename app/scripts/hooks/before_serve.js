/**
  Copyright (c) 2015, 2023, Oracle and/or its affiliates.
  Licensed under The Universal Permissive License (UPL), Version 1.0
  as shown at https://oss.oracle.com/licenses/upl/

*/

"use strict";

module.exports = function (configObj) {
  return new Promise((resolve, reject) => {
    console.log("Running before_serve hook.");
    // ojet custom connect and serve options
    const { connectOpts, serveOpts } = configObj;
    const express = require("express");
    const http = require("http");
    const proxy = require("express-http-proxy");
    const url = require("url");

    // New hostname+path as specified by question:
    const apiProxy = proxy("http://localhost:8080", {
      proxyReqPathResolver: (req) => url.parse("/api" + req.url).path,
    });
    const app = express();
    app.use("/api", apiProxy);
    // pass back custom http
    configObj["http"] = http;
    // pass back custom express app
    configObj["express"] = app;
    // pass back custom options for http.createServer
    // const serverOptions = {...};
    // configObj['serverOptions'] = serverOptions;
    // pass back custom server
    // configObj['server'] = http.createServer(serverOptions, express());
    // const tinylr = require('tiny-lr');
    // pass back custom live reload server
    // configObj['liveReloadServer'] = tinylr({ port: PORT });
    // pass back a replacement set of middleware
    // configObj['middleware'] = [...];
    // pass back a set of middleware that goes before the default middleware
    // configObj['preMiddleware'] = [...];
    // pass back a set of middleware that goes after the default middleware
    // configObj['postMiddleware'] = [...];
    resolve(configObj);
  });
};
