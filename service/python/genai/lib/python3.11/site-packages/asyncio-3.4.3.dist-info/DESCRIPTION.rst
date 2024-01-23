Tulip is the codename for my reference implementation of PEP 3156.

PEP 3156: http://www.python.org/dev/peps/pep-3156/

*** This requires Python 3.3 or later! ***

Copyright/license: Open source, Apache 2.0. Enjoy.

Master Mercurial repo: http://code.google.com/p/tulip/

The actual code lives in the 'asyncio' subdirectory.
Tests are in the 'tests' subdirectory.

To run tests:
  - make test

To run coverage (coverage package is required):
  - make coverage

On Windows, things are a little more complicated.  Assume 'P' is your
Python binary (for example C:\Python33\python.exe).

You must first build the _overlapped.pyd extension and have it placed
in the asyncio directory, as follows:

    C> P setup.py build_ext --inplace

If this complains about vcvars.bat, you probably don't have the
required version of Visual Studio installed.  Compiling extensions for
Python 3.3 requires Microsoft Visual C++ 2010 (MSVC 10.0) of any
edition; you can download Visual Studio Express 2010 for free from
http://www.visualstudio.com/downloads (scroll down to Visual C++ 2010
Express).

Once you have built the _overlapped.pyd extension successfully you can
run the tests as follows:

    C> P runtests.py

And coverage as follows:

    C> P runtests.py --coverage

--Guido van Rossum <guido@python.org>


