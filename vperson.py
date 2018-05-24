from distutils.util import strtobool
import xml.etree.ElementTree as ET
import requests


class VPerson(object):
    """VPerson API"""

    _session_attrs = ('ident','userlogid')
    _default_params = dict(JSIN=1)

    def __init__(self, url, **kwargs):
        # type: (object, object) -> object
        self.base_url = url
        self._params = dict(self._default_params,**kwargs)

    def request(self, **params):
        resp = requests.get(self.base_url,
                            params=dict(self._params,**params), verify=False)
        xml = ET.fromstring(resp.content)
        for attr in self._session_attrs:
            self._params[attr] = xml.find(attr).text
        return resp

    def ask(self, question, use_parts=False):
        """shortcut method for asking a text question and getting a text answer"""
        resp = self.request(entry=question)
        if not use_parts:
            return Answer(resp)
        else:
            return AnswerParts(resp)


class Answer(object):

    def __init__(self, response):
        self.xml = ET.fromstring(response.content)
        self._process_response()

    @property
    def escalate(self):
        element = self.xml.find('livepersonchatoffer')
        return bool(strtobool(element.text)) if element is not None else False

    def _process_response(self):
        self.answer_text = self.xml.find('botanswer').text.replace('&amp;', '&')

    def __str__(self):
        return self.answer_text

    __unicode__ = __str__
