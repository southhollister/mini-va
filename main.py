import os
import ui
from vperson import VPerson, Answer
import tornado.httpserver
import tornado.ioloop
import tornado.web
import xml.etree.ElementTree as ET
from twilio.twiml.messaging_response import Message, MessagingResponse
import requests


ACCOUNT_SID = "AC17f854bd01970aab68b981a47b8e4b51"
ACCOUNT_TOKEN = "5422517ccbeb628e6bfccbc76eddeb49"

TWILIO = True


class Engine(VPerson):
    def transaction(self, use_parts=True, *args, **kwargs):
        """helper function to display transaction; return value used to set ident key in sessions dictionary; see post method
        args path to xml element element; elements divided by "/"

        :returns dict of init_text, ident, *args
        """
        resp = self.request(kwargs)
        xml = ET.fromstring(resp.content)
        ident = xml.find('ident').text
        if use_parts:
            text = AnswerParts(resp)
        else:
            text = Answer(resp)

        d = {'ident': ident, 'text': text}

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
        init = self.engine.transaction('autosubmitmode', 'autosubmitwaittime')
        ident = init['ident']
        answer = init['text']
        # if transaction.get('autosubmitmode') == 'true':
        self.timer = 10  # int(transaction.get('autosubmitwaittime', 0))

        # Inital request is get request; TWILIO DOES NOT USE GET REQUESTS UNLESS CONFIGURED TO DO SO
        # Store engine reference, auto submit timer, convo history
        self.sessions[ident] = {
            'engine': self,
            'entries': [('', answer)],
            'timer': self.timer,
            'active_close_time': self.timer
        }

        self.render('index.html', ident=ident, entries=self.sessions[ident]['entries'])

    def post(self, *args, **kwargs):
        if not TWILIO:
            question = self.get_argument('input-bar')
            ident = self.get_argument('ident')
            xsrf = self.get_argument('_xsrf')

            session = self.sessions[ident]
            try:
                answer = session['engine'].engine.ask(question, use_parts=True)
            except KeyError:
                self.write('Your session has expired.')
                return

            session['entries'].append((question, answer))
            session['timer'] = session['active_close_time']
            session['xsrf'] = xsrf

            self.render('index.html', ident=ident, entries=session['entries'])

            print (session)

        else:
            question = self.get_argument('Body')
            from_num = self.get_argument('From')

            if from_num not in self.sessions:
                self.sessions[from_num] = {
                    'engine': self,
                    'entries': []
                }

            session = self.sessions[from_num]
            # Make engine request
            res = session['engine'].engine.transaction('autosubmitmode', 'autosubmitwaittime', entry='question')

            # set up active close timer
            if res['autosubmitmode'] == 'true':
                session['timer'] = res['autosubmitwaittime']
            else:
                session['timer'] = None

            # grab answer text/parts
            answer = res['text']

            # keep convo history
            session['entries'].append((question, answer))

            response = MessagingResponse()
            for part in answer:
                message = Message()
                message.body(str(part))
                response.append(message)

            self.write(str(response))

            # store session
            self.sessions[from_num] = session


class ActiveCloseTimer(tornado.ioloop.PeriodicCallback):

    def __init__(self):
        super(ActiveCloseTimer, self).__init__(self._process, 1000)

    def _process(self):
        """Check each sessions timer and decrease by one; when timer reaches 0 active close is triggered"""
        sessions = MainHandler.sessions

        for ident in sessions:
            session = sessions[ident]
            #only run on post transaction session transactions
            if len(session['entries']) < 2:
                print 'skipping %s' % ident
                continue
            if session.get('timer'):
                session['timer'] -=1
                print session['timer']

            if session['timer'] is not None and session['timer'] <= 0:
                # url = os.environ.get('URL', 'localhost:5000')
                # params = {
                #     'ident': ident,
                #     'input_bar': 'autosubmission',
                #     '_xsrf': session['xsrf']
                # }
                # r = requests.post(url, params=params)

                r = session['engine'].engine.ask('autosubmission', use_parts=True)
                print r
                session['timer'] = None
                # print 'call active close'
                break

    # def handle_callback_exception(self):

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

    service = ActiveCloseTimer()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(int(os.environ.get('PORT', 5000)))
    # service.start()
    tornado.ioloop.IOLoop.instance().start()


# class
if __name__ == '__main__':
    main()
