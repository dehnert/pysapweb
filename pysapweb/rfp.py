"""
    rfp
    ~~~

    The `rfp` module exposes the Request for Payment (RFP) interface in MIT's
    SAPweb system. It contains a class to interact with each page of the
    interface as well as convenience methods that automate RFP creation,
    updates and lookup.
"""

from selenium.common.exceptions import NoSuchElementException

def create(browser,
           name='',
           payee=None,
           address=None,
           line_items=(),
           office_note='',
           receipts=(),
           send_to=None):
    """
    Create an RFP Reimbursement. Exposes the most common options for both MIT
    and non-MIT payees.

    .. note::
       Parameters are subject to addition and deletion. Reference by kwargs
       is recommended.

    :param browser: WebDriver instance to use
    :param name: RFP name, optional
    :param payee: tuple of (is_mit, name)
    :param address: tuple of (address_line, city[, state], postal_code, country)
    :param line_items: list of tuples of (date_of_service, gl_account,
        cost_object, amount, explanation)
    :param office_note: note to central office, optional
    :param receipts: list of filenames to upload
    :param send_to: tuple of (recipient, note), optional

    All fields should be passed as strings. `is_mit` is a boolean indicating
    if the payee is a current student/employee. `country` and `state` may be
    specified by full name or two-letter abberviation. For `amount`, use USD
    but do not include the dollar sign.

    Return the number of the created RFP, as a string.
    """
    # Search for Payee
    is_mit = payee[0]
    payee_name = payee[1]
    # --- search ---
    page = CreateReimbursementPage(browser)
    page.is_mit(is_mit)
    page.payee_name(payee_name)
    page.search()
    # --- results ---
    assert len(page.results()) == 1
    page = page.results(0)

    # RFP Details
    page.rfp_name(name)

    # Mailing Address
    if address:
        if len(address) == 5:
            address_line, city, state, postal_code, country = address
        elif len(address) == 4:
            address_line, city, postal_code, country = address
        else:
            raise IndexError("address has an improper length.")
        # -- entry ---
        page.country(country)
        page.address(address_line)
        page.city(city)
        try:
            page.state(state)
        except NameError:
            pass
        page.postal_code(postal_code)

    # Line Items
    i = 0
    for date_of_service, gl_account, cost_object, amount, explanation \
        in line_items:

        if i > 0:
            page.add_line()
        page.date_of_service(i, date_of_service)
        page.gl_account(i, gl_account)
        page.cost_object(i, cost_object)
        page.amount(i, amount)
        page.explanation(i, explanation)
        i += 1

    # Office Note
    page.office_note(office_note)
    page = page.save()

    # Attach Receipts
    for receipt in receipts:
        if isinstance(page, ViewAndEditPage):
            page = page.attach_receipt()
        page.select_file(receipt)
        page = page.attach()
    if not receipts:
        page = page.cancel()

    rfp_number = page.rfp_number()

    # Send To?
    if send_to:
        page = page.send_to()
        recipient = send_to[0]
        note = send_to[1]
        # --- search ---
        page.recipient_name(recipient)
        page.search()
        assert len(page.results()) == 1
        page.note(note)
        page = page.send()
    return rfp_number

def view(browser, rfp_number):
    """
    Return details about the specified RFP as a dictionary. Keys may include:

    ==============  ====================  ========
    Details         Address               Tax
    ==============  ====================  ========
    rfp_number      mailing_instructions  tax_type
    inbox           addressee             ssn_tin
    payee           phone
    company_code    address
    rfp_name        city
    rfp_type        state
    payment_method  postal_code
    office_note     country
    history
    ==============  ====================  ========
    
    The line_items key is a list of dictionaries, each containing:
    date_of_service, gl_account, cost_object, amount, explanation.
    """
    # Search for RFP
    page = SearchPage(browser)
    page.rfp_number(rfp_number)
    page = page.search()
    assert isinstance(page, ViewOnlyPage) # a single result found

    # View RFP
    details = {}
    details['rfp_number'] = rfp_number
    details['inbox'] = page.inbox()
    assert page.rfp_number() == rfp_number
    details['payee'] = page.payee()
    details['company_code'] = page.company_code()
    details['rfp_name'] = page.rfp_name()
    details['rfp_type'] = page.rfp_type()
    details['payment_method'] = page.payment_method()
    details['mailing_instructions'] = page.mailing_instructions()
    details['addressee'] = page.addressee()
    details['phone'] = page.phone()
    details['address'] = page.address()
    details['city'] = page.city()
    details['state'] = page.state()
    details['postal_code'] = page.postal_code()
    details['country'] = page.country()
    details['tax_type'] = page.tax_type()
    details['ssn_tin'] = page.ssn_tin()
    details['line_items'] = []
    for i in range(page.line_item_count()):
        li = {}
        li['date_of_service'] = page.date_of_service(i)
        li['gl_account'] = page.gl_account(i)
        li['cost_object'] = page.cost_object(i)
        li['amount'] = page.amount(i)
        li['explanation'] = page.explanation(i)
        details['line_items'].append(li)
    details['office_note'] = page.office_note()
    details['history'] = page.history()
    return details

