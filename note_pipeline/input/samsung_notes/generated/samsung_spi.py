# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SamsungSpi(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        super(SamsungSpi, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._read()

    def _read(self):
        self.header_packet_size = self._io.read_u4le()
        self._raw_header_packet = self._io.read_bytes(self.header_packet_size)
        _io__raw_header_packet = KaitaiStream(BytesIO(self._raw_header_packet))
        self.header_packet = SamsungSpi.HeaderPacket(_io__raw_header_packet, self, self._root)
        self.image_packet_size = self._io.read_u4le()
        self._raw_image_packet = self._io.read_bytes(self.image_packet_size)
        _io__raw_image_packet = KaitaiStream(BytesIO(self._raw_image_packet))
        self.image_packet = SamsungSpi.ImagePacket(_io__raw_image_packet, self, self._root)


    def _fetch_instances(self):
        pass
        self.header_packet._fetch_instances()
        self.image_packet._fetch_instances()

    class HeaderPacket(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungSpi.HeaderPacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.tag = self._io.read_u2be()
            self.reserved = self._io.read_u2be()
            self.record_size = self._io.read_u2be()
            self.record_reserved = self._io.read_u2be()
            self.format_family = self._io.read_u4be()
            self.width = self._io.read_u2le()
            self.height = self._io.read_u2le()
            self.texture_width_units = self._io.read_u2be()
            self.fixed_00e0 = self._io.read_u2be()


        def _fetch_instances(self):
            pass

        @property
        def texture_width(self):
            if hasattr(self, '_m_texture_width'):
                return self._m_texture_width

            self._m_texture_width = self.texture_width_units * 256
            return getattr(self, '_m_texture_width', None)


    class ImagePacket(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungSpi.ImagePacket, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.tag = self._io.read_u2be()
            self.reserved = self._io.read_u2be()
            self.size_hint = self._io.read_u4le()
            self.payload = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    @property
    def image_packet_size_matches_file_size(self):
        if hasattr(self, '_m_image_packet_size_matches_file_size'):
            return self._m_image_packet_size_matches_file_size

        self._m_image_packet_size_matches_file_size = self.image_packet_size == (self._io.size() - 8) - self.header_packet_size
        return getattr(self, '_m_image_packet_size_matches_file_size', None)


