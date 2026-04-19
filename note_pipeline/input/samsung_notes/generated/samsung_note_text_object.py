# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SamsungNoteTextObject(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        super(SamsungNoteTextObject, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._read()

    def _read(self):
        self.object_base_size = self._io.read_u4le()
        if not self.object_base_size >= 4:
            raise kaitaistruct.ValidationLessThanError(4, self.object_base_size, self._io, u"/seq/0")
        self.object_base_body = self._io.read_bytes(self.object_base_size - 4)
        self.shape_base_size = self._io.read_u4le()
        if not self.shape_base_size >= 4:
            raise kaitaistruct.ValidationLessThanError(4, self.shape_base_size, self._io, u"/seq/2")
        self.shape_base_body = self._io.read_bytes(self.shape_base_size - 4)
        self.shape_text_record_size = self._io.read_u4le()
        if not self.shape_text_record_size >= 17:
            raise kaitaistruct.ValidationLessThanError(17, self.shape_text_record_size, self._io, u"/seq/4")
        self._raw_shape_text_record = self._io.read_bytes(self.shape_text_record_size - 4)
        _io__raw_shape_text_record = KaitaiStream(BytesIO(self._raw_shape_text_record))
        self.shape_text_record = SamsungNoteTextObject.ShapeTextRecord(_io__raw_shape_text_record, self, self._root)
        self.trailing_bytes = self._io.read_bytes_full()


    def _fetch_instances(self):
        pass
        self.shape_text_record._fetch_instances()
        _ = self.text_common_bytes
        if hasattr(self, '_m_text_common_bytes'):
            pass

        _ = self.text_common_size
        if hasattr(self, '_m_text_common_size'):
            pass


    class ShapeTextRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungNoteTextObject.ShapeTextRecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.record_type = self._io.read_u2le()
            self.own_data_offset = self._io.read_u4le()
            self.unknown_06 = self._io.read_bytes(3)
            self.property_mask = self._io.read_u4le()
            self.remaining = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    @property
    def has_text_common(self):
        if hasattr(self, '_m_has_text_common'):
            return self._m_has_text_common

        self._m_has_text_common =  ((self.shape_text_record.record_type == 7) and (self.shape_text_record.property_mask & 1 != 0) and (self.text_common_size_offset + 4 <= self._io.size())) 
        return getattr(self, '_m_has_text_common', None)

    @property
    def shape_text_record_offset(self):
        if hasattr(self, '_m_shape_text_record_offset'):
            return self._m_shape_text_record_offset

        self._m_shape_text_record_offset = self.object_base_size + self.shape_base_size
        return getattr(self, '_m_shape_text_record_offset', None)

    @property
    def text_common_bytes(self):
        if hasattr(self, '_m_text_common_bytes'):
            return self._m_text_common_bytes

        if  ((self.has_text_common) and (self.text_common_size <= (self._io.size() - self.text_common_size_offset) - 4)) :
            pass
            _pos = self._io.pos()
            self._io.seek(self.text_common_size_offset + 4)
            self._m_text_common_bytes = self._io.read_bytes(self.text_common_size)
            self._io.seek(_pos)

        return getattr(self, '_m_text_common_bytes', None)

    @property
    def text_common_size(self):
        if hasattr(self, '_m_text_common_size'):
            return self._m_text_common_size

        if self.has_text_common:
            pass
            _pos = self._io.pos()
            self._io.seek(self.text_common_size_offset)
            self._m_text_common_size = self._io.read_u4le()
            self._io.seek(_pos)

        return getattr(self, '_m_text_common_size', None)

    @property
    def text_common_size_offset(self):
        if hasattr(self, '_m_text_common_size_offset'):
            return self._m_text_common_size_offset

        self._m_text_common_size_offset = self.shape_text_record_offset + self.shape_text_record.own_data_offset
        return getattr(self, '_m_text_common_size_offset', None)


