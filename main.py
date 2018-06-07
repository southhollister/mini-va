import os
import ui
from vperson import VPerson, Answer
import tornado.httpserver
import tornado.ioloop
import tornado.web
import xml.etree.ElementTree as ET
from twilio.twiml.messaging_response import Message, MessagingResponse
from twilio.rest import Client
import requests


ACCOUNT_SID = os.environ.get('TWILIO_SID')
ACCOUNT_TOKEN = os.environ.get('TWILIO_TOKEN')
CLIENT = Client(ACCOUNT_SID, ACCOUNT_TOKEN)


class Engine(VPerson):
    def transaction(self, *args, **kwargs):
        """helper function to display transaction; return value used to set ident key in sessions dictionary; see post method
        args path to xml element element; elements divided by "/"

        :returns dict of init_text, ident, *args
        """
        resp = self.request(**kwargs)
        xml = ET.fromstring(resp.content)
        ident = xml.find('ident').text
        text = AnswerParts(resp)

        d = {'ident': ident, 'text': text}
        # print(xml.find(args[0]).text)
        # print(args)

        # extra args from xml
        for val in args:
            # key = val.split('/')[-1]
            if xml.find(val).text is not None:
                d[val] = xml.find(val).text

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


class WebHandler(tornado.web.RequestHandler):
    sessions = {}
    timer = None

    def initialize(self):
        self.engine = Engine("https://vastage1.creativevirtual15.com/quarkstaging/bot.htm")

    def get(self):
        init = self.engine.transaction('autosubmitmode', 'autosubmitwaittime')
        ident = init['ident']
        answer = init['text']
        self.timer = int(init.get('autosubmitwaittime', 0))

        # Store engine reference, auto submit timer, convo history
        self.sessions[ident] = {
            'engine': self,
            'entries': [('', answer)],
            'timer': self.timer,
            'active_close_time': self.timer
        }

        self.render('index.html', ident=ident, entries=self.sessions[ident]['entries'])

    def post(self, *args, **kwargs):

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


class SMSHandler(tornado.web.RequestHandler):

    sessions = {}
    timer = None

    def initialize(self):
        self.engine = Engine("https://vastage1.creativevirtual15.com/quarkstaging/bot.htm")

    def post(self, *args, **kwargs):

        question = self.get_argument('Body')
        from_num = self.get_argument('From')

        if from_num not in self.sessions:
            print('New Session @ %s' % from_num)
            self.sessions[from_num] = {
                'engine': self,
                'entries': []
            }

        session = self.sessions[from_num]
        # Make engine request
        res = session['engine'].engine.transaction('autosubmitmode', 'autosubmitwaittime', entry=question)
        print(res)
        try:
            # set up active close timer
            if res.get('autosubmitmode') == 'true' and session.get('timer', 0) is not None:
                session['timer'] = 10  # int(res['autosubmitwaittime'])
            else:
                session['timer'] = None

        except KeyError:
            print(res)
            exit()

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
        sessions = SMSHandler.sessions

        for ident in sessions:
            session = sessions[ident]
            # only run on post transaction session transactions
            if len(session['entries']) < 2:

                continue
            if session.get('timer'):
                session['timer'] -= 1
                print('%s || %s' % (ident, session['timer']))

            if session['timer'] is not None and session['timer'] <= 0:

                r = session['engine'].engine.ask('autosubmission', use_parts=True)
                print('%s || %s' % (ident, r))

                session['timer'] = None
                print('%s || call active close' % ident)
                message = CLIENT.messages.create(
                    to=ident,
                    from_='+12038729948',
                    body=r
                )
                print(message)


def main():

    settings = dict(
        ui_modules=ui,
        cookie_secret=str(os.urandom(45)),
        template_path=os.path.join(os.path.dirname(__file__), 'templates'),
        static_path=os.path.join(os.path.dirname(__file__), 'static'),
        # xsrf_cookies=True,
        autoreload=True,
        gzip=True,
        debug=True,
        autoescape=None
    )

    application = tornado.web.Application([
        (r"/", SMSHandler),
        (r'/web', WebHandler)
    ], **settings)

    service = ActiveCloseTimer()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(int(os.environ.get('PORT', 5000)))
    service.start()
    tornado.ioloop.IOLoop.instance().start()


# class
if __name__ == '__main__':
    main()
