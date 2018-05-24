import os
import ui
from vperson import VPerson, Answer
import tornado.httpserver
import tornado.ioloop
import tornado.web
import xml.etree.ElementTree as ET
from twilio.twiml.messaging_response import Message, MessagingResponse


ACCOUNT_SID = "AC17f854bd01970aab68b981a47b8e4b51"
ACCOUNT_TOKEN = "5422517ccbeb628e6bfccbc76eddeb49"

TWILIO = False


class Engine(VPerson):
    def init(self, *args):
        """helper function to display init; return value used to set ident key in sessions dictionary; see post method
        args path to xml element element; elements divided by "/"

        :returns dict of init_text, ident, *args
        """
        resp = self.request()
        xml = ET.fromstring(resp.content)
        ident = xml.find('ident').text
        init_text = AnswerParts(resp)

        d = {'ident': ident, 'init_text': init_text}

        # extra args from xml
        for val in args:
            key = val.split('/')[-1]
            if xml.find(val):
                d[key] = xml.find('val').text

        return d

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
    timer = None

    def initialize(self, active_close=None):
        self.engine = Engine("https://vastage1.creativevirtual15.com/quarkstaging/bot.htm")


    def get(self):
        init = self.engine.init('autosubmitmode', 'autosubmitwaittime')
        ident = init['ident']
        answer = init['init_text']
        if init.get('autosubmitmode') == 'true':
            self.timer = int(init.get('autosubmitwaittime', 0))


        # Inital request is get request;
        # Store engine reference, auto submit timer, convo history
        self.sessions[ident] = {
            'engine': self,
            'entries': [('', answer)],
            'timer': self.timer
        }

        self.render('index.html', ident=ident, entries=self.sessions[ident]['entries'])

    def post(self, *args, **kwargs):
        if not TWILIO:
            question = self.get_argument('input-bar')
            ident = self.get_argument('ident')
            session = self.sessions[ident]
            try:
                answer = session['engine'].engine.ask(question, use_parts=True)
            except KeyError:
                self.write('Your session has expired.')
                return

            session['entries'].append((question, answer))
            session['timer'] = self.timer

            self.render('index.html', ident=ident, entries=session['entries'])

            print (self.sessions.keys())

        else:
            question = self.get_argument('Body')
            from_num = self.get_argument('From')

            if from_num not in self.sessions:
                self.sessions[from_num] = self

            answer = self.sessions[from_num].engine.ask(question, use_parts=True)
            response = MessagingResponse()
            for part in answer:
                message = Message()
                message.body(str(part))
                response.append(message)

            self.write(str(response))


# class ActiveCloseTimer(tornado.ioloop.PeriodicCallback):
#     def __init__(self):
#         super(ActiveCloseTimer, self).__init__(self._process(MainHandler.sessions), 1000)
#
#     def _process(self, sessions):
#         """Check each sessions timer and decrease by one; when timer reaches 0 active close is triggered"""
#         for session in sessions:
#             if session.get('timer'):
#                 session['timer'] -=1
#
#             if session['timer'] <= 0:
#                 



def main():

    if not TWILIO:
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

    else:
        settings = {}

    application = tornado.web.Application([
        (r"/", MainHandler),
    ], **settings)

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(int(os.environ.get('PORT', 5000)))
    tornado.ioloop.IOLoop.instance().start()


# class
if __name__ == '__main__':
    main()
