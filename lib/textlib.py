import itertools
import re
import sys
import time

import pygame.gfxdraw as gfx


def grouper_it(n, iterable):
    """
    Groups iterable by chunks of size n.

    Credit:
    https://stackoverflow.com/questions/8991506/iterate-an-iterator-by-chunks-of-n-in-python
    """
    it = iter(iterable)
    while 1:
        chunk_it = itertools.islice(it, n)
        try:
            first_el = next(chunk_it)
        except StopIteration:
            return
        yield itertools.chain((first_el,), chunk_it)


def get_variation_menu_coords(left, right, initial_y, delta_y, variations):
    """
    Returns a list of lists of the menu coordinates.

    :param left: the left x coordinate of the menu
    :param right: the right x coordinate of the menu
    :param initial_y: the top y value of the menu
    :param delta_y: the y size of each menu block
    :variations: the number of variations
    :return: a list of rectangle lists
    """
    coords = []
    for i in range(min(14, variations)):
        top_y = initial_y + i * delta_y
        bottom_y = top_y + delta_y
        coords.append(
            [(left, top_y), (right, top_y), (right, bottom_y), (left, bottom_y)]
        )
    return coords


def shift_variation_menu(coordlist, delta):
    """
    Shifts up a variation menu list to not have it exceed the screen.

    :param coordlist: the list of coordinate rectangles of the menu
    :param delta: the y distance between the menu items
    :return: None
    """
    coordcopy = coordlist[:]
    for coords in coordcopy:
        coords[:] = [(x, y - delta) for x, y in coords]
    return coordcopy


def get_variation_menu_item(coordlist, mouse_x, mouse_y):
    """
    Returns which menu item the mouse is in.

    :param coordlist: the list of coordinate rectangles of the menu
    :param mouse_x: the x coordinate of the mouse
    :param mouse_y: the y coordinate of the mouse
    :return: the index of the menu item or None
    """
    for i, coords in enumerate(coordlist):
        min_x = min(c[0] for c in coords)
        min_y = min(c[1] for c in coords)
        max_x = max(c[0] for c in coords)
        max_y = max(c[1] for c in coords)
        if min_x <= mouse_x <= max_x and min_y <= mouse_y <= max_y:
            return i


