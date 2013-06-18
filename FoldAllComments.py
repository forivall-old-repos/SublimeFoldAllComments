# import re
import itertools
import sublime
import sublime_plugin


class FoldAllCommentsCommand(sublime_plugin.TextCommand):
    ''' view.run_command('fold_all_comments') '''
    def run(self, edit):
        regions = self.view.find_by_selector('comment')
        if not regions:
            return
        if len(regions) < 2:
            self.view.fold(regions)
            return
        i1, i2 = itertools.tee(regions)
        next(i2)
        merged_regions = [regions[0]]
        cur = 0
        for i, (r, s) in enumerate(itertools.izip(i1, i2)):
            whitespace_region = self.view.find('^[ \t\n]*[ \t]', r.b)
            if (len(whitespace_region) > 0 and
                    whitespace_region.b == s.a):
                merged_regions[cur] = sublime.Region(
                    merged_regions[cur].a, s.b)
            else:
                merged_regions.append(s)
                cur += 1

        cur = 0
        for r in self.view.find_all('\n[ \t]+'):
            while cur < len(merged_regions):
                cur_region = merged_regions[cur]
                if r.b < cur_region.a:
                    _continue = True
                    break
                if r.b == cur_region.a:
                    merged_regions[cur] = sublime.Region(r.a, cur_region.b)
                    cur += 1
                    _continue = True
                    break
                cur += 1
            if _continue:
                continue
            break

        self.view.fold([sublime.Region(r.a, r.b - 1) for r in merged_regions])


class FoldAllWhitespaceLines(sublime_plugin.TextCommand):
    ''' view.run_command('fold_all_comments') '''
    def run(self, edit):
        self.view.fold(self.view.find_all(r'\h*\v{2,}\h*$'))
        SimplifyFolds(self.view).run(edit)


