/**
  Copyright (c) 2017, 2023, Oracle and/or its affiliates.
  The Universal Permissive License (UPL), Version 1.0
*/
define(['ojs/ojcomposite', 'text!./markdown-viewer-view.html', './markdown-viewer-viewModel', 'text!./component.json', 'css!./markdown-viewer-styles'],
  function(Composite, view, viewModel, metadata) {
    Composite.register('oj-sample-markdown-viewer', {
      view: view, 
      viewModel: viewModel, 
      metadata: JSON.parse(metadata)
    });
  }
);