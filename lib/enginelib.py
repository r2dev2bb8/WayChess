import time
import threading
import os

import chess
import chess.engine
import pygame.gfxdraw as gfx

class AnalysisDisplay:
    def __init__(self):
        self.queue = []

    def raw_display(self, i, info):
        print("og analysis")
        print(i, info, '\n')

    def pre_display(self):
        pass

    def print(self):
        first3 = self.queue[:3]
        self.pre_display()
        if len(first3) == 3:
            for i, info in enumerate(first3, 1):
                self.raw_display(i, info)
                self.queue.pop(0)
            self.post_display()


    def post_display(self):
        print('\n')

    def clear(self):
        self.queue[:] = []

    def add(self, info, board):
        if info.get("score") is not None:
            ogboard = board.copy()
            for i, move in enumerate(info.get("pv")):
                board.push(move)
            san = ogboard.variation_san(board.move_stack)
            score = str(info.get("score"))
            score = score if ogboard.turn else flip_eval(score)
            
            self.queue.append(
                    f"{score} {info.get('depth')} {san}"
            )
            self.print()


def flip_eval(ev):
    """Flips the evaluation from + to - and - to +"""
    if '+' in ev:
        return ev.replace('+', '-')
    return ev.replace('-', '+')


def analysis(engine, display, board=chess.Board(), end=lambda:False):
    """
    Syncronous analysis for use in a threading.Thread
                                                                        
    :param engine: the awaited chess.engine.popen_uci engine
    :param display: the display queue for analysis
    :param board: the chess.Board() of the position
    :param end: the function telling whether to stop analysis
    """
    try:
        with engine.analysis(board, multipv=3) as analysis:
            for info in analysis:
                display.add(info, chess.Board(board.fen()))

                if end():
                    return
    except:
        return


# async def analysis(engine, display, board=lambda: chess.Board(), end = lambda : False):
#     """
#     Asyncronous analysis
# 
#     :param engine: the awaited chess.engine.popen_uci engine
#     :param display: the display queue for analysis
#     :param board: the function to get the chess.Board() of the position
#     :param end: the function telling whether to stop analysis
#     """
#     # transport, engine = await chess.engine.popen_uci("Engines/stockfish_bmi2.exe")
# 
#     og = board()
# 
#     with await engine.analysis(og, multipv=3) as analysis:
#         async for info in analysis:
#             b = board()
#             if b != og:
#                 await analysis(engine, display, board, end)
#             await display.add(info, chess.Board(b.fen()))
# 
#             if end():
#                 break

def wrap_iter(string, length=150):
    # yield string[:length]
    for i in range(len(string)//length+1):
        yield string[length*i: length*(i+1)]


def wrap(string, length=150):
    return '\n'.join(wrap_iter(string, length))


class GUIAnalysis(AnalysisDisplay):
    def __init__(self, gui):
        self.queue = []
        self.gui = gui


    def pre_display(self):
        # self.gui.clear_analysis()
        pass


    def raw_display(self, i, info):
        sx, sy = 40, 595
        for j, text in enumerate(wrap_iter(str(i) + ' ' + info)):
            self.gui.render_raw_text(
                    text,
                    (sx, sy+i*50+j*20), self.gui.font_engine,
                    (234, 234, 234)
            )


    def post_display(self):
        pass
        # self.gui.refresh()


class GUI:
    engine_panel = [
            (35, 590), (515, 590),
            (515, 755), (35, 755)
    ]

    def clear_analysis(self):
        gfx.filled_polygon(self.screen, GUI.engine_panel, (21, 21, 21))

    def set_analysis(self):
        beg = time.time()
        if not hasattr(self, "engine"):
            print("Opening engine")
            self.engine = chess.engine.SimpleEngine.popen_uci("Engines/stockfish_bmi2.exe")
            # self.engine.configure({"MultiPV": 3})
        # _, self.engine = await chess.engine.popen_uci("Engines/stockfish_bmi2.exe")
        self.is_analysing = True
        self.analysis_display = GUIAnalysis(self)
        assert type(self.analysis_display) is GUIAnalysis
        def get_end():
            nonlocal self
            return not self.is_analysing
        self.analysis_service = threading.Thread(target=analysis,
                args = (self.engine, self.analysis_display, self.board, get_end),
                daemon=True
        )
        self.analysis_service.start()
        print("set analysis callback started in", time.time()-beg, "seconds")

    def stop_analysis_task(self):
        self.is_analysing = False
        self.show_engine = False
        try:
            beg = time.time()
            self.analysis_service.join()
            print(time.time()-beg, "seconds taken to stop analysis")
        except AttributeError:
            return

    def stop_analysis(self):
        try:
            threading.Thread(self.stop_analysis_task).start()
        except Exception as e:
            print(e)

    def engine_callback(self):
        # try:
            # print("calling engine callback", self.show_engine)
        # except AttributeError:
            # print("calling engine callback", "undefined")
        try:
            if not self.show_engine:
                # print("gone down engine_callback")
                self.show_engine = True
                self.set_analysis()
            else:
                # print("stopping analysis")
                self.stop_analysis()
                # print("show_engine changed to", self.show_engine)
        except AttributeError:
            self.show_engine = True
            self.set_analysis()
    

def main():
    engine = chess.engine.SimpleEngine.popen_uci("Engines/stockfish_bmi2.exe")
    analysis(engine, AnalysisDisplay())
    engine.quit()


if __name__ == "__main__":
    main()

