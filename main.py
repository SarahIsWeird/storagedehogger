import os
import pathlib

import wx
import wx.dataview as dv

import argparse


class File(object):
    def __init__(self, parent, path, size):
        self.parent = parent
        self.path = path
        self.size = size

    def __repr__(self):
        return f'{self.path} ({self.size} bytes)'


class Folder(File):
    def __init__(self, parent, path, size, children: list[File]):
        File.__init__(self, parent, path, size)

        self.parent = parent
        self.path = path
        self.size = size
        self.children = children

    def __repr__(self):
        return f'{self.path}/ ({self.size} bytes)'


def get_file_tree(name, root, parent):
    total = 0
    files = []

    with os.scandir(root) as it:
        for entry in it:
            try:
                if entry.is_file(follow_symlinks=False):
                    size = entry.stat().st_size
                    total += size
                    files.append(File(parent, entry.name, size))
                elif entry.is_dir(follow_symlinks=False):
                    folder = get_file_tree(entry.name, entry.path, parent)
                    total += folder.size
                    files.append(folder)
            except PermissionError:
                continue

    return Folder(parent, name, total, files)


class FileSizeRenderer(dv.DataViewCustomRenderer):
    def __init__(self, *args, **kw):
        dv.DataViewCustomRenderer.__init__(self, *args, **kw)

        self.value = None

    def SetValue(self, value):
        self.value = int(value) if value is not None else None
        return True

    def GetValue(self):
        return self.value

    def GetSize(self):
        return self.GetTextExtent(self.pretty_print_size())

    def Render(self, cell, dc, state):
        value = self.pretty_print_size()

        self.RenderText(value, 0, cell, dc, state)

        return True

    def pretty_print_size(self):
        if self.value is None:
            return ''

        tmp = int(self.value)

        if tmp < 1000:
            return f'{tmp} bytes'

        tmp /= 1000

        if tmp < 1000:
            return f'{tmp:.2f} kB'

        tmp /= 1000

        if tmp < 1000:
            return f'{tmp:.2f} MB'

        tmp /= 1000

        if tmp < 1000:
            return f'{tmp:.2f} GB'


class FolderTreeViewModel(dv.PyDataViewModel):
    def __init__(self, data: list[File]):
        dv.PyDataViewModel.__init__(self)

        self.data = data

        self.UseWeakRefs(True)

    def Compare(self, item1, item2, column, ascending):
        file1: File = self.ItemToObject(item1)
        file2: File = self.ItemToObject(item2)

        if column == 0 or file1.size == file2.size:
            return 1 if ascending == (file1.path > file2.path) else -1
        else:
            return 1 if ascending == (file1.size > file2.size) else -1

    def HasContainerColumns(self, item):
        return True

    def GetColumnCount(self):
        return 2

    def GetChildren(self, parent, children):
        if not parent:
            data = self.data
        else:
            data = self.ItemToObject(parent).children

        for file in data:
            item = self.ObjectToItem(file)

            children.append(item)

        return len(data)

    def IsContainer(self, item):
        if not item:
            return True

        node = self.ItemToObject(item)

        if isinstance(node, Folder):
            return True

        return False

    def GetParent(self, item):
        if not item:
            return dv.NullDataViewItem

        node = self.ItemToObject(item)
        return node.parent

    def GetValue(self, item, col):
        node: File = self.ItemToObject(item)

        return {
            0: node.path,
            1: str(node.size)
        }[col]

    def GetAttr(self, item, col, attr):
        node = self.ItemToObject(item)

        if isinstance(node, Folder):
            attr.SetColour('blue')
            attr.SetBold(True)

            return True

        return False

    def SetValue(self, value, item, col):
        return True


class AppFrame(wx.Frame):
    def __init__(self, root_path):
        wx.Frame.__init__(self, None, title='Storage Dehogger', size=(800, 600))

        tree = get_file_tree(root_path, root_path, None)

        foo = Folder(None, 'foo', 69, [])
        foo.children.append(File(foo, 'bar', 420))
        foo.children.append(File(foo, 'baz', 1337))

        self.dvc = dv.DataViewCtrl(self, size=(800, 600), style=wx.EXPAND | wx.BORDER_THEME | dv.DV_ROW_LINES
                                   | dv.DV_VERT_RULES | dv.DV_MULTIPLE)
        self.model = FolderTreeViewModel([tree])

        self.dvc.AssociateModel(self.model)

        self.dvc.AppendTextColumn('Name', 0, width=300, mode=dv.DATAVIEW_CELL_EDITABLE)

        size_renderer = FileSizeRenderer()
        col = dv.DataViewColumn('Size', size_renderer, 1, width=100)
        col.Alignment = wx.ALIGN_LEFT
        self.dvc.AppendColumn(col)

        for col in self.dvc.GetColumns():
            col.SetSortable(True)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(self.dvc)

        self.SetSizer(main_sizer)

        self.Show(True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find storage heavyweights on your disk!')
    parser.add_argument('--path', type=pathlib.Path, required=True)
    args = parser.parse_args()

    app = wx.App(False)

    frame = AppFrame(str(args.path))

    app.MainLoop()
