# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SamsungEndTag(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        super(SamsungEndTag, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._read()

    def _read(self):
        self.payload_size = self._io.read_u2le()
        self._raw_payload = self._io.read_bytes(self.payload_size)
        _io__raw_payload = KaitaiStream(BytesIO(self._raw_payload))
        self.payload = SamsungEndTag.Payload(_io__raw_payload, self, self._root)


    def _fetch_instances(self):
        pass
        self.payload._fetch_instances()

    class Payload(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungEndTag.Payload, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.format_version = self._io.read_s4le()
            self.note_id = SamsungEndTag.Utf16StringU16(self._io, self, self._root)
            self.modified_time_raw = self._io.read_u8le()
            self.property_flags = self._io.read_s4le()
            self.cover_image = SamsungEndTag.Utf16StringU16(self._io, self, self._root)
            self.note_width = self._io.read_s4le()
            self.note_height = self._io.read_f4le()
            self.title = SamsungEndTag.Utf16StringU16(self._io, self, self._root)
            self.thumbnail_width = self._io.read_s4le()
            self.thumbnail_height = self._io.read_s4le()
            self.app_patch_name = SamsungEndTag.Utf16StringU16(self._io, self, self._root)
            self.min_format_version = self._io.read_s4le()
            self.created_time_raw = self._io.read_u8le()
            self.last_viewed_page_index = self._io.read_s4le()
            self.page_mode = self._io.read_u2le()
            self.document_type = self._io.read_u2le()
            self.owner_id = SamsungEndTag.Utf16StringU16(self._io, self, self._root)
            self.reserved_zero_1 = self._io.read_s4le()
            self.reserved_zero_2 = self._io.read_s4le()
            self.display_created_time_raw = self._io.read_u8le()
            self.display_modified_time_raw = self._io.read_u8le()
            self.last_recognized_data_modified_time_raw = self._io.read_u8le()
            self.fixed_font = SamsungEndTag.Utf16StringU16(self._io, self, self._root)
            self.fixed_text_direction = self._io.read_s4le()
            self.fixed_background_theme = self._io.read_s4le()
            self.server_checkpoint = self._io.read_s8le()
            self.new_orientation = self._io.read_s4le()
            self.min_unknown_version = self._io.read_s4le()
            self.app_custom_data = SamsungEndTag.Utf16StringU32(self._io, self, self._root)
            self.footer_marker = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass
            self.note_id._fetch_instances()
            self.cover_image._fetch_instances()
            self.title._fetch_instances()
            self.app_patch_name._fetch_instances()
            self.owner_id._fetch_instances()
            self.fixed_font._fetch_instances()
            self.app_custom_data._fetch_instances()


    class Utf16StringU16(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungEndTag.Utf16StringU16, self).__init__(_io)
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



    class Utf16StringU32(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungEndTag.Utf16StringU32, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.len = self._io.read_u4le()
            if self.len != 4294967295:
                pass
                self.value = (self._io.read_bytes(self.len * 2)).decode(u"UTF-16LE")



        def _fetch_instances(self):
            pass
            if self.len != 4294967295:
                pass