class BasePage(object):
    """
    Represents a web page loaded through Selenium. Each page is a child class of
    BasePage. Pages have fields, which may be read-write or read-only, and
    actions, which return a new page. Includes common methods for interacting
    with SAPweb pages.

    .. warning::
       Most pages should not be accessed directly, as SAPweb often requires that
       pages be accessed in a specific order. Individual classes will note
       whether or not they are an "entry page" in their documentation.
    """
    entry_url = None

    def __init__(self, browser):
        self.browser = browser
        # If this page is an entry, navigate to the entry URL.
        if self.entry_url:
            self.browser.get(self.entry_url)

    def _pre_transition(self):
        """
        When transitioning to a new page, first call this method. It checks
        for errors; if there are some, it's likely that the transition failed
        and we're actually on the same page that we started on.
        """
        if self.errors():
            raise FailedTransitionError("This page contains errors. " + \
                                        "The transition likely failed.")

    def errors(self):
        """
        Return a list of errors shown by the SAPweb UI. Errors usually indicate
        that an attempted action has failed.
        """
        # Regular Errors
        browsermulticss = self.browser.find_elements_by_css_selector
        errors = [e.text for e in browsermulticss('.portlet-msg-error')]
        errors += [e.text for e in browsermulticss('label.jqerror')]
        return errors

    def info(self):
        """
        Return a list of informational messages shown by the SAPweb UI.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        return [e.text for e in browsermulticss('.portlet-msg-alert')]

    def success(self):
        """
        Return a list of success messages shown by the SAPweb UI.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        return [e.text for e in browsermulticss('.portlet-msg-success')]

    def _radio(self, group_name, val=None):
        """
        Get or set the value of a radio button group. Groups are identified by
        the 'name' attribute, which is the same for all radio buttons in the
        group. The selected button is identified by its 'value' attribute. If
        no button is selected, None is returned.
        """
        browsercss = self.browser.find_element_by_css_selector
        if val is None:
            try:
                selector = "input[type='radio'][name='%s']:checked" % \
                           group_name
                return browsercss(selector).get_attribute("value")
            except NoSuchElementException:
                return None
        else:
            selector = "input[type='radio'][name='%s'][value='%s']" % \
                       (group_name, val)
            browsercss(selector).click()

    def _checkbox(self, selector, val=None):
        """
        Get or set the value of a checkbox. True represents 'checked', False
        represents 'unchecked'. The checkbox is identified by a CSS selector.
        """
        browsercss = self.browser.find_element_by_css_selector
        elem = browsercss(selector)
        if val is None:
            return elem.is_selected()
        else:
            if elem.is_selected() != val:
                elem.click()
            assert elem.is_selected() == val

    def _textbox(self, selector, val=None):
        """
        Get or set the value of a text box. The text box is identified by a CSS
        selector.
        """
        browsercss = self.browser.find_element_by_css_selector
        elem = browsercss(selector)
        if val is None:
            return elem.get_attribute('value')
        else:
            elem.clear()
            elem.send_keys(val)

    def _select(self, fragment, val=None):
        """
        Get or set the value of a select dropdown. The select is identified by
        a fragment of a CSS selector, e.g. `#countries`, or `[name='code']`.
        `val` can match either the value (preferred, faster) or the displayed
        text.
        """
        browsercss = self.browser.find_element_by_css_selector
        if val is None:
            selector = "select%s option:checked" % fragment
            return browsercss(selector).text.strip()
        else:
            try:
                # Convert values (i.e. 'US') into text (i.e., 'United St...')
                optselector = "select%s option[value='%s']" % \
                              (fragment, val)
                val = browsercss(optselector).text.strip()
            except NoSuchElementException:
                pass
            sel = browsercss("select%s" % fragment)
            sel.send_keys(val + '\t')
            assert self._select(fragment) == val

    def _datalist(self, label):
        """
        Get a value out of a table. The row is identified by its header text.
        """
        browserxp = self.browser.find_element_by_xpath
        xpath = "//div[normalize-space(.)='%s']/../../td[@class='data']" % label
        xpath += " | //th[normalize-space(.)='%s']/../td" % label
        return browserxp(xpath).text

    def _try_datalist(self, label):
        """
        For elements that only appear on some pages or in certain circumstances:
        get a value out of a table, and return None if not found.
        """
        try:
            return self._datalist(label)
        except NoSuchElementException:
            return None

    def _row_element(self, rfp):
        """
        In a table of RFPs, get the specified RFP's row as a list of <td>
        elements.
        """
        browsermultixp = self.browser.find_elements_by_xpath
        xpath = "//a[contains(text(), '%s')]/../../td" % rfp
        return browsermultixp(xpath)

