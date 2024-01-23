# coding: utf-8
# Modified Work: Copyright (c) 2018, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.
# Copyright (c) 2013-2018, Kim Davies. All rights reserved.

from .core import *
from .codec import *

def ToASCII(label):
    return encode(label)

def ToUnicode(label):
    return decode(label)

def nameprep(s):
    raise NotImplementedError("IDNA 2008 does not utilise nameprep protocol")

