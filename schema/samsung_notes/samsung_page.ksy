meta:
  id: samsung_page
  endian: le
seq:
  - id: raw_layer_offset
    type: u4
  - id: property_offset
    type: u4
  - id: unknown_08
    type: u1
  - id: text_only_flag
    type: u4
  - id: unknown_0d
    type: u1
  - id: page_property_mask
    type: u4
  - id: note_orientation
    type: u4
  - id: page_width
    type: u4
  - id: page_height
    type: u4
  - id: offset_x
    type: u4
  - id: offset_y
    type: u4
  - id: page_uuid
    type: utf16_string_u16
  - id: modified_time_raw
    type: u8
    if: _io.pos + 8 <= _io.size
  - id: format_version
    type: u4
    if: _io.pos + 4 <= _io.size
  - id: min_format_version
    type: u4
    if: _io.pos + 4 <= _io.size
instances:
  properties:
    pos: property_offset
    size: _io.size - property_offset
    type: page_properties(page_property_mask, format_version)
    if: property_offset < _io.size
types:
  utf16_string_u16:
    seq:
      - id: len
        type: u2
      - id: value
        type: str
        size: len * 2
        encoding: UTF-16LE
        if: len != 65535
  counted_utf8_u32:
    seq:
      - id: len
        type: u4
      - id: value
        type: str
        size: len
        encoding: UTF-8
  utf8_u16_bytes:
    seq:
      - id: len
        type: u2
      - id: raw_value
        size: len
  rect_f32:
    seq:
      - id: left
        type: f4
      - id: top
        type: f4
      - id: right
        type: f4
      - id: bottom
        type: f4
  rect_f64:
    seq:
      - id: left
        type: f8
      - id: top
        type: f8
      - id: right
        type: f8
      - id: bottom
        type: f8
  rect_i32:
    seq:
      - id: left
        type: s4
      - id: top
        type: s4
      - id: right
        type: s4
      - id: bottom
        type: s4
  page_properties:
    params:
      - id: property_mask
        type: u4
      - id: format_version
        type: u4
    seq:
      - id: drawn_rect
        type: rect_f64
        if: (property_mask & 1) != 0
      - id: tags
        type: tag_list
        if: (property_mask & 2) != 0
      - id: template_uri
        type: utf16_string_u16
        if: (property_mask & 4) != 0
      - id: bg_image_id
        type: u4
        if: (property_mask & 8) != 0
      - id: bg_image_mode
        type: u4
        if: (property_mask & 16) != 0
      - id: background_color_int
        type: u4
        if: (property_mask & 32) != 0
      - id: bg_width
        type: u4
        if: (property_mask & 64) != 0
      - id: bg_rotation
        type: u4
        if: (property_mask & 128) != 0
      - id: pdf_data
        type: pdf_data_list(format_version)
        if: (property_mask & 256) != 0
      - id: template_type
        type: u4
        if: (property_mask & 512) != 0
      - id: canvas_cache
        type: canvas_cache_list
        if: (property_mask & 1024) != 0
      - id: imported_data_height
        type: u4
        if: (property_mask & 2048) != 0
      - id: reserved_0x1000
        type: u4
        if: (property_mask & 4096) != 0
      - id: custom_objects
        type: custom_object_list
        if: (property_mask & 262144) != 0
  tag_list:
    seq:
      - id: num_tags
        type: u2
      - id: tags
        type: utf16_string_u16
        repeat: expr
        repeat-expr: num_tags
  pdf_data_list:
    params:
      - id: format_version
        type: u4
    seq:
      - id: num_entries
        type: u2
      - id: entries
        type: pdf_data_entry(format_version)
        repeat: expr
        repeat-expr: num_entries
  pdf_data_entry:
    params:
      - id: format_version
        type: u4
    seq:
      - id: file_id
        type: s4
      - id: page_index
        type: s4
      - id: rect_as_f32
        type: rect_f32
        if: format_version != 0 and format_version < 2034
      - id: rect_as_i32
        type: rect_i32
        if: format_version == 0 or format_version >= 2034
  canvas_cache_list:
    seq:
      - id: num_entries
        type: u4
      - id: record_size
        type: u2
      - id: entries
        type: canvas_cache_entry
        size: record_size
        repeat: expr
        repeat-expr: num_entries
  canvas_cache_entry:
    seq:
      - id: key
        type: u4
      - id: file_id
        type: u4
      - id: width
        type: u4
      - id: height
        type: u4
      - id: is_dark_mode
        type: u1
      - id: background_color_int
        type: u4
      - id: version0
        type: u4
      - id: version1
        type: u4
      - id: version2
        type: u4
      - id: cache_version
        type: u4
      - id: property
        type: u4
      - id: locale_list_id
        type: u4
      - id: system_font_path_hash
        type: u4
      - id: extra
        size-eos: true
  custom_object_list:
    seq:
      - id: num_entries
        type: u4
      - id: entries
        type: custom_object_entry
        repeat: expr
        repeat-expr: num_entries
  custom_object_entry:
    seq:
      - id: object_type
        type: u4
      - id: payload_size
        type: u4
      - id: payload
        size: payload_size