class InboxPage(BasePage):
    """
    The RFP Inbox. Entry page.
    """
    entry_url = "https://insidemit-apps.mit.edu/apps/rfp/InboxEntry.action?gatewayType=admin&sapSystemId=PS1"
    help_url = "http://insidemit.mit.edu/help-apps/rfp_inbox.shtml"

    def list(self):
        """
        Get a list of displayed RFPs by RFP number (as strings).
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        return [e.text for e in browsermulticss("td.data > a")]

    def select(self, rfp):
        """
        Click on an RFP's number. Return an instance of
        :class:`ViewAndEditPage`.

        Note that this action may recall the RFP to your inbox. It is
        recommended that you check :meth:`state` before selecting an RFP.
        """
        browserxp = self.browser.find_element_by_xpath
        xpath = "//a[contains(text(), '%s')]/../../td//a" % rfp
        browserxp(xpath).click()
        self._pre_transition()
        return ViewAndEditPage(self.browser)

    def is_deletable(self, rfp):
        """
        Determine whether or not the specified RFP may deleted by the user.
        Return True or False.
        """
        return self._row_element(rfp)[9].text != 'n/a'

    def mark_for_deletion(self, rfp, val=None):
        """
        Get or set whether or not the specified RFP is marked for deletion. True
        if marked, False if unmarked.
        """
        browserxp = self.browser.find_element_by_xpath
        xpath = ("//a[contains(text(), '%s')]/../../td//" +
                 "input[@type='checkbox']") % rfp
        elem = browserxp(xpath)
        if val is None:
            return elem.is_selected()
        else:
            if elem.is_selected() != val:
                elem.click()
            assert elem.is_selected() == val

    def delete_selected(self):
        """
        Click the 'Delete Selected' button. Results load in the same page.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss(".deleteButton").click()

    def is_cloneable(self, rfp):
        """
        Determine whether or not the specified RFP may currently be cloned.
        Return True or False.
        """
        try:
            self._clone_button(rfp)
            return True
        except NoSuchElementException:
            return False

    def clone(self, rfp):
        """
        Click the 'Clone' button for the specified RFP. Return an instance of
        :class:`ViewAndEditPage`.
        """
        self._clone_button(rfp).click()
        return ViewAndEditPage(self.browser)

    def _clone_button(self, rfp):
        """
        Get the 'Clone' button for the specified RFP. If the button does not
        exist, raise a NoSuchElementException.
        """
        browserxp = self.browser.find_element_by_xpath
        xpath = ("//a[contains(text(), '%s')]/../../td//" +
                 "button[contains(@class, '.clone')]") % rfp
        return browserxp(xpath)

    def state(self, rfp):
        """
        Get the field 'State' for the specified RFP. Options include 'Incoming',
        'Saved', 'Sent On' and 'Rejected'.
        """
        browsermultixp = self.browser.find_elements_by_xpath
        xpath = "//a[contains(text(), '%s')]/../../td//img" % rfp
        results = browsermultixp(xpath)
        if len(results) == 0:
            return None
        elif len(results) == 1:
            return results[0].get_attribute("alt").title()
        else:
            raise NoSuchElementException("img not unique in table cell.")

    def receipt(self, rfp):
        """
        Get the field 'Receipt' for the specified RFP. True or False.
        """
        return self._row_element(rfp)[2].text == 'Yes'

    def creation_date(self, rfp):
        """
        Get the field 'Creation Date' for the specified RFP.
        """
        return self._row_element(rfp)[4].text

    def payee(self, rfp):
        """
        Get the field 'Payee' for the specified RFP.
        """
        return self._row_element(rfp)[5].text

    def created_by(self, rfp):
        """
        Get the field 'Created By' for the specified RFP.
        """
        return self._row_element(rfp)[6].text

    def cost_object(self, rfp):
        """
        Get the field 'Cost Object' for the specified RFP.
        """
        return self._row_element(rfp)[7].text

    def amount(self, rfp):
        """
        Get the field 'Amount' for the specified RFP.
        """
        return self._row_element(rfp)[8].text

