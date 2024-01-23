/**
  Copyright (c) 2015, 2023, Oracle and/or its affiliates.
  Licensed under The Universal Permissive License (UPL), Version 1.0
  as shown at https://oss.oracle.com/licenses/upl/

*/
'use strict';

module.exports = function () {
  return new Promise((resolve) => {
    console.log('Running after_app_restore hook.');
    resolve();
  });
};
