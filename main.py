import os
import sys
import math
import random
import traceback

# Nangkep semua error biar gak "force close" diam-diam,
# tapi ditulis ke file + ditampilin di layar.
def _global_excepthook(exc_type, exc_value, exc_tb):
    text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        with open(os.path.join(os.path.expanduser('~'), 'flappy_crash.log'), 'w') as f:
            f.write(text)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _global_excepthook

from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, StringProperty
from kivy.graphics import PushMatrix, PopMatrix, Rotate

BASE = os.path.dirname(os.path.abspath(__file__))

def asset(name):
    return os.path.join(BASE, 'assets', name)

GRAVITY = -1500.0
FLAP_V = 520.0
SPEED = 210.0
PIPE_W = 88.0
GAP = 250.0
SPAWN_EVERY = 2.0
BIRD_SIZE = 54.0


class ErrorScreen(BoxLayout):
    def __init__(self, text, **kw):
        super(ErrorScreen, self).__init__(orientation='vertical', **kw)
        self.padding = 16
        title = Label(text='TERJADI ERROR (screenshot & kirim ke dev)',
                      size_hint_y=0.12, font_size=20, bold=True, color=(1, 0.4, 0.4, 1))
        body = Label(text=text, font_size=14, halign='left', valign='top', color=(1, 1, 1, 1))
        body.bind(size=body.setter('text_size'))
        self.add_widget(title)
        self.add_widget(body)