def CreateReimbursementPage(browser):
    """
    Encapuslates the Create RFP Reimbursement entry URL, returning an instance
    of :class:`SearchForPayeePage`. Entry page.
    """
    entry_url = "https://insidemit-apps.mit.edu/apps/rfp/SelectPayeeReimbursementEntry.action?sapSystemId=PS1"
    browser.get(entry_url)
    return SearchForPayeePage(browser)

def CreatePaymentPage(browser):
    """
    Encapuslates the Create RFP Payment entry URL, returning an instance of
    :class:`SearchForPayeePage`. Entry page.
    """
    entry_url = "https://insidemit-apps.mit.edu/apps/rfp/SelectPayeePaymentEntry.action?sapSystemId=PS1"
    browser.get(entry_url)
    return SearchForPayeePage(browser)

class SearchForPayeePage(BasePage):
    """
    The first step of RFP creation, the Search for Payee page. Not an entry
    page; use :py:func:`CreateReimbursementPage` and
    :py:func:`CreatePaymentPage` instead of direct instantiation.
    """
    help_url = "http://insidemit.mit.edu/help-apps/rfp_select_payee.shtml"

    def is_mit(self, val=None):
        """
        Get or set the field 'MIT/Non-MIT'. True if MIT, False if Non-MIT.
        """
        if val is None:
            return self._radio("payeeType") == "MIT"
        else:
            text = "MIT" if val else "NONMIT"
            self._radio("payeeType", text)

    def payee_name(self, val=None):
        """
        Get or set the field 'Payee Name'.
        """
        return self._textbox("#payeeName", val)

    def search(self):
        """
        Click the 'Search' button. Results load in the same page.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss("#searchButton").click()

    def results(self, index=None):
        """
        Get a list of search results or select one.

        If index is None or not specified: return an ordered list of search
        results, if any are displayed. Results are usually in the form
        "Name (kerberos,department)", although entries such as
        "No results found: Continue" (for non-MIT payees) also count as a
        result.

        If index is not None: click on a search result, treating `index` as
        specifying a result by its zero-indexed position in the list. Return an
        instance of :class:`RequestRfpPage`.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        results = browsermulticss("#mit a")
        if index is None:
            return [result.text.strip() for result in results]
        else:
            results[index].click()
            self._pre_transition()
            return RequestRfpPage(self.browser)

