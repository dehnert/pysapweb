Getting Started
===============

Prerequisites
-------------

To use pysapweb, you will need:

- `Python 2.7`_
- `pip`_
- the ability to obtain MIT Certificates (for students, faculty and staff)

.. _Python 2.7: http://python.org/download/
.. _pip: http://www.pip-installer.org/en/latest/installing.html


Installing pysapweb
-------------------

::

    $ pip install pysapweb


Creating the Firefox Profile
----------------------------

The instance of Firefox that pysapweb controls is launched from a dedicated
profile stored in `~/.pysapweb/`. To configure this profile run::

    $ python -m pysapweb.sap_profiles

from a terminal. Firefox will launch. Follow the prompts in the terminal.

.. warning::

    Take care when interacting with Firefox windows that are controlled by
    pysapweb. Clicking links or entering a URL in the address bar will cause
    pysapweb to lose its handle on the window and crash.


Next Steps
----------

That's it! You can now run scripts written for pysapweb, or write them
yourself. The pysapweb API exposes methods that allow scripts to click buttons
and enter text as if they were a real user interacting with SAPweb. See this
documentation for details, or check out the source code. The method
:py:func:`rfp.create` in `rfp.py` is a good starting point.
