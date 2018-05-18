import os
from vperson import VPerson
import tornado.httpserver
import tornado.ioloop
import tornado.web


class MainHandler(tornado.web.RequestHandler):
    sessions = {}

    def initialize(self):
        self.engine = VPerson("https://vastage1.creativevirtual15.com/coxstaging/bot.htm")

    def get(self):
        self.question = self.get_argument('question')
        self.ident = self.get_arguments('ident')
        # self.write(str(self.ident))

        # if an ident is in the request grab it
        if self.ident:
            self.ident = self.ident[-1]
        # else get an ident for this new session and store session
        else:
            self.engine.request()
            self.ident = self.engine._params['ident']
            self.sessions[self.ident] = self

        session = self.sessions[self.ident]
        answer = session.engine.ask(self.question)
        self.write('ident=%s \n\n Answer Text:\n %s' % (self.ident, str(answer)))


def main():
    application = tornado.web.Application([
        (r"/ask", MainHandler),
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(int(os.environ.get('PORT', 5000)))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
