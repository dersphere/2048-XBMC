#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2014 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import random

import xbmc
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon()

ADDON_NAME = addon.getAddonInfo('name')
ADDON_PATH = addon.getAddonInfo('path').decode('utf-8')
MEDIA_PATH = os.path.join(
    xbmc.translatePath(ADDON_PATH),
    'resources',
    'skins',
    'default',
    'media'
)

STRINGS = {
    'score': 32000,
    'highscore': 32001,
    'lose_heading': 32002,
    'lose_line1': 32003,
}


GRID_SIZE = 4
TILE_VALUE_CHOICES = [2] * 9 + [4]

ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_UP = 3
ACTION_DOWN = 4
ACTION_MENU = 122
ACTION_BACK = 92

WINDOW_X = 390
WINDOW_Y = 110

ZOOM = 1.0
GRID_HEIGHT = 500
GRID_WIDTH = 500
TILE_WIDTH = 106
TILE_HEIGHT = 106
TILE_GAP = 15

ANIM_TIME = 200

SLIDE_EFFECT = 'effect=slide start=%d,%d end=%d,%d time=%d condition=true'
MERGE_ZOOM_EFFECT = 'effect=zoom start=120 end=100 delay=%d time=%d center=auto condition=true'
MERGE_FADE_EFFECT = 'effect=fade start=0 end=100 time=50 condition=true'
SPAWN_ZOOM_EFFECT = 'effect=zoom start=0 end=100 time=%d delay=100 center=auto condition=true'
SPAWN_FADE_EFFECT = 'effect=fade start=0 end=100 time=50 delay=50 condition=true'


def get_image(filename):
    return os.path.join(MEDIA_PATH, filename)


def _(string_id):
    if string_id in STRINGS:
        return addon.getLocalizedString(STRINGS[string_id])
    else:
        xbmc.log('String is missing: %s' % string_id, level=xbmc.LOGDEBUG)
        return string_id


def log(msg):
    xbmc.log('[ADDON][%s] %s' % (ADDON_NAME, msg.encode('utf-8')),
             level=xbmc.LOGNOTICE)


class HighscoreManager(object):

    def __init__(self, addon):
        self.addon = addon
        self.__load()

    def __load(self):
        try:
            with open(self._filepath, 'r') as f:
                self.__value = int(f.read() or 0)
        except IOError:
            self.__value = 0

    def __save(self):
        with open(self._filepath, 'w') as f:
            f.write(str(self.__value))

    def _get(self):
        return self.__value

    def _set(self, value):
        if value != self.__value:
            self.__value = value
            self.__save()

    @property
    def _filepath(self):
        return os.path.join(
            xbmc.translatePath(addon.getAddonInfo('profile').decode('utf-8')),
            'highscore.txt',
        )

    value = property(_get, _set)


class Cell(object):
    row = None
    column = None
    tile = None

    def __init__(self, row, column):
        self.row = row
        self.column = column

    def __del__(self):
        if self.tile:
            self.tile.__del__()

    @property
    def within_grid(self):
        if self.row < 0 or self.row >= self.grid.size:
            return False
        elif self.column < 0 or self.column >= self.grid.size:
            return False
        return True

    @property
    def has_tile(self):
        return self.tile is not None

    def __repr__(self):
        return '(%d, %d)' % (self.row, self.column)


