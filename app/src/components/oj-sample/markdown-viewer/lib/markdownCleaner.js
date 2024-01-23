/**
 * Copyright (c) 2018, 2023, Oracle and/or its affiliates.
 * The Universal Permissive License (UPL), Version 1.0
 */
define([],
function(){
  'use strict';
    function MarkdownCleaner() {
    } 
    
    MarkdownCleaner.prototype.defaultCleanse = function(rawOutput){
      var scriptTag = /<[//]*script[\s]*>/gi;
      return rawOutput.replace(scriptTag,'&lt;script&gt;');
    };
    
    
    return new MarkdownCleaner;
});


