# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SamsungNote(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        super(SamsungNote, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._read()

    def _read(self):
        self.integrity_offset = self._io.read_u4le()
        self.header_constant_1 = self._io.read_u1()
        self.header_flags = self._io.read_u4le()
        self.header_constant_2 = self._io.read_u1()
        self.property_flags = self._io.read_u4le()
        self.format_version = self._io.read_u4le()
        self.note_id = SamsungNote.Utf16StringU16(self._io, self, self._root)
        self.file_revision = self._io.read_u4le()
        self.created_time_raw = self._io.read_u8le()
        self.modified_time_raw = self._io.read_u8le()
        self.width = self._io.read_u4le()
        self.height = self._io.read_u4le()
        self.page_horizontal_padding = self._io.read_u4le()
        self.page_vertical_padding = self._io.read_u4le()
        self.min_format_version = self._io.read_u4le()
        self.title_object_size = self._io.read_u4le()
        self.title_object = self._io.read_bytes(self.title_object_size)
        self.body_object_size = self._io.read_u4le()
        self.body_object = self._io.read_bytes(self.body_object_size)
        if self.property_flags & 1 != 0:
            pass
            self.app_name = SamsungNote.Utf16StringU16(self._io, self, self._root)

        if self.property_flags & 2 != 0:
            pass
            self.app_version = SamsungNote.AppVersionBlock(self._io, self, self._root)

        if self.property_flags & 4 != 0:
            pass
            self.author_info = SamsungNote.AuthorBlock(self._io, self, self._root)

        if self.property_flags & 8 != 0:
            pass
            self.geo = SamsungNote.GeoBlock(self._io, self, self._root)

        if self.property_flags & 64 != 0:
            pass
            self.template_uri = SamsungNote.Utf16StringU16(self._io, self, self._root)

        if self.property_flags & 128 != 0:
            pass
            self.last_edited_page_index = self._io.read_s4le()

        if self.property_flags & 512 != 0:
            pass
            self.last_edited_page_image = SamsungNote.LastEditedPageImageBlock(self._io, self, self._root)

        if self.property_flags & 1024 != 0:
            pass
            self.string_id_block_size = self._io.read_u4le()

        if self.property_flags & 1024 != 0:
            pass
            self._raw_string_id_block = self._io.read_bytes(self.string_id_block_size)
            _io__raw_string_id_block = KaitaiStream(BytesIO(self._raw_string_id_block))
            self.string_id_block = SamsungNote.StringIdBlock(_io__raw_string_id_block, self, self._root)

        if self.property_flags & 2048 != 0:
            pass
            self.body_text_font_size_delta = self._io.read_s4le()

        if self.property_flags & 4096 != 0:
            pass
            self.legacy_pen_info = SamsungNote.PenInfoLegacy(self._io, self, self._root)

        if self.property_flags & 8192 != 0:
            pass
            self.voice_data = SamsungNote.VoiceDataBlock(self._io, self, self._root)

        if self.property_flags & 16384 != 0:
            pass
            self.attached_files = SamsungNote.AttachedFilesBlock(self._io, self, self._root)

        if self.property_flags & 32768 != 0:
            pass
            self.current_pen_info_block = SamsungNote.SizedCurrentPenInfo(self._io, self, self._root)

        if self.property_flags & 65536 != 0:
            pass
            self.last_recognized_data_modified_time_raw = self._io.read_u8le()

        if self.property_flags & 131072 != 0:
            pass
            self.fixed_font = SamsungNote.Utf16StringU16(self._io, self, self._root)

        if self.property_flags & 262144 != 0:
            pass
            self.fixed_text_direction = self._io.read_s4le()

        if self.property_flags & 524288 != 0:
            pass
            self.fixed_background_theme = self._io.read_s4le()

        if self.property_flags & 1048576 != 0:
            pass
            self.text_summarization = SamsungNote.Utf16StringU16(self._io, self, self._root)

        if self.property_flags & 2097152 != 0:
            pass
            self.stroke_group_size = self._io.read_s4le()

        if self.property_flags & 4194304 != 0:
            pass
            self.app_custom_data = SamsungNote.Utf16StringU32(self._io, self, self._root)

        if  ((self.integrity_offset > self._io.pos()) and (self.integrity_offset <= self._io.size())) :
            pass
            self.unknown_optional_bytes = self._io.read_bytes(self.integrity_offset - self._io.pos())



    def _fetch_instances(self):
        pass
        self.note_id._fetch_instances()
        if self.property_flags & 1 != 0:
            pass
            self.app_name._fetch_instances()

        if self.property_flags & 2 != 0:
            pass
            self.app_version._fetch_instances()

        if self.property_flags & 4 != 0:
            pass
            self.author_info._fetch_instances()

        if self.property_flags & 8 != 0:
            pass
            self.geo._fetch_instances()

        if self.property_flags & 64 != 0:
            pass
            self.template_uri._fetch_instances()

        if self.property_flags & 128 != 0:
            pass

        if self.property_flags & 512 != 0:
            pass
            self.last_edited_page_image._fetch_instances()

        if self.property_flags & 1024 != 0:
            pass

        if self.property_flags & 1024 != 0:
            pass
            self.string_id_block._fetch_instances()

        if self.property_flags & 2048 != 0:
            pass

        if self.property_flags & 4096 != 0:
            pass
            self.legacy_pen_info._fetch_instances()

        if self.property_flags & 8192 != 0:
            pass
            self.voice_data._fetch_instances()

        if self.property_flags & 16384 != 0:
            pass
            self.attached_files._fetch_instances()

        if self.property_flags & 32768 != 0:
            pass
            self.current_pen_info_block._fetch_instances()

        if self.property_flags & 65536 != 0:
            pass

        if self.property_flags & 131072 != 0:
            pass
            self.fixed_font._fetch_instances()

        if self.property_flags & 262144 != 0:
            pass

        if self.property_flags & 524288 != 0:
            pass

        if self.property_flags & 1048576 != 0:
            pass
            self.text_summarization._fetch_instances()

        if self.property_flags & 2097152 != 0:
            pass

        if self.property_flags & 4194304 != 0:
            pass
            self.app_custom_data._fetch_instances()

        if  ((self.integrity_offset > self._io.pos()) and (self.integrity_offset <= self._io.size())) :
            pass

        _ = self.integrity_hash
        if hasattr(self, '_m_integrity_hash'):
            pass


    class AppVersionBlock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.AppVersionBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.major = self._io.read_s4le()
            self.minor = self._io.read_s4le()
            self.patch_name = SamsungNote.Utf16StringU16(self._io, self, self._root)


        def _fetch_instances(self):
            pass
            self.patch_name._fetch_instances()


    class AttachedFileEntry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.AttachedFileEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.filename = SamsungNote.Utf16StringU16(self._io, self, self._root)
            self.bind_id = self._io.read_s4le()


        def _fetch_instances(self):
            pass
            self.filename._fetch_instances()


    class AttachedFilesBlock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.AttachedFilesBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.num_entries = self._io.read_u2le()
            self.entries = []
            for i in range(self.num_entries):
                self.entries.append(SamsungNote.AttachedFileEntry(self._io, self, self._root))



        def _fetch_instances(self):
            pass
            for i in range(len(self.entries)):
                pass
                self.entries[i]._fetch_instances()



    class AuthorBlock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.AuthorBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.a = SamsungNote.Utf16StringU16(self._io, self, self._root)
            self.b = SamsungNote.Utf16StringU16(self._io, self, self._root)
            self.c = SamsungNote.Utf16StringU16(self._io, self, self._root)
            self.d = self._io.read_s4le()


        def _fetch_instances(self):
            pass
            self.a._fetch_instances()
            self.b._fetch_instances()
            self.c._fetch_instances()


    class GeoBlock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.GeoBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.latitude = self._io.read_f8le()
            self.longitude = self._io.read_f8le()


        def _fetch_instances(self):
            pass


    class LastEditedPageImageBlock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.LastEditedPageImageBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.image_id = self._io.read_s4le()
            self.time_raw = self._io.read_u8le()


        def _fetch_instances(self):
            pass


    class PenInfoCurrent(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.PenInfoCurrent, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.name = SamsungNote.Utf16StringU16(self._io, self, self._root)
            self.size = self._io.read_f4le()
            self.color_int = self._io.read_u4le()
            self.is_curvable = self._io.read_s4le()
            self.advanced_setting = SamsungNote.Utf16StringU16(self._io, self, self._root)
            self.is_eraser_enabled = self._io.read_s4le()
            self.size_level = self._io.read_s4le()
            self.particle_density = self._io.read_s4le()
            self.particle_size = self._io.read_f4le()
            self.is_fixed_width = self._io.read_s4le()
            self.hsv = []
            for i in range(3):
                self.hsv.append(self._io.read_f4le())

            if self._io.pos() + 4 <= self._io.size():
                pass
                self.color_ui_info = self._io.read_s4le()



        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            self.advanced_setting._fetch_instances()
            for i in range(len(self.hsv)):
                pass

            if self._io.pos() + 4 <= self._io.size():
                pass



    class PenInfoLegacy(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.PenInfoLegacy, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.name = SamsungNote.Utf16StringU16(self._io, self, self._root)
            self.size = self._io.read_f4le()
            self.color_int = self._io.read_u4le()
            self.is_curvable = self._io.read_s4le()
            self.advanced_setting = SamsungNote.Utf16StringU16(self._io, self, self._root)
            self.is_eraser_enabled = self._io.read_s4le()
            self.size_level = self._io.read_s4le()
            self.particle_density = self._io.read_s4le()
            self.hsv = []
            for i in range(3):
                self.hsv.append(self._io.read_f4le())

            if self._io.pos() + 4 <= self._io.size():
                pass
                self.color_ui_info = self._io.read_s4le()



        def _fetch_instances(self):
            pass
            self.name._fetch_instances()
            self.advanced_setting._fetch_instances()
            for i in range(len(self.hsv)):
                pass

            if self._io.pos() + 4 <= self._io.size():
                pass



    class SizedCurrentPenInfo(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.SizedCurrentPenInfo, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.block_size = self._io.read_u4le()
            self._raw_body = self._io.read_bytes(self.block_size - 4)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = SamsungNote.PenInfoCurrent(_io__raw_body, self, self._root)


        def _fetch_instances(self):
            pass
            self.body._fetch_instances()


    class StringIdBlock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.StringIdBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.num_entries = self._io.read_u2le()
            self.entries = []
            for i in range(self.num_entries):
                self.entries.append(SamsungNote.StringIdEntry(self._io, self, self._root))



        def _fetch_instances(self):
            pass
            for i in range(len(self.entries)):
                pass
                self.entries[i]._fetch_instances()



    class StringIdEntry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.StringIdEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.string_id = self._io.read_s4le()
            self.value = SamsungNote.Utf16StringU16(self._io, self, self._root)


        def _fetch_instances(self):
            pass
            self.value._fetch_instances()


    class Utf16StringU16(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.Utf16StringU16, self).__init__(_io)
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
            super(SamsungNote.Utf16StringU32, self).__init__(_io)
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



    class VoiceDataBlock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.VoiceDataBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.num_entries = self._io.read_u4le()
            self.entries = []
            for i in range(self.num_entries):
                self.entries.append(SamsungNote.VoiceDataEntry(self._io, self, self._root))



        def _fetch_instances(self):
            pass
            for i in range(len(self.entries)):
                pass
                self.entries[i]._fetch_instances()



    class VoiceDataEntry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNote.VoiceDataEntry, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.entry_size = self._io.read_u4le()
            self.data = self._io.read_bytes(self.entry_size)


        def _fetch_instances(self):
            pass


    @property
    def integrity_hash(self):
        if hasattr(self, '_m_integrity_hash'):
            return self._m_integrity_hash

        if self.integrity_offset + 32 <= self._io.size():
            pass
            _pos = self._io.pos()
            self._io.seek(self.integrity_offset)
            self._m_integrity_hash = self._io.read_bytes(32)
            self._io.seek(_pos)

        return getattr(self, '_m_integrity_hash', None)


