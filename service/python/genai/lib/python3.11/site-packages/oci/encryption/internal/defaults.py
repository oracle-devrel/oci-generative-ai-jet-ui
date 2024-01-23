# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from oci.encryption.algorithms import Algorithm

import math

DEFAULT_ENCODING = "utf-8"

DEFAULT_ALGORITHM = Algorithm.AES_256_GCM_IV12_TAG16

DEFAULT_MAX_GCM_ENCRYPTION_SIZE = int(math.pow(2, 31) - 1)

DEFAULT_MAX_ENCRYPTION_SIZE_SENTINEL = object()
