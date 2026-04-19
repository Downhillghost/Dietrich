# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class SamsungTextCommon(KaitaiStruct):
    def __init__(self, format_version, _io, _parent=None, _root=None):
        super(SamsungTextCommon, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self.format_version = format_version
        self._read()

    def _read(self):
        self.text_length = self._io.read_u4le()
        if not self.text_length <= 250000:
            raise kaitaistruct.ValidationGreaterThanError(250000, self.text_length, self._io, u"/seq/0")
        self.text = (self._io.read_bytes(self.text_length * 2)).decode(u"UTF-16LE")
        self.span_count = self._io.read_u4le()
        if not self.span_count <= 10000:
            raise kaitaistruct.ValidationGreaterThanError(10000, self.span_count, self._io, u"/seq/2")
        self.spans = []
        for i in range(self.span_count):
            self.spans.append(SamsungTextCommon.SpanRecord(self._io, self, self._root))

        self.paragraph_count = self._io.read_u4le()
        if not self.paragraph_count <= 10000:
            raise kaitaistruct.ValidationGreaterThanError(10000, self.paragraph_count, self._io, u"/seq/4")
        self.paragraphs = []
        for i in range(self.paragraph_count):
            self.paragraphs.append(SamsungTextCommon.ParagraphRecord(self._io, self, self._root))

        self.margins = []
        for i in range(4):
            self.margins.append(self._io.read_f4le())

        self.text_gravity = self._io.read_u1()
        self.object_count = self._io.read_u2le()
        if not self.object_count <= 4096:
            raise kaitaistruct.ValidationGreaterThanError(4096, self.object_count, self._io, u"/seq/8")
        self.object_refs = []
        for i in range(self.object_count):
            self.object_refs.append(SamsungTextCommon.ObjectRef(self._io, self, self._root))

        if self.format_version >= 2035:
            pass
            self.object_span_flags = self._io.read_u4le()

        if self.format_version >= 2035:
            pass
            self.object_span_reserved = self._io.read_u4le()

        if  ((self.format_version >= 2035) and (self.object_span_flags & 1 != 0)) :
            pass
            self.object_span_count = self._io.read_u4le()
            if not self.object_span_count <= 4096:
                raise kaitaistruct.ValidationGreaterThanError(4096, self.object_span_count, self._io, u"/seq/12")

        if  ((self.format_version >= 2035) and (self.object_span_flags & 1 != 0)) :
            pass
            self.object_spans = []
            for i in range(self.object_span_count):
                self.object_spans.append(SamsungTextCommon.ObjectSpanRecord(self._io, self, self._root))




    def _fetch_instances(self):
        pass
        for i in range(len(self.spans)):
            pass
            self.spans[i]._fetch_instances()

        for i in range(len(self.paragraphs)):
            pass
            self.paragraphs[i]._fetch_instances()

        for i in range(len(self.margins)):
            pass

        for i in range(len(self.object_refs)):
            pass
            self.object_refs[i]._fetch_instances()

        if self.format_version >= 2035:
            pass

        if self.format_version >= 2035:
            pass

        if  ((self.format_version >= 2035) and (self.object_span_flags & 1 != 0)) :
            pass

        if  ((self.format_version >= 2035) and (self.object_span_flags & 1 != 0)) :
            pass
            for i in range(len(self.object_spans)):
                pass
                self.object_spans[i]._fetch_instances()



    class BoolExtra(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.BoolExtra, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.value = self._io.read_u1()
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class F32Extra(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.F32Extra, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.value = self._io.read_f4le()
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class FontNameExtra(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.FontNameExtra, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.unknown_prefix = self._io.read_bytes(8)
            self.len_name = self._io.read_u2le()
            self.value = (self._io.read_bytes(self.len_name * 2)).decode(u"UTF-16LE")
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class I32Extra(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.I32Extra, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.value = self._io.read_s4le()
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class LineSpacingExtra(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.LineSpacingExtra, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.spacing_type = self._io.read_u1()
            self.unknown_01 = self._io.read_bytes(3)
            self.spacing = self._io.read_f4le()
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class ObjectRef(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.ObjectRef, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.a = self._io.read_u4le()
            self.b = self._io.read_u4le()


        def _fetch_instances(self):
            pass


    class ObjectSpanBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.ObjectSpanBody, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.object_binary_size = self._io.read_u4le()
            self.object_type = self._io.read_u4le()
            self.object_blob = self._io.read_bytes(self.object_binary_size)
            if self._io.pos() + 4 <= self._io.size():
                pass
                self.span_target = self._io.read_u4le()

            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass
            if self._io.pos() + 4 <= self._io.size():
                pass



    class ObjectSpanRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.ObjectSpanRecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.record_size = self._io.read_u4le()
            self._raw_body = self._io.read_bytes(self.record_size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = SamsungTextCommon.ObjectSpanBody(_io__raw_body, self, self._root)


        def _fetch_instances(self):
            pass
            self.body._fetch_instances()


    class ParagraphBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.ParagraphBody, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.paragraph_type = self._io.read_u4le()
            self.start = self._io.read_u4le()
            self.end = self._io.read_u4le()
            _on = self.paragraph_type
            if _on == 1:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.U32Extra(_io__raw_extra, self, self._root)
            elif _on == 2:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.TwoU32Extra(_io__raw_extra, self, self._root)
            elif _on == 3:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.U32Extra(_io__raw_extra, self, self._root)
            elif _on == 4:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.LineSpacingExtra(_io__raw_extra, self, self._root)
            elif _on == 5:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.TwoU32Extra(_io__raw_extra, self, self._root)
            elif _on == 6:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.U32Extra(_io__raw_extra, self, self._root)
            else:
                pass
                self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass
            _on = self.paragraph_type
            if _on == 1:
                pass
                self.extra._fetch_instances()
            elif _on == 2:
                pass
                self.extra._fetch_instances()
            elif _on == 3:
                pass
                self.extra._fetch_instances()
            elif _on == 4:
                pass
                self.extra._fetch_instances()
            elif _on == 5:
                pass
                self.extra._fetch_instances()
            elif _on == 6:
                pass
                self.extra._fetch_instances()
            else:
                pass


    class ParagraphRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.ParagraphRecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.payload_size = self._io.read_u2le()
            if not self.payload_size >= 20:
                raise kaitaistruct.ValidationLessThanError(20, self.payload_size, self._io, u"/types/paragraph_record/seq/0")
            self._raw_body = self._io.read_bytes(self.payload_size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = SamsungTextCommon.ParagraphBody(_io__raw_body, self, self._root)


        def _fetch_instances(self):
            pass
            self.body._fetch_instances()


    class SpanBody(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.SpanBody, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.span_type = self._io.read_u4le()
            self.start = self._io.read_u4le()
            self.end = self._io.read_u4le()
            self.expand_flag = self._io.read_u4le()
            _on = self.span_type
            if _on == 1:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.I32Extra(_io__raw_extra, self, self._root)
            elif _on == 17:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.I32Extra(_io__raw_extra, self, self._root)
            elif _on == 20:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.BoolExtra(_io__raw_extra, self, self._root)
            elif _on == 3:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.F32Extra(_io__raw_extra, self, self._root)
            elif _on == 4:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.FontNameExtra(_io__raw_extra, self, self._root)
            elif _on == 5:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.BoolExtra(_io__raw_extra, self, self._root)
            elif _on == 6:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.BoolExtra(_io__raw_extra, self, self._root)
            elif _on == 7:
                pass
                self._raw_extra = self._io.read_bytes_full()
                _io__raw_extra = KaitaiStream(BytesIO(self._raw_extra))
                self.extra = SamsungTextCommon.UnderlineExtra(_io__raw_extra, self, self._root)
            else:
                pass
                self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass
            _on = self.span_type
            if _on == 1:
                pass
                self.extra._fetch_instances()
            elif _on == 17:
                pass
                self.extra._fetch_instances()
            elif _on == 20:
                pass
                self.extra._fetch_instances()
            elif _on == 3:
                pass
                self.extra._fetch_instances()
            elif _on == 4:
                pass
                self.extra._fetch_instances()
            elif _on == 5:
                pass
                self.extra._fetch_instances()
            elif _on == 6:
                pass
                self.extra._fetch_instances()
            elif _on == 7:
                pass
                self.extra._fetch_instances()
            else:
                pass


    class SpanRecord(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.SpanRecord, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.payload_size = self._io.read_u2le()
            if not self.payload_size >= 20:
                raise kaitaistruct.ValidationLessThanError(20, self.payload_size, self._io, u"/types/span_record/seq/0")
            self._raw_body = self._io.read_bytes(self.payload_size)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = SamsungTextCommon.SpanBody(_io__raw_body, self, self._root)


        def _fetch_instances(self):
            pass
            self.body._fetch_instances()


    class TwoU32Extra(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.TwoU32Extra, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.first = self._io.read_u4le()
            self.second = self._io.read_u4le()
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class U32Extra(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.U32Extra, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.value = self._io.read_u4le()
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass


    class UnderlineExtra(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(SamsungTextCommon.UnderlineExtra, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.value = self._io.read_u1()
            self.underline_type = self._io.read_u1()
            self.unknown_02 = self._io.read_bytes(2)
            self.underline_color = self._io.read_s4le()
            self.extra = self._io.read_bytes_full()


        def _fetch_instances(self):
            pass



