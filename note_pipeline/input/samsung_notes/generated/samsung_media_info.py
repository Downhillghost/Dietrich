# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SamsungMediaInfo(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        super(SamsungMediaInfo, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._read()

    def _read(self):
        self.format_version = self._io.read_u4le()
        self.num_entries = self._io.read_u2le()
        self.entries = []
        for i in range(self.num_entries):
            self.entries.append(SamsungMediaInfo.Entry(self._io, self, self._root))

        self.footer_marker = self._io.read_bytes_full()


    def _fetch_instances(self):
        pass
        for i in range(len(self.entries)):
            pass
            self.entries[i]._fetch_instances()


    class Entry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungMediaInfo.Entry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.entry_size = self._io.read_u4le()
            self._raw_body = self._io.read_bytes(self.entry_size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = SamsungMediaInfo.EntryBody(_io__raw_body, self, self._root)


        def _fetch_instances(self):
            pass
            self.body._fetch_instances()


    class EntryBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungMediaInfo.EntryBody, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.bind_id = self._io.read_u4le()
            self.filename = SamsungMediaInfo.Utf16StringU16(self._io, self, self._root)
            self.file_hash_raw = self._io.read_bytes(64)
            self.ref_count = self._io.read_u2le()
            self.modified_time = self._io.read_u8le()
            self.is_file_attached = self._io.read_u1()
            self.extra_bytes = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass
            self.filename._fetch_instances()


    class Utf16StringU16(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungMediaInfo.Utf16StringU16, self).__init__(_io)
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




