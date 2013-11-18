"""
    sap_profiles
    ~~~~~~~~~~~~

    The `sap_profiles` module includes utility methods to create and load
    Selenium browser profiles configured for use with SAPweb.
"""

import os
import shutil
import sys

from selenium import webdriver

DEFAULT_PROFILE = os.path.join("~", ".pysapwebprofile")
CA_URL = "https://ca.mit.edu/"
EXTENSION_URL = "https://addons.mozilla.org/en-us/firefox/addon/startupmaster/"

def create_firefox_profile(profile_dir=DEFAULT_PROFILE, overwrite=False):
    """
    Guide the user through setting up a Firefox profile for use with pysapweb.
    This involves two steps: installing an MIT certificate, and installing an
    extension to prompt for the Firefox Master Password on startup. (The
    extension is necessary because if Firefox prompts for this password during
    a page load, Selenium will lose its handle on the page.)
    """
    profile_dir = os.path.expanduser(profile_dir)
    if os.path.exists(profile_dir):
        if overwrite:
            shutil.rmtree(profile_dir)
        else:
            raise OSError("Profile directory %s already exists." % profile_dir)

    profile = webdriver.FirefoxProfile()
    profile.accept_untrusted_certs = False
    profile.set_preference("security.default_personal_cert",
                           "Select Automatically")
    profile.set_preference("datareporting.healthreport.uploadEnabled",
                           False)
    profile.set_preference("places.history.enabled",
                           False)

    print ""
    print "  1. Please load a certificate into the browser and set"
    print "     a master password."
    print ""
    sys.stdout.write("    - Starting Firefox...")
    browser = webdriver.Firefox(profile)
    browser.get(CA_URL)
    print "Done"
    raw_input("    - To continue, press ENTER.")

    print ""
    print "  2. Please accept installation of the extension, but"
    print "     do not restart."
    print ""
    browser.get(EXTENSION_URL)
    browser.find_element_by_css_selector(".prominent.installer").click()
    raw_input("    - To continue, press ENTER.")

    # don't use browser.quit() b/c removes profile dir
    browser.binary.kill()

    temp_dir = browser.firefox_profile.path
    shutil.move(temp_dir, profile_dir)

    # delete extension to avoid future errors
    shutil.rmtree(os.path.join(profile_dir, "extensions",
                               "fxdriver@googlecode.com"))
    print "    - Profile created successfully!"

def load_firefox(profile_dir=DEFAULT_PROFILE):
    """Return a WebDriver instance with the given Firefox profile loaded."""
    profile_dir = os.path.expanduser(profile_dir)
    profile = webdriver.FirefoxProfile(profile_dir)
    browser = webdriver.Firefox(profile)
    return browser
