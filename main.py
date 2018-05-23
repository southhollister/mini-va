import os
import ui
from vperson import VPerson, Answer
import tornado.httpserver
import tornado.ioloop
import tornado.web
import xml.etree.ElementTree as ET


class Engine(VPerson):
    def init(self):
        resp = self.request()
        xml = ET.fromstring(resp.content)
        ident = xml.find('ident').text
        init_text = AnswerParts(resp)

        return {'ident': ident, 'init_text': init_text}

    def ask(self, question, use_parts=False):
        """shortcut method for asking a text question and getting a text answer"""
        resp = self.request(entry=question)
        if not use_parts:
            return Answer(resp)
        else:
            return AnswerParts(resp)


class AnswerParts(object):
    """
    Iterable object; list of answer part texts
    """
    def __init__(self, response):
        self.answer_parts = []
        response_xml = ET.fromstring(response.content)
        self._process_request(response_xml)

    def _process_request(self, xml):
        for part in xml.findall('answerparts/answerpart/text'):
            self.answer_parts.append(part.text.replace('&amp;', '&'))

    def __iter__(self):
        self._idx = 0
        return self

    def next(self):
        self._idx += 1
        try:
            return self.answer_parts[self._idx-1]
        except IndexError:
            self._idx = 0
            raise StopIteration

    __next__ = next

    def __len__(self):
        return len(self.answer_parts)

    def __getitem__(self, item):
        return self.answer_parts[item]

    def __str__(self):
        return '\n\n'.join(self.answer_parts)

    __repr__ = __str__


class MainHandler(tornado.web.RequestHandler):

    sessions = {}
    entries = []

    def initialize(self):
        self.engine = Engine("https://vastage1.creativevirtual15.com/quarkstaging/bot.htm")

    def get(self):
        init = self.engine.init()
        ident = init['ident']
        answer = init['init_text']

        if ident not in self.sessions:
            del self.entries[:]

        self.sessions[ident] = self
        self.entries.append(('', answer))

        self.render('index.html', ident=ident, entries=self.entries)

    def post(self, *args, **kwargs):
        question = self.get_argument('input-bar')
        ident = self.get_argument('ident')

        try:
            answer = self.sessions[ident].engine.ask(question, use_parts=True)
        except KeyError:
            self.write('Your session has expired.')
            return

        self.entries.append((question, answer))
        # TODO Set up to use twillio or some othe service
        self.render('index.html', ident=ident, entries=self.entries)


def main():

    settings = dict(
        ui_modules=ui,
        cookie_secret=str(os.urandom(45)),
        template_path=os.path.join(os.path.dirname(__file__), 'templates'),
        static_path=os.path.join(os.path.dirname(__file__), 'static'),
        xsrf_cookies=True,
        autoreload=True,
        gzip=True,
        debug=True,
        autoescape=None
    )
    application = tornado.web.Application([
        (r"/", MainHandler),
    ], **settings)

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(int(os.environ.get('PORT', 5000)))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
