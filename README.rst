pysapweb
========

pysapweb is a Python library that allows programmers to script interactions with
MIT's SAPweb accounting system. Jump in with the `Getting Started Guide`_!

Quick Example
-------------

To create an RFP Reimbursement using the convenience method `rfp.create`, first
set up a Firefox profile per the instructions in the `Getting Started Guide`_,
then type:

.. code-block:: python

    from pysapweb import sap_profiles, rfp
    browser = sap_profiles.load_firefox()
    rfp_number = rfp.create(browser,
                            name="pysapweb Experiment",
                            payee=(False, "Tim D. Beaver"), # non-MIT payee
                            address=("77 Massachusetts Avenue",
                                     "Cambridge", "MA", "02139",
                                     "United States of America"),
                            line_items=[("1/1/2013",    # date of service
                                          "420226",     # G/L account
                                          "6666666",    # your cost object
                                          10000,        # amount, in cents
                                          "Birthday cake")],
                            receipts=["/home/tim/Desktop/receipt.pdf"])

Useful Links
------------

The code is hosted at `github.com/btidor/pysapweb`_.

Documentation is available at `pysapweb.readthedocs.org`_. 

.. _Getting Started Guide: https://pysapweb.readthedocs.org/en/latest/introduction.html
.. _github.com/btidor/pysapweb: https://github.com/btidor/pysapweb
.. _pysapweb.readthedocs.org: https://pysapweb.readthedocs.org/en/latest/