class Tile(object):

    def __init__(self, grid, cell, value=None, is_merged=False):
        self.value = value
        self.grid = grid
        self.cell = cell
        self.original_cell = None
        self.is_merged = is_merged
        self._build_control()
        self.spawn()

    def __del__(self):
        self._del_control()

    def _build_control(self):
        self.control = xbmcgui.ControlImage(
            x=0,
            y=0,
            width=int(
                float(self.grid.window.zoom) *
                float(TILE_WIDTH)
            ),
            height=int(
                float(self.grid.window.zoom) *
                float(TILE_HEIGHT)
            ),
            filename='',
        )
        self.grid.window.addControl(self.control)

    def _del_control(self):
        self.grid.window.removeControl(self.control)
        self.control = None

    def get_coordinates(self, cell=None):
        if cell is None:
            cell = self.cell
        x = self.grid.window.x + int(
            float(self.grid.window.zoom) *
            float(TILE_GAP + cell.column * (TILE_WIDTH + TILE_GAP))
        )
        y = self.grid.window.y + int(
            float(self.grid.window.zoom) *
            float(TILE_GAP + cell.row * (TILE_HEIGHT + TILE_GAP))
        )
        return x, y

    def spawn(self):
        if self.value is None:
            self.value = random.choice(TILE_VALUE_CHOICES)
        # print 'spawn %s' % self.cell
        x, y = self.get_coordinates()
        if self.is_merged:
            # merge
            self.control.setAnimations([
                ('conditional', SLIDE_EFFECT % (x, y, x, y, ANIM_TIME)),
                ('conditional', MERGE_FADE_EFFECT),
                ('conditional', MERGE_ZOOM_EFFECT % (ANIM_TIME, ANIM_TIME)),
            ])
        else:
            # spawn
            self.control.setAnimations([
                ('conditional', SLIDE_EFFECT % (x, y, x, y, ANIM_TIME)),
                ('conditional', SPAWN_ZOOM_EFFECT % ANIM_TIME),
                ('conditional', SPAWN_FADE_EFFECT),
            ])
        self.cell.tile = self
        self.control.setImage(get_image('%d.png' % self.value))

    def move(self, new_cell):
        # print 'move %s -> %s' % (self.cell, new_cell)
        if self.cell == new_cell:
            return False
        x, y = self.get_coordinates()
        new_x, new_y = self.get_coordinates(new_cell)
        self.control.setAnimations([
            ('conditional', SLIDE_EFFECT % (x, y, new_x, new_y, ANIM_TIME))
        ])
        self.cell.tile = None
        self.cell = new_cell
        self.cell.tile = self
        self.control.setImage(get_image('%d.png' % self.value))
        return True

    def merge(self, new_cell):
        # print 'move_and_merge %s -> %s' % (self.cell, new_cell)
        self.is_merged = True
        x, y = self.get_coordinates(self.original_cell or self.cell)
        new_x, new_y = self.get_coordinates(new_cell)
        self.control.setAnimations([
            ('conditional', SLIDE_EFFECT % (x, y, new_x, new_y, ANIM_TIME)),
        ])
        self.grid.cells[self.cell.row][self.cell.column].tile = None
        self.grid.killed_tiles.append(self)
        return True

    def __repr__(self):
        return '%d (%s)' % (self.value, self.cell)


