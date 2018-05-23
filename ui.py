import tornado.web


class TextBubble(tornado.web.UIModule):
    def css_files(self):
        return ['css/style.css']

    def render(self, answer_text):
        return self.render_string('text-bubble.html', answer_text=str(answer_text))


class BotText(TextBubble):

    def render(self, **kwargs):
        return self.render_string(
            'bot_text.html',
            text=str(kwargs['text']),
            extra_classes=' '.join(kwargs.get('extra_classes', []))
        )
