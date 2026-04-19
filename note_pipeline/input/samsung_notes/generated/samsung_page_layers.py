# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SamsungPageLayers(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        super(SamsungPageLayers, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._read()

    def _read(self):
        self.layer_count = self._io.read_u2le()
        if not self.layer_count >= 1:
            raise kaitaistruct.ValidationLessThanError(1, self.layer_count, self._io, u"/seq/0")
        if not self.layer_count <= 64:
            raise kaitaistruct.ValidationGreaterThanError(64, self.layer_count, self._io, u"/seq/0")
        self.current_layer_index = self._io.read_u2le()
        if not self.current_layer_index <= self.layer_count - 1:
            raise kaitaistruct.ValidationGreaterThanError(self.layer_count - 1, self.current_layer_index, self._io, u"/seq/1")
        self.layers = []
        for i in range(self.layer_count):
            self.layers.append(SamsungPageLayers.Layer(self._io, self, self._root))



    def _fetch_instances(self):
        pass
        for i in range(len(self.layers)):
            pass
            self.layers[i]._fetch_instances()


    class ImageLayoutOwnBlock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageLayers.ImageLayoutOwnBlock, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.block_size = self._io.read_u4le()
            self.unknown_04 = self._io.read_u2le()
            self.layout_type = self._io.read_u4le()
            self.alpha = self._io.read_u4le()
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class ImageLayoutSubrecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageLayers.ImageLayoutSubrecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.own_offset = self._io.read_u4le()
            self.raw_after_own_offset = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass
            _ = self.own_block
            if hasattr(self, '_m_own_block'):
                pass
                self._m_own_block._fetch_instances()


        @property
        def own_block(self):
            if hasattr(self, '_m_own_block'):
                return self._m_own_block

            if  ((self.own_offset >= 6) and (self.own_offset - 6 < self._io.size())) :
                pass
                _pos = self._io.pos()
                self._io.seek(self.own_offset - 6)
                self._m_own_block = SamsungPageLayers.ImageLayoutOwnBlock(self._io, self, self._root)
                self._io.seek(_pos)

            return getattr(self, '_m_own_block', None)


    class ImageOwnSubrecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageLayers.ImageOwnSubrecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.flexible_payload_present = self._io.read_u1()
            self.unknown_01 = self._io.read_bytes(6)
            self.group1_flags = self._io.read_u1()
            self.group2_flags = self._io.read_u1()
            self.group3_flags = self._io.read_u1()
            self.unknown_0a = self._io.read_u1()
            self.flexible_payload = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class Layer(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageLayers.Layer, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.header_size = self._io.read_u4le()
            if not self.header_size >= 16:
                raise kaitaistruct.ValidationLessThanError(16, self.header_size, self._io, u"/types/layer/seq/0")
            if not self.header_size <= 16384:
                raise kaitaistruct.ValidationGreaterThanError(16384, self.header_size, self._io, u"/types/layer/seq/0")
            self.metadata_offset_abs = self._io.read_u4le()
            self.unknown_08 = self._io.read_u1()
            self.flags_1 = self._io.read_u1()
            self.unknown_0a = self._io.read_u1()
            self.flags_2 = self._io.read_u1()
            self.layer_number = self._io.read_u4le()
            self.header_extra = self._io.read_bytes(self.header_size - 16)
            self.object_count = self._io.read_u4le()
            if not self.object_count <= 4096:
                raise kaitaistruct.ValidationGreaterThanError(4096, self.object_count, self._io, u"/types/layer/seq/8")
            self.objects = []
            for i in range(self.object_count):
                self.objects.append(SamsungPageLayers.ObjectRecord(self._io, self, self._root))

            if self._io.pos() + 32 <= self._io.size():
                pass
                self.trailer = self._io.read_bytes(32)



        def _fetch_instances(self):
            pass
            for i in range(len(self.objects)):
                pass
                self.objects[i]._fetch_instances()

            if self._io.pos() + 32 <= self._io.size():
                pass



    class ObjectRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageLayers.ObjectRecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.object_type = self._io.read_u1()
            self.child_count = self._io.read_u2le()
            self.object_size = self._io.read_u4le()
            if not self.object_size >= 32:
                raise kaitaistruct.ValidationLessThanError(32, self.object_size, self._io, u"/types/object_record/seq/2")
            self.payload_bytes = self._io.read_bytes(self.object_size - 32)
            self.trailer = self._io.read_bytes(32)
            self.children = []
            for i in range(self.child_count):
                self.children.append(SamsungPageLayers.ObjectRecord(self._io, self, self._root))



        def _fetch_instances(self):
            pass
            for i in range(len(self.children)):
                pass
                self.children[i]._fetch_instances()



    class RectF64(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageLayers.RectF64, self).__init__(_io)
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
            super(SamsungPageLayers.RectI32, self).__init__(_io)
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


    class ShapeImageSubrecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageLayers.ShapeImageSubrecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.own_offset = self._io.read_u4le()
            self.unknown_04 = self._io.read_bytes(3)
            self.shape_property_mask = self._io.read_u4le()
            self.shape_type = self._io.read_u4le()
            self.original_rect = SamsungPageLayers.RectF64(self._io, self, self._root)
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass
            self.original_rect._fetch_instances()


    class StrokeSubrecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageLayers.StrokeSubrecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.flexible_offset = self._io.read_u4le()
            self.property_mask1_length = self._io.read_u1()
            self.property_mask1_bytes = self._io.read_bytes(self.property_mask1_length)
            self.property_mask2_length = self._io.read_u1()
            self.property_mask2_bytes = self._io.read_bytes(self.property_mask2_length)
            self.point_count = self._io.read_u2le()
            self.geometry_and_flexible = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class Subrecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungPageLayers.Subrecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.size = self._io.read_u4le()
            self.record_type = self._io.read_u2le()
            _on = self.record_type
            if _on == 1:
                pass
                self._raw_body = self._io.read_bytes(self.size - 6)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = SamsungPageLayers.StrokeSubrecord(_io__raw_body, self, self._root)
            elif _on == 3:
                pass
                self._raw_body = self._io.read_bytes(self.size - 6)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = SamsungPageLayers.ImageOwnSubrecord(_io__raw_body, self, self._root)
            elif _on == 6:
                pass
                self._raw_body = self._io.read_bytes(self.size - 6)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = SamsungPageLayers.ImageLayoutSubrecord(_io__raw_body, self, self._root)
            elif _on == 7:
                pass
                self._raw_body = self._io.read_bytes(self.size - 6)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = SamsungPageLayers.ShapeImageSubrecord(_io__raw_body, self, self._root)
            else:
                pass
                self.body = self._io.read_bytes(self.size - 6)


        def _fetch_instances(self):
            pass
            _on = self.record_type
            if _on == 1:
                pass
                self.body._fetch_instances()
            elif _on == 3:
                pass
                self.body._fetch_instances()
            elif _on == 6:
                pass
                self.body._fetch_instances()
            elif _on == 7:
                pass
                self.body._fetch_instances()
            else:
                pass



