# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SamsungPageIdInfo(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        super(SamsungPageIdInfo, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._read()

    def _read(self):
        self.file_hash = self._io.read_bytes(32)
        self.num_entries = self._io.read_u2le()
        self.entries = []
        for i in range(self.num_entries):
            self.entries.append(SamsungPageIdInfo.Entry(self._io, self, self._root))



    def _fetch_instances(self):
        pass
        for i in range(len(self.entries)):
            pass
            self.entries[i]._fetch_instances()


    class Entry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageIdInfo.Entry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.page_id = SamsungPageIdInfo.Utf16StringU16(self._io, self, self._root)
            self.page_hash = self._io.read_bytes(32)


        def _fetch_instances(self):
            pass
            self.page_id._fetch_instances()


    class Utf16StringU16(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageIdInfo.Utf16StringU16, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.len = self._io.read_u2le()
            if self.len != 65535:
                pass
                self.value = (self._io.read_bytes(self.len * 2)).decode(u"UTF-16LE")



        def _fetch_instances(self):
            pass
            if self.len != 65535:
                pass




