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


class FoldBoringLines(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.fold(self.view.find_all(r'\n(^[^a-zA-Z0-9]*$)+'))


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
