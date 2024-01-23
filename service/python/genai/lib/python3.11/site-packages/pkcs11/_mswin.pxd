#!python
#cython: language_level=3
#
# MIT License
#
# Copyright 2019 Eric Devolder
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Definitions to support compilation on Windows platform
"""

cdef extern from "Windows.h":
    ctypedef unsigned long DWORD
    ctypedef Py_UNICODE wchar_t
    ctypedef wchar_t *LPWSTR
    ctypedef const wchar_t *LPCWSTR
    ctypedef char *LPSTR
    ctypedef const char *LPCSTR
    ctypedef void *PVOID
    ctypedef const void *LPCVOID
    ctypedef PVOID HANDLE
    ctypedef HANDLE HLOCAL
    ctypedef HANDLE HINSTANCE
    ctypedef HINSTANCE HMODULE
    ctypedef bint BOOL
    ctypedef short INT16

    ctypedef enum LANG_ID:
        LANG_NEUTRAL
        LANG_USER_DEFAULT
        SUBLANG_DEFAULT

    ctypedef enum FORMAT_FLAGS:
        FORMAT_MESSAGE_ALLOCATE_BUFFER
        FORMAT_MESSAGE_FROM_SYSTEM
        FORMAT_MESSAGE_IGNORE_INSERTS

    HMODULE LoadLibraryW(LPCWSTR lpLibFileName)
    BOOL FreeLibrary(HMODULE hLinModule)
    PVOID GetProcAddress(HMODULE hModule, LPCSTR lpProcName)
    DWORD GetLastError()

    DWORD MAKELANGID(INT16 p, INT16 s)
    DWORD FormatMessageW(
        DWORD   dwFlags,
        LPCVOID lpSource,
        DWORD   dwMessageId,
        DWORD   dwLanguageId,
        LPWSTR  lpBuffer,
        DWORD   nSize,
        ...
    )

    HLOCAL LocalFree(HLOCAL handle)

cdef inline winerror(so) with gil:
    """
    returns the last error message, as a string.
    If the string has '%1', it is substituted with the content of 'so' arg.
    """
    #
    # inspired from https://docs.microsoft.com/en-us/windows/desktop/debug/retrieving-the-last-error-code
    #
    cdef LPWSTR msgbuffer = NULL
    dw = GetLastError()
    errmsg = ""

    if dw != 0:
        # from https://docs.microsoft.com/en-us/windows/desktop/api/WinBase/nf-winbase-formatmessage
        # at 'Security Remarks':
        # In particular, it is unsafe to take an arbitrary system error code returned from an API
        # and use FORMAT_MESSAGE_FROM_SYSTEM without FORMAT_MESSAGE_IGNORE_INSERTS.
        #
        # Given that remark, we are not attempting to parse inserts with a va_list.
        # Instead, we only substitute '%1' with the value of so argument, on the returned string.
        
        FormatMessageW(FORMAT_MESSAGE_ALLOCATE_BUFFER|FORMAT_MESSAGE_FROM_SYSTEM|FORMAT_MESSAGE_IGNORE_INSERTS,
                       NULL,
                       dw,
                       MAKELANGID(LANG_USER_DEFAULT, SUBLANG_DEFAULT),
                       <LPWSTR>&msgbuffer,
                       0,
                       NULL)

        errmsg = <str>msgbuffer # C to python string copy
        LocalFree(msgbuffer)
        
    return errmsg.replace('%1', so)

#EOF
