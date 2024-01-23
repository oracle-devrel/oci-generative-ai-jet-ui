/**
  Copyright (c) 2015, 2023, Oracle and/or its affiliates.
  Licensed under The Universal Permissive License (UPL), Version 1.0
  as shown at https://oss.oracle.com/licenses/upl/

*/
"use strict";
define([
  "knockout",
  "ojs/ojcontext",
  "ojs/ojknockout",
  "oj-sample/markdown-viewer/loader",
], function (ko, Context) {
  function MdWrapper(context) {
    var self = this;
    self.composite = context.element;
    self.properties = context.properties;
  }

  return MdWrapper;
});
