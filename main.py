import os
from vperson import VPerson
import tornado.httpserver
import tornado.ioloop
import tornado.web


class MainHandler(tornado.web.RequestHandler):
    sessions = []

    def initialize(self):
        self.engine = VPerson("https://vastage1.creativevirtual15.com/coxstaging/bot.htm")

    def get(self):
        self.question = self.get_argument('question')
        answer = self.engine.ask(self.question)
        self.write(str(answer))

    # def post(self):
    #




def main():
    application = tornado.web.Application([
        (r"/ask", MainHandler),
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    port = 8888
    http_server.listen(port, address='127.0.0.1')
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
