/**
  Copyright (c) 2015, 2023, Oracle and/or its affiliates.
  Licensed under The Universal Permissive License (UPL), Version 1.0
  as shown at https://oss.oracle.com/licenses/upl/

*/
define([
  "ojs/ojcomposite",
  "text!./md-wrapper-view.html",
  "./md-wrapper-viewModel",
  "text!./component.json",
  "css!./md-wrapper-styles.css",
], function (Composite, view, viewModel, metadata) {
  Composite.register("md-wrapper", {
    view: view,
    viewModel: viewModel,
    metadata: JSON.parse(metadata),
  });
});