class GameWidget(Widget):
    score = NumericProperty(0)
    best = NumericProperty(0)
    state = StringProperty('ready')

    def __init__(self, **kw):
        super(GameWidget, self).__init__(**kw)
        self.vy = 0.0
        self.spawn_t = 0.0
        self.t = 0.0
        self.ground_x = 0.0
        self.pipes = []
        self._load_best()

        self.bg = Image(source=asset('bg.png'), allow_stretch=True, keep_ratio=False)
        self.add_widget(self.bg)

        self.grounds = [
            Image(source=asset('ground.png'), allow_stretch=True, keep_ratio=False),
            Image(source=asset('ground.png'), allow_stretch=True, keep_ratio=False),
        ]
        for g in self.grounds:
            self.add_widget(g)

        self.bird = Image(source=asset('bird.png'), allow_stretch=True, keep_ratio=True,
                          size_hint=(None, None), size=(BIRD_SIZE, BIRD_SIZE))
        with self.bird.canvas.before:
            PushMatrix()
            self.bird_rot = Rotate(angle=0, axis=(0, 0, 1), center=self.bird.center)
        with self.bird.canvas.after:
            PopMatrix()
        self.add_widget(self.bird)

        self.score_lbl = Label(text='0', font_size=54, bold=True,
                               size_hint=(None, None), size=(240, 80),
                               color=(1, 1, 1, 1),
                               outline_color=(0, 0, 0, 0.8), outline_width=2)
        self.add_widget(self.score_lbl)

        self.msg = Label(text='FLAPPY NEON\n\nTap layar untuk mulai',
                         font_size=30, bold=True, halign='center', valign='middle',
                         size_hint=(None, None), size=(420, 200),
                         color=(1, 1, 1, 1),
                         outline_color=(0, 0, 0, 0.8), outline_width=2)
        self.add_widget(self.msg)

        self.restart_btn = Button(text='MAIN LAGI', font_size=24, bold=True,
                                  size_hint=(None, None), size=(220, 64),
                                  background_color=(0.2, 0.85, 0.45, 1),
                                  color=(0, 0, 0, 1))
        self.restart_btn.bind(on_release=self._on_restart)
        self.add_widget(self.restart_btn)

        self._reset_world()
        Clock.schedule_interval(self._safe_update, 1.0 / 60.0)

    def ground_h(self):
        return max(56.0, self.height * 0.09)

    def on_size(self, *_):
        if not hasattr(self, 'bg'):
            return
        W, H = self.size
        gh = self.ground_h()
        self.bg.pos = (0, 0)
        self.bg.size = self.size
        for g in self.grounds:
            g.size = (W, gh)
            g.y = 0
        self.bird.x = W * 0.28
        if self.state == 'ready':
            self.bird.center_y = H * 0.55
        self.score_lbl.x = (W - self.score_lbl.width) / 2
        self.score_lbl.y = H - self.score_lbl.height - 14
        self.msg.center = (W / 2, H * 0.60)
        self.msg.text_size = self.msg.size
        self.restart_btn.center = (W / 2, H * 0.34)

    def _reset_world(self):
        for p in self.pipes:
            self.remove_widget(p['top'])
            self.remove_widget(p['bot'])
        self.pipes = []
        self.score = 0
        self.score_lbl.text = '0'
        self.vy = 0.0
        self.spawn_t = SPAWN_EVERY * 0.4
        self.state = 'ready'
        self.bird.center_y = self.height * 0.55
        self.bird_rot.angle = 0
        self.msg.text = 'FLAPPY NEON\n\nTap layar untuk mulai'
        self.msg.text_size = self.msg.size
        self.msg.opacity = 1
        self.restart_btn.opacity = 0
        self.restart_btn.disabled = True

    def _spawn_pipe(self):
        W, H = self.size
        gh = self.ground_h()
        margin = 70
        lo = gh + GAP / 2 + margin
        hi = H - GAP / 2 - margin
        if hi <= lo:
            hi = lo + 10
        gap_y = random.uniform(lo, hi)

        top = Image(source=asset('pipe_top.png'), allow_stretch=True, keep_ratio=False,
                    size_hint=(None, None))
        bot = Image(source=asset('pipe_bottom.png'), allow_stretch=True, keep_ratio=False,
                    size_hint=(None, None))
        top.width = bot.width = PIPE_W
        top.x = bot.x = W + 20
        top.y = gap_y + GAP / 2
        top.height = H - top.y + 30
        bot.y = gh - 14
        bot.height = (gap_y - GAP / 2) - bot.y

        self.add_widget(bot, index=len(self.children) - 1)
        self.add_widget(top, index=len(self.children) - 1)
        self.pipes.append({'top': top, 'bot': bot, 'scored': False})

    def on_touch_down(self, touch):
        if super(GameWidget, self).on_touch_down(touch):
            return True
        if self.state == 'ready':
            self.state = 'play'
            self.msg.opacity = 0
            self.vy = FLAP_V
        elif self.state == 'play':
            self.vy = FLAP_V
        return True

    def _on_restart(self, *_):
        if self.state == 'dead':
            self._reset_world()

    def _safe_update(self, dt):
        try:
            self._update(dt)
        except Exception:
            Clock.unschedule(self._safe_update)
            self.clear_widgets()
            self.add_widget(ErrorScreen(traceback.format_exc()))

    def _update(self, dt):
        dt = min(dt, 0.05)
        W, H = self.size
        if W < 100 or H < 100:
            return
        gh = self.ground_h()
        speed = SPEED + min(140.0, self.score * 5.0)

        if self.state != 'dead':
            self.ground_x = (self.ground_x - speed * dt) % W
            self.grounds[0].x = self.ground_x - W
            self.grounds[1].x = self.ground_x

        if self.state == 'ready':
            self.t += dt
            self.bird.center_y = H * 0.55 + 10 * math.sin(self.t * 3.0)
            self.bird_rot.center = self.bird.center
            self.bird_rot.angle = 0
            return

        if self.state == 'dead':
            if self.bird.y > gh:
                self.vy += GRAVITY * dt
                self.bird.y = max(gh, self.bird.y + self.vy * dt)
                self.bird_rot.center = self.bird.center
                self.bird_rot.angle = max(-90.0, self.bird_rot.angle - 300.0 * dt)
            return

        self.vy += GRAVITY * dt
        self.bird.y += self.vy * dt
        if self.bird.top > H + 40:
            self.bird.top = H + 40
            if self.vy > 0:
                self.vy = 0
        ang = max(-70.0, min(32.0, self.vy * 0.06))
        self.bird_rot.center = self.bird.center
        self.bird_rot.angle = ang

        self.spawn_t += dt
        if self.spawn_t >= SPAWN_EVERY:
            self.spawn_t = 0.0
            self._spawn_pipe()

        bx1 = self.bird.x + 10
        by1 = self.bird.y + 10
        bx2 = self.bird.right - 10
        by2 = self.bird.top - 10

        dead = False
        for p in self.pipes[:]:
            p['top'].x -= speed * dt
            p['bot'].x -= speed * dt
            if not p['scored'] and p['top'].x + PIPE_W < self.bird.x:
                p['scored'] = True
                self.score += 1
                self.score_lbl.text = str(self.score)
            if p['top'].x < -PIPE_W - 30:
                self.remove_widget(p['top'])
                self.remove_widget(p['bot'])
                self.pipes.remove(p)
                continue
            for img in (p['top'], p['bot']):
                if (bx1 < img.x + img.width and bx2 > img.x and
                        by1 < img.y + img.height and by2 > img.y):
                    dead = True
                    break
            if dead:
                break

        if dead:
            self._die()
            return

        if self.bird.y <= gh:
            self.bird.y = gh
            self._die()

    def _die(self):
        if self.state != 'play':
            return
        self.state = 'dead'
        if self.score > self.best:
            self.best = self.score
            self._save_best()
        self.msg.text = 'GAME OVER\n\nSkor : %d\nTerbaik : %d' % (self.score, self.best)
        self.msg.text_size = self.msg.size
        self.msg.opacity = 1
        self.restart_btn.opacity = 1
        self.restart_btn.disabled = False

    def _best_path(self):
        return os.path.join(os.path.expanduser('~'), '.flappy_neon_best')

    def _load_best(self):
        try:
            with open(self._best_path(), 'r') as f:
                self.best = int((f.read() or '0').strip())
        except Exception:
            self.best = 0

    def _save_best(self):
        try:
            with open(self._best_path(), 'w') as f:
                f.write(str(self.best))
        except Exception:
            pass


class FlappyNeonApp(App):
    def build(self):
        Window.clearcolor = (0.07, 0.04, 0.2, 1)
        try:
            return GameWidget()
        except Exception:
            return ErrorScreen(traceback.format_exc())


if __name__ == '__main__':
    FlappyNeonApp().run()