class RequestRfpPage(BasePage):
    """
    The second step of RFP creation, where all the knobs are located. Not an
    entry page.
    """
    help_urls = ["http://insidemit.mit.edu/help-apps/rfp_reimbursement.shtml",
                 "http://insidemit.mit.edu/help-apps/rfp_payment.shtml"]

    def __init__(self, browser):
        super(RequestRfpPage, self).__init__(browser)
        # Select index as a determiner of which address fields to use:
        #  - #country1/#city1/etc. is the permanent address, for RFP Payment
        #      (the mailing address must be the same as this)
        #  - #country2/#city2/etc. is the mailing address, for RFP Reimbursement
        self.index = 1 if "Payment" in browser.title else 2

    # Section: Payment Details
    def payee(self, val=None):
        """
        Get or set the field 'Payee'.

        Non-MIT payees only.
        """
        return self._textbox("#payee", val)

    def change_payee(self):
        """
        Click the 'Change Payee' button. Return an instance of
        :class:`SearchForPayeePage`.

        MIT payees only.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss(".changePayeeAction").click()
        self._pre_transition()
        return SearchForPayeePage(self.browser)

    def charge_to(self, val=None):
        """
        Get or set the field 'Charge to'.
        """
        return self._select("#coCode", val)

    def rfp_name(self, val=None):
        """
        Get or set the field 'Name this RFP'.
        """
        return self._textbox("#rfpName", val)

    # Section: Permanent Address
    def country(self, val=None):
        """
        Get or set the field 'Country' in the permanent address section. In
        addition to full country names, the set operation also supports
        two-leter country codes.

        Note: changing this field may clear the entries in 'Address', 'City',
        'State/Region', and 'Postal Code'.

        Non-MIT payees only.
        """
        selector = "#country%d" % self.index
        return self._select(selector, val)

    def address(self, val=None):
        """
        Get or set the field 'Address' (for RFP Reimbursement, this is the
        mailing address; for RFP Payment, this is both the permanent and
        mailing address---they must be the same).

        Non-MIT payees only.
        """
        selector = "#address%d" % self.index
        return self._textbox(selector, val)

    def city(self, val=None):
        """
        Get or set the field 'City'.

        Non-MIT payees only.
        """
        selector = "#city%d" % self.index
        return self._textbox(selector, val)

    def state(self, val=None):
        """
        Get or set the field 'State/Region'. In addition to full state/region
        names, the set operation also supports two-letter state/region codes.

        Non-MIT payees in the U.S. or Canada only.
        """
        selector = "#region%d" % self.index
        return self._select(selector, val)

    def postal_code(self, val=None):
        """
        Get or set the field 'Postal Code'.

        Non-MIT payees only.
        """
        selector = "#zip%d" % self.index
        return self._textbox(selector, val)

    # Section: Payee's Tax Information
    def citizen_alien(self, val=None):
        """
        Get or set the field 'Is payee a US citizen or a resident alien?' in the
        tax information section. Values are 'Y' (yes), 'N' (no), 'C' (payee is
        not an individual), or None (not yet set).

        Note: changing this field may clear the values in 'Type of Visa' and
        'Country of Citizenship'.

        Non-MIT payees only.
        """
        return self._radio("rfpDocument.payee.usCitizenType", val)

    def ssn_tin(self, val=None):
        """
        Get or set the field 'SSN/TIN' in the tax information section.
        """
        return self._textbox("#ssnTin", val)

    def visa(self, val=None):
        """
        Get or set the field 'Type of Visa' in the tax information section.

        Individual non-citizen payees only.
        """
        return self._textbox("#visaType", val)

    def citizenship(self, val=None):
        """
        Get or set the field 'Country of Citizenship' in the tax information
        section.

        Individual non-citizen payees only.
        """
        return self._select("#citizenship", val)

    # Section: Mailing Instructions
    def mail_check(self, val=None):
        """
        Get or set whether to 'Mail check to payee' (True) or 'Deliver check to
        MIT address' (False) in the mailing instructions section.

        Non-MIT payees only.
        """
        if val is None:
            return self._radio("rfpDocument.mailToMit") == "false"
        else:
            val = "false" if val else "true"
            self._radio("rfpDocument.mailToMit", val)

    def hold_check(self, val=None):
        """
        Get or set whether to 'Hold check for pickup at Accounts Payable
        office' in the mailing instructions section. This option is only
        available if :meth:`mail_check` is False.

        Non-MIT payees only.
        """
        return self._checkbox("#holdCheck", val)

    def addressee(self, val=None):
        """
        Get or set the field 'Name' in the mailing instructions section under
        'Deliver check to MIT address'. Applies to both interdepartmental
        mail and holding for pickup.

        Non-MIT payees only.
        """
        return self._textbox("#addressee", val)

    def building_room(self, val=None):
        """
        Get or set the field 'Building-Room' in the mailing instructions section
        under 'Deliver check to MIT address'.

        Non-MIT payees using interdepartmental mail for delivery, only.
        """
        return self._textbox("#bldg-rm", val)

    def phone(self, val=None):
        """
        Get or set the field 'Phone' in the mailing instructions section under
        'Deliver check to MIT address'.

        Non-MIT payees holding the check for pickup, only.
        """
        # Technically, this is the same field as 'building_room', above.
        return self._textbox("#bldg-rm", val)

    # Section: Line Items
    def line_item_count(self):
        """
        Get the number of line items displayed.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        return len(browsermulticss(".lineItem"))

    def date_of_service(self, li, val=None):
        """
        Get or set the field 'Date of Service' for the specified line item
        (zero-indexed). If the line item does not exist, :meth:`add_line` must
        be called first.
        """
        return self._textbox("#serviceDate-%d" % li, val)

    def gl_account(self, li, val=None):
        """
        Get or set the field 'G/L Account' for the specified line item.
        """
        return self._textbox("#glAccount-%d" % li, val)

    def cost_object(self, li, val=None):
        """
        Get or set the field 'Cost Object' for the specified line item.
        """
        return self._textbox("#costObject-%d" % li, val)

    def amount(self, li, val=None):
        """
        Get or set the field 'Amount' for the specified line item.
        """
        return self._textbox("#amount-%d" % li, val)

    def explanation(self, li, val=None):
        """
        Get or set the field 'Explanation' for the specified line item.
        """
        return self._textbox("#description-%d" % li, val)

    def add_line(self):
        """
        Click the 'Add Line' button. Does not cause a page reload.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss("#addLine").click()

    def office_note(self, val=None):
        """
        Get or set the field 'Note to Central Office'.
        """
        return self._textbox("#messageForAP", val)

    def save(self):
        """
        Click the 'Save & Continue' button. Return an instance of
        :class:`AttachReceiptPage`.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss(".saveAction").click()
        self._pre_transition()
        return AttachReceiptPage(self.browser)

