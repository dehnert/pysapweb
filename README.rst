pysapweb
========

pysapweb is a Python library that allows programmers to script interactions with
MIT's SAPweb accounting system.

Quick Example
-------------

To create an RFP Reimbursement using the convenience method `rfp.create`::

    from pysapweb import rfp
    rfp_number = rfp.create(browser,
                            name="pysapweb Experiment",
                            payee=(False, "Tim D. Beaver"), # non-MIT payee
                            address=("77 Massachusetts Avenue",
                                     "Cambridge", "MA", "02139",
                                     "United States of America"),
                            line_items=[("1/1/2013",    # date of service
                                          "420226",     # G/L account
                                          "666666",     # your cost object
                                          10000,        # amount, in cents
                                          "Birthday cake")],
                            receipts=["/home/tim/Desktop/receipt.pdf"])

Getting Started
---------------

Documentation for pysapweb is available at `pysapweb.readthedocs.org`_. Jump in
with the `Getting Started Guide`_.

.. _pysapweb.readthedocs.org: https://pysapweb.readthedocs.org/en/latest/
.. _Getting Started Guide: https://pysapweb.readthedocs.org/en/latest/introduction.html
