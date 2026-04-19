# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SamsungPage(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        super(SamsungPage, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._read()

    def _read(self):
        self.raw_layer_offset = self._io.read_u4le()
        self.property_offset = self._io.read_u4le()
        self.unknown_08 = self._io.read_u1()
        self.text_only_flag = self._io.read_u4le()
        self.unknown_0d = self._io.read_u1()
        self.page_property_mask = self._io.read_u4le()
        self.note_orientation = self._io.read_u4le()
        self.page_width = self._io.read_u4le()
        self.page_height = self._io.read_u4le()
        self.offset_x = self._io.read_u4le()
        self.offset_y = self._io.read_u4le()
        self.page_uuid = SamsungPage.Utf16StringU16(self._io, self, self._root)
        if self._io.pos() + 8 <= self._io.size():
            pass
            self.modified_time_raw = self._io.read_u8le()

        if self._io.pos() + 4 <= self._io.size():
            pass
            self.format_version = self._io.read_u4le()

        if self._io.pos() + 4 <= self._io.size():
            pass
            self.min_format_version = self._io.read_u4le()



    def _fetch_instances(self):
        pass
        self.page_uuid._fetch_instances()
        if self._io.pos() + 8 <= self._io.size():
            pass

        if self._io.pos() + 4 <= self._io.size():
            pass

        if self._io.pos() + 4 <= self._io.size():
            pass

        _ = self.properties
        if hasattr(self, '_m_properties'):
            pass
            self._m_properties._fetch_instances()


    class CanvasCacheEntry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.CanvasCacheEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.key = self._io.read_u4le()
            self.file_id = self._io.read_u4le()
            self.width = self._io.read_u4le()
            self.height = self._io.read_u4le()
            self.is_dark_mode = self._io.read_u1()
            self.background_color_int = self._io.read_u4le()
            self.version0 = self._io.read_u4le()
            self.version1 = self._io.read_u4le()
            self.version2 = self._io.read_u4le()
            self.cache_version = self._io.read_u4le()
            self.property = self._io.read_u4le()
            self.locale_list_id = self._io.read_u4le()
            self.system_font_path_hash = self._io.read_u4le()
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class CanvasCacheList(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.CanvasCacheList, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.num_entries = self._io.read_u4le()
            self.record_size = self._io.read_u2le()
            self._raw_entries = []
            self.entries = []
            for i in range(self.num_entries):
                self._raw_entries.append(self._io.read_bytes(self.record_size))
                _io__raw_entries = KaitaiStream(BytesIO(self._raw_entries[i]))
                self.entries.append(SamsungPage.CanvasCacheEntry(_io__raw_entries, self, self._root))



        def _fetch_instances(self):
            pass
            for i in range(len(self.entries)):
                pass
                self.entries[i]._fetch_instances()



    class CountedUtf8U32(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.CountedUtf8U32, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.len = self._io.read_u4le()
            self.value = (self._io.read_bytes(self.len)).decode(u"UTF-8")


        def _fetch_instances(self):
            pass


    class CustomObjectEntry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.CustomObjectEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.object_type = self._io.read_u4le()
            self.payload_size = self._io.read_u4le()
            self.payload = self._io.read_bytes(self.payload_size)


        def _fetch_instances(self):
            pass


    class CustomObjectList(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.CustomObjectList, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.num_entries = self._io.read_u4le()
            self.entries = []
            for i in range(self.num_entries):
                self.entries.append(SamsungPage.CustomObjectEntry(self._io, self, self._root))



        def _fetch_instances(self):
            pass
            for i in range(len(self.entries)):
                pass
                self.entries[i]._fetch_instances()



    class PageProperties(KaitaiStruct):
        def __init__(self, property_mask, format_version, _io, _parent=None, _root=None):
            super(SamsungPage.PageProperties, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.property_mask = property_mask
            self.format_version = format_version
            self._read()

        def _read(self):
            if self.property_mask & 1 != 0:
                pass
                self.drawn_rect = SamsungPage.RectF64(self._io, self, self._root)

            if self.property_mask & 2 != 0:
                pass
                self.tags = SamsungPage.TagList(self._io, self, self._root)

            if self.property_mask & 4 != 0:
                pass
                self.template_uri = SamsungPage.Utf16StringU16(self._io, self, self._root)

            if self.property_mask & 8 != 0:
                pass
                self.bg_image_id = self._io.read_u4le()

            if self.property_mask & 16 != 0:
                pass
                self.bg_image_mode = self._io.read_u4le()

            if self.property_mask & 32 != 0:
                pass
                self.background_color_int = self._io.read_u4le()

            if self.property_mask & 64 != 0:
                pass
                self.bg_width = self._io.read_u4le()

            if self.property_mask & 128 != 0:
                pass
                self.bg_rotation = self._io.read_u4le()

            if self.property_mask & 256 != 0:
                pass
                self.pdf_data = SamsungPage.PdfDataList(self.format_version, self._io, self, self._root)

            if self.property_mask & 512 != 0:
                pass
                self.template_type = self._io.read_u4le()

            if self.property_mask & 1024 != 0:
                pass
                self.canvas_cache = SamsungPage.CanvasCacheList(self._io, self, self._root)

            if self.property_mask & 2048 != 0:
                pass
                self.imported_data_height = self._io.read_u4le()

            if self.property_mask & 4096 != 0:
                pass
                self.reserved_0x1000 = self._io.read_u4le()

            if self.property_mask & 262144 != 0:
                pass
                self.custom_objects = SamsungPage.CustomObjectList(self._io, self, self._root)



        def _fetch_instances(self):
            pass
            if self.property_mask & 1 != 0:
                pass
                self.drawn_rect._fetch_instances()

            if self.property_mask & 2 != 0:
                pass
                self.tags._fetch_instances()

            if self.property_mask & 4 != 0:
                pass
                self.template_uri._fetch_instances()

            if self.property_mask & 8 != 0:
                pass

            if self.property_mask & 16 != 0:
                pass

            if self.property_mask & 32 != 0:
                pass

            if self.property_mask & 64 != 0:
                pass

            if self.property_mask & 128 != 0:
                pass

            if self.property_mask & 256 != 0:
                pass
                self.pdf_data._fetch_instances()

            if self.property_mask & 512 != 0:
                pass

            if self.property_mask & 1024 != 0:
                pass
                self.canvas_cache._fetch_instances()

            if self.property_mask & 2048 != 0:
                pass

            if self.property_mask & 4096 != 0:
                pass

            if self.property_mask & 262144 != 0:
                pass
                self.custom_objects._fetch_instances()



    class PdfDataEntry(KaitaiStruct):
        def __init__(self, format_version, _io, _parent=None, _root=None):
            super(SamsungPage.PdfDataEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.format_version = format_version
            self._read()

        def _read(self):
            self.file_id = self._io.read_s4le()
            self.page_index = self._io.read_s4le()
            if  ((self.format_version != 0) and (self.format_version < 2034)) :
                pass
                self.rect_as_f32 = SamsungPage.RectF32(self._io, self, self._root)

            if  ((self.format_version == 0) or (self.format_version >= 2034)) :
                pass
                self.rect_as_i32 = SamsungPage.RectI32(self._io, self, self._root)



        def _fetch_instances(self):
            pass
            if  ((self.format_version != 0) and (self.format_version < 2034)) :
                pass
                self.rect_as_f32._fetch_instances()

            if  ((self.format_version == 0) or (self.format_version >= 2034)) :
                pass
                self.rect_as_i32._fetch_instances()



    class PdfDataList(KaitaiStruct):
        def __init__(self, format_version, _io, _parent=None, _root=None):
            super(SamsungPage.PdfDataList, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.format_version = format_version
            self._read()

        def _read(self):
            self.num_entries = self._io.read_u2le()
            self.entries = []
            for i in range(self.num_entries):
                self.entries.append(SamsungPage.PdfDataEntry(self.format_version, self._io, self, self._root))



        def _fetch_instances(self):
            pass
            for i in range(len(self.entries)):
                pass
                self.entries[i]._fetch_instances()



    class RectF32(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.RectF32, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.left = self._io.read_f4le()
            self.top = self._io.read_f4le()
            self.right = self._io.read_f4le()
            self.bottom = self._io.read_f4le()


        def _fetch_instances(self):
            pass


    class RectF64(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.RectF64, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.left = self._io.read_f8le()
            self.top = self._io.read_f8le()
            self.right = self._io.read_f8le()
            self.bottom = self._io.read_f8le()


        def _fetch_instances(self):
            pass


    class RectI32(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.RectI32, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.left = self._io.read_s4le()
            self.top = self._io.read_s4le()
            self.right = self._io.read_s4le()
            self.bottom = self._io.read_s4le()


        def _fetch_instances(self):
            pass


    class TagList(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.TagList, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.num_tags = self._io.read_u2le()
            self.tags = []
            for i in range(self.num_tags):
                self.tags.append(SamsungPage.Utf16StringU16(self._io, self, self._root))



        def _fetch_instances(self):
            pass
            for i in range(len(self.tags)):
                pass
                self.tags[i]._fetch_instances()



    class Utf16StringU16(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.Utf16StringU16, self).__init__(_io)
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



    class Utf8U16Bytes(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPage.Utf8U16Bytes, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.len = self._io.read_u2le()
            self.raw_value = self._io.read_bytes(self.len)


        def _fetch_instances(self):
            pass


    @property
    def properties(self):
        if hasattr(self, '_m_properties'):
            return self._m_properties

        if self.property_offset < self._io.size():
            pass
            _pos = self._io.pos()
            self._io.seek(self.property_offset)
            self._raw__m_properties = self._io.read_bytes(self._io.size() - self.property_offset)
            _io__raw__m_properties = KaitaiStream(BytesIO(self._raw__m_properties))
            self._m_properties = SamsungPage.PageProperties(self.page_property_mask, self.format_version, _io__raw__m_properties, self, self._root)
            self._io.seek(_pos)

        return getattr(self, '_m_properties', None)


