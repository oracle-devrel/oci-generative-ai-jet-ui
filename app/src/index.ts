/**
 * @license
 * Copyright (c) 2014, 2023, Oracle and/or its affiliates.
 * Licensed under The Universal Permissive License (UPL), Version 1.0
 * as shown at https://oss.oracle.com/licenses/upl/
 * @ignore
 */
import "./components/app";

declare global {
  namespace preact.JSX {
    interface IntrinsicElements {
      "md-wrapper": any;
    }
  }
}