class FoldStupidCurlysOnlyLines(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.fold(self.view.find_all(
            r'(?:\n\t*)*\n(^\h*[\{\};\[\]\(\)]+\h*$)+'))
        SimplifyFolds(self.view).run(edit)


class FoldStupidlyFormattedNewlines(sublime_plugin.TextCommand):
    def run(self, edit):
        if 'HTML' in self.view.settings().get('syntax'):
            self.view.fold(self.view.find_all(
                # r'\n(^\h*(?=[\{\}\[\]\(\)]+))'
                r'\n(^\h*(?=</[a-z]+>$))'
            ))
        else:
            self.view.fold(self.view.find_all(
                # r'\n(^\h*(?=[\{\}\[\]\(\)]+))'
                r'(\n\h*)*\n(^\h*(?=([\{\(]+|[\}\]\)]+(\(\)+)*)[,;]?$))'
            ))
        if any(lang in self.view.settings().get('syntax') for lang in
               ('Python', 'Cython')):
            # I don't really care for the pep8 2-line breaks
            self.view.fold(self.view.find_all(r'\n(?=\n\n+)'))
        SimplifyFolds(self.view).run(edit)


class FoldBoringLines(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.fold(self.view.find_all(r'\n(^[^a-zA-Z0-9]*$)+'))
        SimplifyFolds(self.view).run(edit)


def iter_simplify(regions):
    regions_iter = iter(regions)
    first = next(regions_iter)
    begin = first.a
    end = first.b
    for region in regions_iter:
        if region.a != end:
            yield sublime.Region(begin, end)
            begin = region.a
        end = region.b
    yield sublime.Region(begin, end)


class SimplifyFolds(sublime_plugin.TextCommand):
    def run(self, edit):
        folded_regions = self.view.folded_regions()
        if len(folded_regions) < 2:
            return
        self.view.unfold(folded_regions)
        self.view.fold(list(iter_simplify(folded_regions)))


class FoldAllLevels(sublime_plugin.TextCommand):
    def run(self, edit):
        for i in range(10):
            self.view.run_command('fold_by_level', {"level": i})

import re


class FoldTemplateBlocks(sublime_plugin.TextCommand):
    def run(self, edit):
        start_sre = r'\{\% *block ([a-zA-Z0-9_]+) *%\}'
        block_starts = self.view.find_all(start_sre)
        for start in block_starts:
            name = re.match(start_sre, self.view.substr(start)
                            ).group(1)
            # print name
            end = self.view.find(
                r'\{\% *endblock ' + name + r' *\%\}', start.b)
            if end is None:
                end = self.view.find(r'\{\% *endblock *\%\}', start.b)
            self.view.fold(sublime.Region(start.b, end.a))


class CountSloc(sublime_plugin.TextCommand):
    def run(self, edit):
        sloc = count_sloc(self.view)
        message = 'SLOC: ' + str(sloc)
        print message
        sublime.status_message(message)
        self.view.window().show_quick_panel([message], None)


def count_sloc(view):
    c = len([l
             for r in view.find_by_selector('comment')
             for l in view.split_by_newlines(r)])
    b = len(view.find_all(r'^\h*$'))
    total = len(view.lines(sublime.Region(0, view.size()))) + 1
    return total - c - b
    # len(view.lines(sublime.Region(0, view.size()))) + 1 -
    # len([l for r in view.find_by_selector('comment') for l in
    #     view.split_by_newlines(r)]) - len(view.find_all(r'^\h*$'))


# following is ripped from bufferscroll for manual fold save/load

from os.path import lexists, normpath, dirname
from hashlib import sha1
from gzip import GzipFile
from cPickle import load, dump
db = {}

database = dirname(
    sublime.packages_path()) + '/Settings/FoldAllComments.bin.gz'
if lexists(database):
    try:
        gz = GzipFile(database, 'rb')
        db = load(gz)
        gz.close()
    except:
        db = {}

writing_to_disk = False


def write_db():
    global writing_to_disk
    if writing_to_disk:
        return
    writing_to_disk = True
    sublime.set_timeout(write_db_sync, 0)


def write_db_sync():
    global writing_to_disk
    gz = GzipFile(database, 'wb')
    dump(db, gz, -1)
    gz.close()
    writing_to_disk = False


class SaveFolds(sublime_plugin.TextCommand):
    def view_id(self, view):
        if not view.settings().has('buffer_scroll_name'):
            view.settings().set(
                'buffer_scroll_name', sha1(normpath(
                    view.file_name().encode('utf-8'))).hexdigest()[:8])
        return (
            view.settings().get('buffer_scroll_name'), self.view_index(view))

    def view_index(self, view):
        window = view.window()
        if not window:
            window = sublime.active_window()
        index = window.get_view_index(view)
        if index and index != (0, 0) \
                and index != (0, -1) and index != (-1, -1):
            return str(window.id()) + str(index)
        else:
            return '0'

    def save_callback(self, name):
        view = self.view
        id, index = self.view_id(view)
        if id not in db:
            db[id] = {}
        db[id][name] = [[item.a, item.b] for item in view.folded_regions()]
        write_db()

    def run(self, edit):
        # todo: autocomplete
        self.view.window().show_input_panel(
            'enter a name', 'default', self.save_callback, None, None)


class ResaveFolds(sublime_plugin.TextCommand):
    def view_id(self, view):
        if not view.settings().has('buffer_scroll_name'):
            view.settings().set(
                'buffer_scroll_name', sha1(normpath(
                    view.file_name().encode('utf-8'))).hexdigest()[:8])
        return (
            view.settings().get('buffer_scroll_name'), self.view_index(view))

    def view_index(self, view):
        window = view.window()
        if not window:
            window = sublime.active_window()
        index = window.get_view_index(view)
        if index and index != (0, 0) \
                and index != (0, -1) and index != (-1, -1):
            return str(window.id()) + str(index)
        else:
            return '0'

    def save_callback(self, id_index):
        view = self.view
        id, index = self.view_id(view)
        print len(self._items), id_index
        item_id = self._items[id_index] \
            if id_index > 0 and id_index < len(self._items) \
            else 'default'
        db[id][item_id] = [[item.a, item.b] for item in view.folded_regions()]
        write_db()

    def run(self, edit):
        view = self.view
        id, index = self.view_id(view)
        if id not in db:
            db[id] = {}
        self._items = sorted(db[id].keys())
        self.view.window().show_quick_panel(self._items, self.save_callback)


class LoadFolds(sublime_plugin.TextCommand):
    def view_id(self, view):
        if not view.settings().has('buffer_scroll_name'):
            view.settings().set(
                'buffer_scroll_name', sha1(normpath(
                    view.file_name().encode('utf-8'))).hexdigest()[:8])
        return (
            view.settings().get('buffer_scroll_name'), self.view_index(view))

    def view_index(self, view):
        window = view.window()
        if not window:
            window = sublime.active_window()
        index = window.get_view_index(view)
        if index and index != (0, 0) \
                and index != (0, -1) and index != (-1, -1):
            return str(window.id()) + str(index)
        else:
            return '0'

    def callback(self, id_index):
        view = self.view
        id, index = self.view_id(view)
        print len(self._items), id_index
        item_id = self._items[id_index] \
            if id_index > 0 and id_index < len(self._items) \
            else 'default'
        regions = []
        for r in db[id][item_id]:
            regions.append(sublime.Region(int(r[0]), int(r[1])))
        if len(regions):
            view.unfold(sublime.Region(0, self.view.size()))
            view.fold(regions)

    def run(self, edit):
        view = self.view
        id, index = self.view_id(view)
        if id not in db:
            db[id] = {}
        self._items = sorted(db[id].keys())
        self.view.window().show_quick_panel(self._items, self.callback)