class Grid(object):

    cells = []
    killed_tiles = []
    score = 0

    def __init__(self, window, size):
        self.window = window
        self.size = size
        self.highscore = HighscoreManager(addon)
        self._build_controls()

    def start_game(self):
        self._delete_cells()
        self._generate_cells()
        self.score = 0
        self.score_control.setLabel(_('score') % self.score)
        self.highscore_control.setLabel(_('highscore') % self.highscore.value)
        self.add_random_tile()
        self.add_random_tile()

    def _build_controls(self):
        self.background_control = xbmcgui.ControlImage(
            x=self.window.x,
            y=self.window.y,
            width=int(
                float(self.window.zoom) *
                float(GRID_WIDTH)
            ),
            height=int(
                float(self.window.zoom) *
                float(GRID_HEIGHT)
            ),
            filename=get_image('grid.png'),
        )
        self.score_control = xbmcgui.ControlLabel(
            x=self.window.x,
            y=self.window.y - 50,
            width=200,
            height=50,
            label='',
        )
        self.highscore_control = xbmcgui.ControlLabel(
            x=self.window.x + 200,
            y=self.window.y - 50,
            width=200,
            height=50,
            label='',
        )
        self.window.addControl(self.background_control)
        self.window.addControl(self.score_control)
        self.window.addControl(self.highscore_control)

    def _del_control(self):
        self.window.removeControl(self.background_control)
        self.window.removeControl(self.score_control)
        self.window.removeControl(self.highscore_control)
        self.background_control = None
        self.score_control = None
        self.highscore_control = None

    def _generate_cells(self):
        self.cells = [
            [Cell(row, column) for column in xrange(self.size)]
            for row in xrange(self.size)
        ]

    def _delete_cells(self):
        while self.cells:
            row = self.cells.pop()
            while row:
                cell = row.pop()
                if cell.tile:
                    cell.tile.__del__()
        while self.killed_tiles:
            tile = self.killed_tiles.pop()
            tile.__del__()

    def all_cells(self):
        for row, cells in enumerate(self.cells):
            for column, cell in enumerate(cells):
                yield cell

    def free_cells(self):
        for cell in self.all_cells():
            if cell.tile is None:
                yield cell

    def has_tile_cells(self):
        for cell in self.all_cells():
            if cell.tile is not None:
                yield cell

    def has_free_cell(self):
        return len(list(self.free_cells())) > 0

    def move_available(self):
        return self.has_free_cell() or self.merge_available()

    def merge_available(self):
        for cell in self.all_cells():
            if cell.tile:
                for direction in ('up', 'down', 'right', 'left'):
                    vector = self.get_vector(direction)
                    other_cell = self.at(
                        row=cell.row + vector['row'],
                        column=cell.column + vector['column'],
                    )
                    if other_cell and other_cell.tile:
                        if other_cell.tile.value == cell.tile.value:
                            return True
        return False

    def within_grid(self, row, column):
        if row < 0 or row >= self.size:
            return False
        elif column < 0 or column >= self.size:
            return False
        return True

    def at(self, row, column):
        if not self.within_grid(row, column):
            return None
        return self.cells[row][column]

    def add_random_tile(self):
        free_cells = list(self.free_cells())
        cell = random.choice(free_cells)
        cell.tile = Tile(self, cell)

    def prepare_tiles(self):
        for cell in self.has_tile_cells():
            cell.tile.is_merged = False
            cell.tile.original_cell = cell
        while self.killed_tiles:
            tile = self.killed_tiles.pop()
            del tile

    def get_vector(self, direction):
        vectors = {
            'up': {'row': -1,  'column': 0},
            'right': {'row': 0,  'column': 1},
            'down': {'row': 1,  'column': 0},
            'left': {'row': 0, 'column': -1}
        }
        return vectors[direction]

    def build_traversal(self, vector):
        traversals = {
            'rows': [i for i in xrange(self.size)],
            'columns': [i for i in xrange(self.size)]
        }
        if vector['row'] == 1:
            traversals['rows'].reverse()
        if vector['column'] == 1:
            traversals['columns'].reverse()
        return traversals

    def find_farthest_cells(self, cell, vector):
        farthest_free_cell = cell
        next_cell = self.at(
            row=cell.row + vector['row'],
            column=cell.column + vector['column'],
        )
        while next_cell and not next_cell.has_tile:
            # print 'previous: %s' % repr(previous)
            # print 'next: %s' % repr(cell)
            farthest_free_cell = next_cell
            next_cell = self.at(
                row=farthest_free_cell.row + vector['row'],
                column=farthest_free_cell.column + vector['column'],
            )
        return farthest_free_cell, next_cell

    def move(self, direction):
        self.prepare_tiles()
        vector = self.get_vector(direction)
        traversals = self.build_traversal(vector)
        moved = False
        for row in traversals['rows']:
            for column in traversals['columns']:
                cell = self.at(row, column)
                if cell.has_tile:
                    farthest_free, next = self.find_farthest_cells(cell, vector)
                    # print 'cell: (%d, %d)' % (cell.row, cell.column)
                    # print 'previous: %s' % (repr(previous))
                    # print 'next: %s' % (repr(next))
                    can_be_merged = (
                        next and
                        next.has_tile and
                        next.tile.value == cell.tile.value and
                        not next.tile.is_merged
                    )
                    if can_be_merged:
                        merged_value = cell.tile.value * 2
                        cell.tile.merge(next)
                        next.tile.merge(next)
                        next.tile = Tile(self, next, merged_value, is_merged=True)
                        moved = True
                        self.score += merged_value
                    else:
                        if cell.tile.move(farthest_free):
                            moved = True
        if moved:
            self.score_control.setLabel(_('score') % self.score)
            if self.score > self.highscore.value:
                self.highscore.value = self.score
                self.highscore_control.setLabel(_('highscore') % self.highscore.value)
            self.add_random_tile()
        return moved

    def __del__(self):
        self._delete_cells()
        self._del_control()


class Window(xbmcgui.WindowXMLDialog):
    x = WINDOW_X
    y = WINDOW_Y
    zoom = ZOOM

    def onInit(self):
        self.grid = Grid(self, GRID_SIZE)
        self.grid.start_game()

    def onAction(self, action):
        action_id = action.getId()
        moved = False
        if action_id == ACTION_LEFT:
            moved = self.grid.move('left')
        elif action_id == ACTION_RIGHT:
            moved = self.grid.move('right')
        elif action_id == ACTION_UP:
            moved = self.grid.move('up')
        elif action_id == ACTION_DOWN:
            moved = self.grid.move('down')
        elif action_id == ACTION_BACK:
            self.exit()
        elif action_id == ACTION_MENU:
            self.grid.start_game()
        if moved and not self.grid.move_available():
            xbmcgui.Dialog().ok(
                heading=_('lose_heading'),
                line1=_('lose_line1'),
            )
            self.grid.start_game()

    def exit(self):
        self.grid.__del__()
        self.close()


if __name__ == '__main__':
    window = Window(
        'script-%s-main.xml' % ADDON_NAME,
        ADDON_PATH,
        'default',
        '720p'
    )
    window.doModal()
    del window
