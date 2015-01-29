"""generic DDNS authenticator (RFC 2136)"""
import logging
import subprocess

import zope.interface

from letsencrypt.client import challenge_util
from letsencrypt.client import interfaces


# TODO: make practical use of this, nothing uses DDNS yet
class DDNS(object):
    """DDNS authenticator.

    """
    zope.interface.implements(interfaces.IAuthenticator)

    def get_chall_pref(self, unused_domain):  # pylint: disable=no-self-use
        """Return list of challenge preferences."""
        return ["dns"]

    def perform(self, chall_list):  # pylint: disable=no-self-use
        """Perform the configuration related challenge.

        :param list chall_list: List of challenges to be
            fulfilled by configurator.

        :returns: list of responses. All responses are returned in the same
            order as received by the perform function. A None response
            indicates the challenge was not performed.
        :rtype: list

        """
        responses = []

        for chall in chall_list:
            if isinstance(chall, challenge_util.DnsChall):
                try:
                    nsupdate("add", chall.domain, chall.token)
                except subprocess.CalledProcessError:
                    responses.append(None)
                else:
                    responses.append({"type": "dns"})
            else:
                responses.append(None)

        return responses

    def cleanup(self, chall_list):  # pylint: disable=no-self-use
        """Revert all challenges."""
        for chall in chall_list:
            if isinstance(chall, challenge_util.DnsChall):
                nsupdate("del", chall.domain, chall.token)


# TODO: add dnsutils to required/suggested packages
# TODO: make this user-configurable.
NSUPDATE_CMD = "nsupdate -k le-nsupdate.key"


def nsupdate(action, domain, token):
    """Invoke the nsupdate commandline tool to send a single DNS update

    :param str action: desired nameserver update operation, "add" or "del"
    :param str domain: domain to verify (no "." at the end, no acme prefix)
    :param str token: token to put into the TXT record

    :raises: subprocess.CalledProcessError if the call to nsupdate resulted
             in a non-zero return code

    """
    logging.debug("nsupdate cmd: %s", NSUPDATE_CMD)
    stdin = "update %s _acme-challenge.%s. 60 TXT %s\nsend\n" % (
        action, domain, token)
    logging.debug("nsupdate stdin: %s", stdin)
    process = subprocess.Popen(
        NSUPDATE_CMD.split(),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(input=stdin)
    retcode = process.poll()
    logging.debug("nsupdate rc: %d", retcode)
    logging.debug("nsupdate stdout: %s", stdout)
    logging.debug("nsupdate stderr: %s", stderr)
    if retcode != 0:
        raise subprocess.CalledProcessError(retcode, NSUPDATE_CMD,
                                            output=stderr)
