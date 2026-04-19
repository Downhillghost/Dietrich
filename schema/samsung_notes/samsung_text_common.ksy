meta:
  id: samsung_text_common
  endian: le
params:
  - id: format_version
    type: u4
seq:
  - id: text_length
    type: u4
    valid:
      max: 250000
  - id: text
    type: str
    size: text_length * 2
    encoding: UTF-16LE
  - id: span_count
    type: u4
    valid:
      max: 10000
  - id: spans
    type: span_record
    repeat: expr
    repeat-expr: span_count
  - id: paragraph_count
    type: u4
    valid:
      max: 10000
  - id: paragraphs
    type: paragraph_record
    repeat: expr
    repeat-expr: paragraph_count
  - id: margins
    type: f4
    repeat: expr
    repeat-expr: 4
  - id: text_gravity
    type: u1
  - id: object_count
    type: u2
    valid:
      max: 4096
  - id: object_refs
    type: object_ref
    repeat: expr
    repeat-expr: object_count
  - id: object_span_flags
    type: u4
    if: format_version >= 2035
  - id: object_span_reserved
    type: u4
    if: format_version >= 2035
  - id: object_span_count
    type: u4
    valid:
      max: 4096
    if: format_version >= 2035 and (object_span_flags & 1) != 0
  - id: object_spans
    type: object_span_record
    repeat: expr
    repeat-expr: object_span_count
    if: format_version >= 2035 and (object_span_flags & 1) != 0
types:
  span_record:
    seq:
      - id: payload_size
        type: u2
        valid:
          min: 20
      - id: body
        type: span_body
        size: payload_size
  span_body:
    seq:
      - id: span_type
        type: u4
      - id: start
        type: u4
      - id: end
        type: u4
      - id: expand_flag
        type: u4
      - id: extra
        type:
          switch-on: span_type
          cases:
            1: i32_extra
            3: f32_extra
            4: font_name_extra
            5: bool_extra
            6: bool_extra
            7: underline_extra
            17: i32_extra
            20: bool_extra
        size-eos: true
  paragraph_record:
    seq:
      - id: payload_size
        type: u2
        valid:
          min: 20
      - id: body
        type: paragraph_body
        size: payload_size
  paragraph_body:
    seq:
      - id: paragraph_type
        type: u4
      - id: start
        type: u4
      - id: end
        type: u4
      - id: extra
        type:
          switch-on: paragraph_type
          cases:
            1: u32_extra
            2: two_u32_extra
            3: u32_extra
            4: line_spacing_extra
            5: two_u32_extra
            6: u32_extra
        size-eos: true
  object_ref:
    seq:
      - id: a
        type: u4
      - id: b
        type: u4
  object_span_record:
    seq:
      - id: record_size
        type: u4
      - id: body
        type: object_span_body
        size: record_size
  object_span_body:
    seq:
      - id: object_binary_size
        type: u4
      - id: object_type
        type: u4
      - id: object_blob
        size: object_binary_size
      - id: span_target
        type: u4
        if: _io.pos + 4 <= _io.size
      - id: extra
        size-eos: true
  bool_extra:
    seq:
      - id: value
        type: u1
      - id: extra
        size-eos: true
  f32_extra:
    seq:
      - id: value
        type: f4
      - id: extra
        size-eos: true
  i32_extra:
    seq:
      - id: value
        type: s4
      - id: extra
        size-eos: true
  u32_extra:
    seq:
      - id: value
        type: u4
      - id: extra
        size-eos: true
  two_u32_extra:
    seq:
      - id: first
        type: u4
      - id: second
        type: u4
      - id: extra
        size-eos: true
  font_name_extra:
    seq:
      - id: unknown_prefix
        size: 8
      - id: len_name
        type: u2
      - id: value
        type: str
        size: len_name * 2
        encoding: UTF-16LE
      - id: extra
        size-eos: true
  underline_extra:
    seq:
      - id: value
        type: u1
      - id: underline_type
        type: u1
      - id: unknown_02
        size: 2
      - id: underline_color
        type: s4
      - id: extra
        size-eos: true
  line_spacing_extra:
    seq:
      - id: spacing_type
        type: u1
      - id: unknown_01
        size: 3
      - id: spacing
        type: f4
      - id: extra
        size-eos: true