class GUI:
    moves_panel = [(580, 65), (750, 65), (750, 555), (580, 555)]
    hist_slot_height = 30

    def textlib_process_mouse_over(self, coords):
        """
        Processes mouse input for textlib.

        :param coords: the raw mouse coordinates
        :return: None
        """
        # Update the variation menu
        if self.display_variation_menu:
            var_menu_coords = self.__get_var_menu_coords()
            self.variation_menu_emphasis = get_variation_menu_item(
                var_menu_coords, *coords
            )
            self.draw_variation_menu()

    def textlib_process_mouse_click(self, coords):
        """
        Processes mouse click input for textlib.

        :param coords: the raw mouse coordinates
        :return: None
        """
        var_menu_coords = self.__get_var_menu_coords()
        loc = get_variation_menu_item(var_menu_coords, *coords)
        if self.display_variation_menu and loc is not None:
            self.node = self.node.variations[loc]
            self.move += 0.5
        elif self.display_variation_menu:
            self.display_variation_menu = False
            self.render_history()
        elif loc == 0:
            self.__initiate_variation_menu()

    def textlib_process_key_press(self, event):
        """
        Processes key press input for textlib.

        :param event: the key pres event
        :return: None
        """
        key = event.key

        # If ctrl is pressed, multiply key by -1
        if self.key_pressed[305] or self.key_pressed[306]:
            key *= -1

        # control right arrow
        if key == -275:
            if not self.display_variation_menu:
                self.__initiate_variation_menu()
        elif key == 274:
            if self.display_variation_menu:
                self.variation_menu_emphasis += 1
                self.variation_menu_emphasis %= min(14, len(self.node.variations))
                self.draw_variation_menu()
        elif key == 273:
            if self.display_variation_menu:
                self.variation_menu_emphasis -= 1
                self.variation_menu_emphasis %= min(14, len(self.node.variations))
                self.draw_variation_menu()
        elif key == 13 or key == 275:
            if self.display_variation_menu:
                self.node = self.node.variations[self.variation_menu_emphasis]
                self.move += 0.5

    def draw_variation_menu(self):
        if self.node.variations[1:]:
            try:
                coords = self.__get_var_menu_coords()
                for i, v, c in zip(itertools.count(), self.node.variations, coords):
                    try:
                        text = re.search(r"\((.+)\.\.\.\)", repr(v)).group(1)
                    except Exception:
                        text = ""
                    color = (
                        (0, 0, 0) if i != self.variation_menu_emphasis else (42, 42, 42)
                    )
                    gfx.filled_polygon(self.screen, c, color)
                    try:
                        self.render_text(
                            text, (None, c[0][1] + 5), True, color  # (None, y),
                        )
                    except Exception as e:
                        print(e)
            except AttributeError as e:
                self.stderr(e)

    def render_history(self):
        """
        Renders the history with autoscroll.

        To implement:
          * Move comments
          * Move marks eg. ! ?
        """
        with self.display_lock:
            if self.changed_hist:
                self.move_hist = self.render_history_task()
                self.changed_hist = False
            else:
                self.render_history_task(self.move_hist)

    def render_history_task(self, moves=None):
        """
        Renders the history with autoscroll.

        To implement:
          * Move comments
          * Move marks eg. ! ?
        """
        gfx.filled_polygon(self.screen, GUI.moves_panel, (21, 21, 21))
        game = self.node.game()

        try:
            if moves is None:
                moves = self.__get_move_text_history(
                    game, self.move, self.variation_path[1:]
                )
        except IndexError:
            moves = []
        except Exception:
            self.exit()

        y = 80
        move_amount = len(moves)
        if move_amount < 15:
            moves.extend([" " * 20] * (15 - move_amount))
        elif 8 <= int(self.move) < move_amount - 8:
            b = int(self.move - 0.5) - 8
            b = 0 if b < 0 else b
            moves = moves[b : int(self.move - 0.5) + 8]
        elif int(self.move) < 8:
            moves = moves[:15]

        moves = moves[-15:]
        for move in moves:
            # Highlight text if it is of the current move
            if move.startswith("\t"):
                b_left = GUI.moves_panel[0][0]
                b_right = GUI.moves_panel[1][0]

                # dy of -5 is needed to align the highlight
                dy = -5
                rect = [
                    (b_left, y + dy),
                    (b_right, y + dy),
                    (b_right, y + dy + GUI.hist_slot_height),
                    (b_left, y + dy + GUI.hist_slot_height),
                ]
                gfx.filled_polygon(self.screen, rect, (0, 0, 0))
                self._initial_variation_y = y + dy
            self.render_text(
                move.lstrip(),
                (None, y),
                True,
                (0, 0, 0) if move.startswith("\t") else (21, 21, 21),
            )
            y += GUI.hist_slot_height
        if "--always-variation" in sys.argv or self.display_variation_menu:
            self.draw_variation_menu()
        return moves

    def render_text(self, text, pos=(None, 20), small=False, background=(21, 21, 21)):
        """Renders text, centered by default"""
        SQUARE_SIZE = self.SQUARE_SIZE
        left_boundary = SQUARE_SIZE * 9
        if pos[0] is None:
            right_boundary = 600
            text_len = len(text)
            left = left_boundary + (right_boundary - left_boundary - text_len) // 2
            pos = (left, pos[1])
        font = self.font_small if small else self.font
        rendered = font.render(text, True, (255, 255, 255), background)
        # brendered = font.render('G'*100, True, (21, 21, 21), (21, 21, 21))
        # self.screen.blit(brendered, (left_boundary-5, pos[1]))
        self.screen.blit(rendered, pos)

    def render_raw_text(self, text, pos, font, color, background=(21, 21, 21)):
        rendered = font.render(text, True, color, background)
        self.screen.blit(rendered, pos)

    @staticmethod
    def __board_node_generator(beg, variation_path):
        """
        Returns the nodes of the game's main variation.

        :param beg: the beginning node
        :param variation_path: the path of which variations to fork on
                               ex: [0, 1, 0] means take variation
                                at index 1 on the second move
        :return: the generator with the nodes of the main variation
        """
        vp_iterator = iter(variation_path)
        while beg.variations:
            yield beg
            try:
                next_idx = next(vp_iterator)
            except StopIteration:
                next_idx = 0
            beg = beg.variations[next_idx]
        yield beg

    @staticmethod
    def __get_move_text_history(game, emphasis, variation_path):
        """
        Returns a list with the san of each move.

        :param game: the ``chess.pgn.Game`` of the game
        :param emphasis: the move which is the current move
        :param variation_path: the path of which variations to fork on
        :return: the list with the san of each move
                    moves with variations will have * in front
                    the emphasis move will be marked with a front tab
        """
        beg = game.variations[0]
        tabbed = False
        moves = []
        # nodes will be tuple of either 2 nodes or 1 node
        # it will be 2 nodes for a full move
        #   and 1 node for a half move
        any_l, len_l, int_l = any, len, int  # lookup time optimization
        for counter, nodes in enumerate(
            map(tuple, grouper_it(2, GUI.__board_node_generator(beg, variation_path))),
            1,
        ):

            try:
                n0s = nodes[0].parent.board().san(nodes[0].move)
                n1s = nodes[1].parent.board().san(nodes[1].move)
                s = f"{counter}. {n0s} {n1s}"
            # If nodes has 1 element
            except IndexError:
                s = f"{counter}. {n0s}"

            # Add a * if there are multiple variations
            if any_l(len_l(n.variations) > 1 for n in nodes):
                s = "*" + s

            # Add a tab if the move is the current move
            if counter - 1 == int_l(emphasis - 0.5):
                s = "\t" + s
                tabbed = True

            moves.append(s)
        if not tabbed:
            moves[-1] = "\t" + moves[-1]
        return moves

    def __get_var_menu_coords(self):
        try:
            coords = None
            amount_variations = len(self.node.variations)
            count = itertools.count()
            while next(count) < 20 and (
                coords is None
                or coords
                and coords[-1][-1][-1] > GUI.moves_panel[-1][-1]
            ):
                if coords:
                    coords = shift_variation_menu(coords, GUI.hist_slot_height)
                else:
                    coords = get_variation_menu_coords(
                        GUI.moves_panel[0][0],
                        GUI.moves_panel[1][0],
                        self._initial_variation_y,
                        GUI.hist_slot_height,
                        amount_variations,
                    )
            return coords

        except Exception as e:
            self.stderr(e)

    def __initiate_variation_menu(self):
        self.display_variation_menu = True
        self.variation_menu_emphasis = 0
        self.draw_variation_menu()