class ViewAndEditPage(RequestRfpPage):
    """
    An editable RFP, either newly-created or in the inbox. Not an entry page.
    """
    help_urls = ["http://insidemit.mit.edu/help-apps/rfp_reimbursement.shtml",
                 "http://insidemit.mit.edu/help-apps/rfp_payment.shtml"]

    def rfp_number(self):
        """
        Get the field 'RFP Number' in the payment details section.
        """
        return self._datalist("RFP Number")

    def payee(self):
        """
        Get the field 'Payee' in the payment details section.
        """
        return self._datalist("Payee")

    def charge_to(self):
        """
        Get the field 'Charge to' in the payment details section.
        """
        return self._datalist("Charge to")

    def ssn_tin(self):
        """
        Get the field 'SSN/TIN' in the tax information section.

        Non-MIT payees only.
        """
        return self._datalist("SSN/TIN")

    def attach_receipt(self):
        """
        Click 'Attach Receipt'. Return an instance of
        :class:`AttachReceiptPage`.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss(".attachReceipts").click()
        # Do not perform checking because errors on this page will persist.
        return AttachReceiptPage(self.browser)

    def save(self):
        """
        Click 'Save'. The page refreshes, but this object is still valid.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss(".saveAction").click()

    def send_to(self):
        """
        Click 'Send to'. Return an instance of :class:`SendToPage`.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss(".sendToAction").click()
        self._pre_transition()
        return SendToPage(self.browser)

class ViewOnlyPage(BasePage):
    """
    An RFP that cannot be edited, i.e. one accessed from search. Not an entry
    page.
    """
    help_urls = ["http://insidemit.mit.edu/help-apps/rfp_reimbursement.shtml",
                 "http://insidemit.mit.edu/help-apps/rfp_payment.shtml"]

    # Section: Current Status
    def inbox(self):
        """
        Get the field 'Inbox' in the current status section if shown, else
        return None.
        """
        return self._try_datalist("Inbox")

    # Section: Payment Details
    def rfp_number(self):
        """
        Get the field 'RFP Number' in the payment details section .
        """
        return self._datalist("RFP Number")

    def payee(self):
        """
        Get the field 'Payee' in the payment details section.
        """
        return self._datalist("Payee")

    def company_code(self):
        """
        Get the field 'Company Code' (a.k.a. 'Charge to') in the payment details
        section.
        """
        return self._datalist("Company Code")

    def rfp_name(self):
        """
        Get the field 'Name of RFP' in the payment details section.
        """
        return self._datalist("Name of RFP")

    def rfp_type(self):
        """
        Get the field 'Type of RFP' in the payment details section.
        """
        return self._datalist("Type of RFP")

    def payment_method(self):
        """
        Get the field 'Payment Method' in the payment details section.
        """
        return self._datalist("Payment Method")

    # Section: Payee's Tax Information / Mailing Instructions
    def mailing_instructions(self):
        """
        Get the description of the mailing instructions in the mailing
        instructions section if shown, else None.
        """
        try:
            browserxp = self.browser.find_element_by_xpath
            xpath = "//h2[normalize-space(.)='Mailing Instructions']" + \
                    "/following-sibling::div[@class='sectionContainer'][1]//h4"
            return browserxp(xpath).text
        except NoSuchElementException:
            return None

    def addressee(self):
        """
        Get the field 'Name' in the mailing instructions section if shown,
        else None.
        """
        return self._try_datalist("Name")

    def phone(self):
        """
        Get the field 'Phone' in the mailing instructions section if shown,
        else None.
        """
        return self._try_datalist("Phone")

    def address(self):
        """
        Get the field 'Address' if shown, else None.
        """
        return self._try_datalist("Address")

    def city(self):
        """
        Get the field 'City' if shown, else None.
        """
        return self._try_datalist("City")

    def state(self):
        """
        Get the field 'State/Region' if shown, else None.
        """
        return self._try_datalist("State/Region")

    def postal_code(self):
        """
        Get the field 'Postal Code' if shown, else None.
        """
        return self._try_datalist("Postal Code")

    def country(self):
        """
        Get the field 'Country' if shown, else None.
        """
        return self._try_datalist("Country")

    def tax_type(self):
        """
        Get the field 'Tax Entity Type' if shown, else None.
        """
        return self._try_datalist("Tax Entity Type")

    def ssn_tin(self):
        """
        Get the field 'SSN/TIN' if shown, else None.
        """
        return self._try_datalist("SSN/TIN")

    # Section: Line Items
    def line_item_count(self):
        """
        Get the number of line items displayed.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        return len(browsermulticss(".lineItem"))

    def date_of_service(self, li):
        """
        Get the field 'Date of Service' for the specified line item
        (zero-indexed).
        """
        return self._line_item_cells(li)[0].text

    def gl_account(self, li):
        """
        Get the field 'G/L Account' for the specified line item.
        """
        return self._line_item_cells(li)[1].text

    def cost_object(self, li):
        """
        Get the field 'Cost Object' for the specified line item.
        """
        return self._line_item_cells(li)[2].text

    def amount(self, li):
        """
        Get the field 'Amount' for the specified line item.
        """
        return self._line_item_cells(li)[3].text

    def explanation(self, li):
        """
        Get the field 'Explanation' for the specified line item.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        lidiv = browsermulticss(".lineItem")[li]
        lidivcss = lidiv.find_element_by_css_selector
        return lidivcss("div.data.indent1").text

    def _line_item_cells(self, li):
        """
        Get an ordered list of cells across the row of a line item.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        lidiv = browsermulticss(".lineItem")[li]
        lidivmulticss = lidiv.find_elements_by_css_selector
        return lidivmulticss("td")

    def office_note(self):
        """
        Get the field 'Note to Central Office', else return None.
        """
        try:
            browserxp = self.browser.find_element_by_xpath
            xpath = "//h3[normalize-space(.)='Note to Central Office']/" + \
                    "following-sibling::div[@class='sectionContainer'][1]"
            return browserxp(xpath).text
        except NoSuchElementException:
            return None


    def attach_receipt(self):
        """
        Click 'Attach Receipt'. Return an instance of
        :class:`AttachReceiptPage`.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss(".attachReceipts").click()
        # Do not perform checking because errors on this page will persist.
        return AttachReceiptPage(self.browser)

    def history(self):
        """
        Get the section 'RFP History' as a list of tuples: (date, time, action).
        """
        browsercss = self.browser.find_elements_by_css_selector
        historydiv = browsercss(".topHeadersTable")[-1]
        historydivmulticss = historydiv.find_elements_by_css_selector
        cells = historydivmulticss("td")
        result = list()
        for i in range(0, len(cells), 3):
            date = cells[i].text
            time = cells[i+1].text
            action = cells[i+2].text
            result.append((date, time, action))
        return result

class AttachReceiptPage(BasePage):
    """
    The receipt upload overlay; treated as a separate page. Not an entry page.
    """
    help_url = "http://insidemit.mit.edu/help-apps/rfp_reimbursement.shtml"

    def __init__(self, browser):
        super(AttachReceiptPage, self).__init__(browser)
        browsercss = self.browser.find_element_by_css_selector
        if not browsercss("#doUpload").is_displayed():
            raise FailedTransitionError("Attachment popup is not shown.")

    def select_file(self, path):
        """
        Browse to the given path for a file to upload.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss("#upload").send_keys(path)

    def cancel(self):
        """
        Click the 'Cancel' button. Return an instance of
        :class:`ViewAndEditPage`.
        """
        return self._overlay_button("Cancel")

    def attach(self):
        """
        Click the 'Attach' button. Return an instance of
        :class:`ViewAndEditPage`.
        """
        return self._overlay_button("Attach")

    def _overlay_button(self, text):
        """
        Click the button in the .ui-dialog overlay with the given text
        displayed. Return an instance of :class:`ViewAndEditPage`.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        buttons = browsermulticss(".ui-dialog button")
        for button in buttons:
            if button.text == text:
                button.click()
                break
        else:
            raise NoSuchElementException("Cancel button not found.")
        # NOTE: if the upload fails, we will end up on a ViewxxxPage, but
        # if an error is raised, the page object would still be an
        # AttachReceiptPage. So, we will not check if the upload succeeded.
        # Here, the user is responsible for checking .errors()
        if 'Display RFP' in self.browser.title:
            return ViewOnlyPage(self.browser)
        else:
            return ViewAndEditPage(self.browser)

class SendToPage(BasePage):
    """
    The Send To page, including search and search results. Not an entry page.
    """
    help_url = "http://insidemit.mit.edu/help-apps/rfp_send_to.shtml"

    def return_to_rfp(self):
        """
        Click the 'Return to RFP' link. Return an instance of
        :class:`ViewAndEditPage`.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss("a[href='ReturnToRfp.action']").click()
        self._pre_transition()
        return ViewAndEditPage(self.browser)

    def recipient_name(self, val=None):
        """
        Get or set the field 'Recipient's Name'.
        """
        return self._textbox("#recipientName", val)

    def search(self):
        """
        Click the 'Search' button. Results load in the same page.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss(".searchForRecipient").click()

    def results(self, index=None):
        """
        Get a list of search results or select one.

        If index is None or not specified: return an ordered list of search
        results, if any are displayed. Results are usually in the form
        "Name (kerberos,department)".

        If index is not None: select a search result, treating `index` as
        specifying a result by its zero-indexed position in the list.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        results = browsermulticss("td.data label[for^='addressee-']")
        if index is None:
            return [result.text.strip() for result in results]
        else:
            results[index].click()

    def note(self, val=None):
        """
        Get or set the field 'Note to Recipient'.
        """
        return self._textbox("#recipientNote", val)

    def send(self):
        """
        Click the 'Send' button. Return an instance of :class:`ViewOnlyPage`.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss(".sendToAction").click()
        self._pre_transition()
        return ViewOnlyPage(self.browser)

class SearchPage(BasePage):
    """
    The Search for RFP page. Entry page.
    """
    entry_url = "https://insidemit-apps.mit.edu/apps/rfp/SearchEntry.action?sapSystemId=PS1"
    help_url = "http://insidemit.mit.edu/help-apps/rfp_search.shtml"

    def rfp_types(self, parked=None, posted=None, deleted=None):
        """
        Get or set the field 'RFP Types', represented as a tuple of booleans:
        (Parked, Posted, Deleted).
        """
        Is_parked = self._checkbox("#parked", parked)
        is_posted = self._checkbox("#posted", posted)
        is_deleted = self._checkbox("#deleted", deleted)
        return (is_parked, is_posted, is_deleted)

    def company_code(self, val=None):
        """
        Get or set the field 'Company Code'.
        """
        return self._select("#coCode", val)

    def rfp_number(self, val=None):
        """
        Get or set the field 'RFP Number'.
        """
        return self._textbox("#rfpNumber", val)

    def creation_start(self, val=None):
        """
        Get or set the start of the range 'Creation Date(s)'.
        """
        return self._textbox("#creationStartDate", val)

    def creation_end(self, val=None):
        """
        Get or set the end of the range 'Creation Date(s)'.
        """
        return self._textbox("#creationEndDate", val)

    def payee(self, val=None):
        """
        Get or set the field 'Payee'.
        """
        return self._textbox("#payee", val)

    def rfp_name(self, val=None):
        """
        Get or set the field 'RFP Name'.
        """
        return self._textbox("#filingLabel", val)

    def cost_object(self, val=None):
        """
        Get or set the field 'Cost Object #'.
        """
        return self._textbox("#costObject", val)

    def gl_account(self, val=None):
        """
        Get or set the field 'G/L Account #'.
        """
        return self._textbox("#glAccount", val)

    def search(self):
        """
        Click the 'Search' button. If multiple results are found, return an
        instance of :class:`SearchPage` listing the results; otherwise, return
        an instance of :class:`ViewOnlyPage`.
        """
        browsercss = self.browser.find_element_by_css_selector
        browsercss("#searchButton").click()
        self._pre_transition()
        if "Display RFP" in self.browser.title:
            return ViewOnlyPage(self.browser)
        else:
            return self

    def results(self, index=None):
        """
        Get a list of search results or select one.

        If index is None or not specified: return an ordered list of RFP
        numbers found in the search.

        If index is not None: select a search result, treating `index` as
        specifying a result by its zero-indexed position in the list. Return an
        instance of :class:`ViewOnlyPage`.

        Note: RFP number displayed on this page may contain a leading zero not
        shown elsewhere.
        """
        browsermulticss = self.browser.find_elements_by_css_selector
        results = browsermulticss("td.data a[href^='SearchDrillDown']")
        if index is None:
            return [result.text.strip() for result in results]
        else:
            results[index].click()
            self._pre_transition()
            return ViewOnlyPage(self.browser)

    def result_creation_date(self, rfp):
        """
        Get the field 'Creation Date' for the specified RFP.
        """
        return self._row_element(rfp)[1].text

    def result_payee(self, rfp):
        """
        Get the field 'Payee' for the specified RFP.
        """
        return self._row_element(rfp)[2].text

    def result_created_by(self, rfp):
        """
        Get the field 'Created by' for the specified RFP.
        """
        return self._row_element(rfp)[3].text

    def result_rfp_name(self, rfp):
        """
        Get the field 'RFP Name' for the specified RFP.
        """
        return self._row_element(rfp)[4].text

    def result_location_status(self, rfp):
        """
        Get the field 'Location/Status' for the specified RFP.
        """
        return self._row_element(rfp)[5].text

    def result_cost_object(self, rfp):
        """
        Get the field 'Cost Object' for the specified RFP.
        """
        return self._row_element(rfp)[6].text

    def result_amount(self, rfp):
        """
        Get the field 'Amount' for the specified RFP.
        """
        return self._row_element(rfp)[7].text

class FailedTransitionError(Exception):
    """
    The browser was expected to load a page transition to the next page, but
    something went wrong.
    """
    pass
