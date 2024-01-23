/*
 Copyright (c) 2017, 2019, Oracle and/or its affiliates.
 The Universal Permissive License (UPL), Version 1.0
 */
/*
 * QUnit Tests for Markdown Viewer
 */
'use strict';
define(['ojs/ojcontext', 'knockout',
    'oj-sample/markdown-viewer/extension/tests/viewModels/testModel',
    'text!oj-sample/markdown-viewer/extension/tests/views/test.html'
  ],
  function (Context, ko, TestModel, testMarkup) {
    QUnit.module('markdown-viewer:properties');
    QUnit.test('Default properties test', function (assert) {
      //insert the testing DOM structure
      var insertSite = document.getElementById('qunit-fixture');
      var template = document.createElement('template');
      template.innerHTML = testMarkup;
      insertSite.appendChild(template.content);
      var done = assert.async();
      assert.expect(1);

      require(['oj-sample/markdown-viewer/loader'], function () {
        var componentDom = document.getElementById('oj-sample-markdown-viewer-tests');
        var testModel = new TestModel();
        var busyContext = Context.getContext(componentDom).getBusyContext();
        ko.applyBindings(testModel, componentDom);

        busyContext.whenReady().then(function () {
          //did it instantiate?
         var ccaElement = document.getElementById('demoMarkdown');
         var flavor = ccaElement.getProperty('flavor');

          assert.ok(flavor === 'vanilla', 'Default markdown flavor is: \"vanilla\"');
          done();
        });
      });
    });

  });