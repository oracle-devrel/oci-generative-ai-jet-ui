/**
  Copyright (c) 2017, 2023, Oracle and/or its affiliates.
  The Universal Permissive License (UPL), Version 1.0
*/
define([
  "ojs/ojcontext",
  "ojs/ojlogger",
  "knockout",
  "ojL10n!./resources/nls/markdown-viewer-strings",
  "marked",
  "./lib/markdownCleaner",
], function (Context, Logger, ko, componentStrings, marked, cleaner) {
  "use strict";
  function MarkdownViewerComponentModel(context) {
    var self = this;
    self.composite = context.element;
    self.res = componentStrings.ojsampleMarkdownViewer;

    self.contentSubId = context.uniqueId + "_content"; //NOTRANS

    self.inputValue = ko.observable();
    self.isContent = ko.observable(false);

    self.applyRedwoodStyling = ko.observable(
      context.properties.htmlRendering.toLowerCase() === "redwood"
    );
    self.applyLegacyStyling = ko.observable(
      ["legacy", "redwood"].includes(
        context.properties.htmlRendering.toLowerCase()
      )
    );

    self.converter = marked;
    self.converter.setOptions({ gfm: context.properties.flavor === "github" });

    self.doFilter = false;
    self.loggingIdentity =
      "oj-sample-markdown-viewer (" + context.uniqueId + "): "; //NOTRANS

    self.properties = context.properties;
    if (self.properties.outputFilter !== undefined) {
      self.doFilter = true;
    }
  }

  /*
   * Standard bindingsApplied lifecycle callback - this is used to carry out the initial conversion by
   * creating the computed value that is actually injected into the iFrame
   * @param {object} context
   * @ignore
   */
  MarkdownViewerComponentModel.prototype.bindingsApplied = function (context) {
    var self = this;
    self.markdownValue = ko.computed(function () {
      //Markdown processing could take some time so we set the busyContext to
      //allow tests to understand this
      var busyContext = Context.getContext(context.element).getBusyContext();
      var options = { description: "Processing of markdown content" }; //NOTRANS
      var busyResolve = busyContext.addBusyState(options);
      if (self.inputValue() !== undefined && self.inputValue().length > 0) {
        //Do a basics of prepping the md and stripping out <script> tags from the generated HTML
        var toParse = self
          .inputValue()
          .replace(/^[\u200B\u200C\u200D\u200E\u200F\uFEFF]/, "");
        var html = cleaner.defaultCleanse(self.converter.parse(toParse));

        //Apply the user supplied filter if present
        var filterPromise;
        if (self.doFilter) {
          filterPromise = self.properties.outputFilter(html);
        } else {
          filterPromise = Promise.resolve(html);
        }

        //Wait for the cleaner callback to resolve and then set the contents of the field
        filterPromise
          .then(function (cleanedHTML) {
            if (cleanedHTML !== undefined && typeof cleanedHTML === "string") {
              if (cleanedHTML.length > 0) {
                self.isContent(true);
                var target = document.getElementById(self.contentSubId);
                target.innerHTML = cleanedHTML;
              } else {
                self.isContent(false);
              }
            } else {
              self.isContent(false);
            }
            busyResolve();
          })
          .catch(function (error) {
            self.isContent(false);
            Logger.error(self.loggingIdentity + " " + error);
            busyResolve();
          });
      } else {
        self.isContent(false);
        busyResolve();
      }
    });
    self.inputValue(self.properties.value);
  };

  MarkdownViewerComponentModel.prototype.propertyChanged = function (context) {
    var self = this;
    if (context.updatedFrom === "external") {
      switch (context.property) {
        case "value":
          self.inputValue(context.value);
          break;
        case "flavor":
          self.converter.setOptions({ gfm: context.value === "github" });
          self.inputValue.valueHasMutated();
          break;
        case "htmlRendering":
          self.applyRedwoodStyling(context.value.toLowerCase() === "redwood");
          self.applyLegacyStyling(
            ["legacy", "redwood"].includes(context.value.toLowerCase())
          );
          break;
      }
    }
  };

  return MarkdownViewerComponentModel;
});
