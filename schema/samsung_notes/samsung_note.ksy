meta:
  id: samsung_note
  endian: le
seq:
  - id: integrity_offset
    type: u4
  - id: header_constant_1
    type: u1
  - id: header_flags
    type: u4
  - id: header_constant_2
    type: u1
  - id: property_flags
    type: u4
  - id: format_version
    type: u4
  - id: note_id
    type: utf16_string_u16
  - id: file_revision
    type: u4
  - id: created_time_raw
    type: u8
  - id: modified_time_raw
    type: u8
  - id: width
    type: u4
  - id: height
    type: u4
  - id: page_horizontal_padding
    type: u4
  - id: page_vertical_padding
    type: u4
  - id: min_format_version
    type: u4
  - id: title_object_size
    type: u4
  - id: title_object
    size: title_object_size
  - id: body_object_size
    type: u4
  - id: body_object
    size: body_object_size
  - id: app_name
    type: utf16_string_u16
    if: (property_flags & 1) != 0
  - id: app_version
    type: app_version_block
    if: (property_flags & 2) != 0
  - id: author_info
    type: author_block
    if: (property_flags & 4) != 0
  - id: geo
    type: geo_block
    if: (property_flags & 8) != 0
  - id: template_uri
    type: utf16_string_u16
    if: (property_flags & 64) != 0
  - id: last_edited_page_index
    type: s4
    if: (property_flags & 128) != 0
  - id: last_edited_page_image
    type: last_edited_page_image_block
    if: (property_flags & 512) != 0
  - id: string_id_block_size
    type: u4
    if: (property_flags & 1024) != 0
  - id: string_id_block
    type: string_id_block
    size: string_id_block_size
    if: (property_flags & 1024) != 0
  - id: body_text_font_size_delta
    type: s4
    if: (property_flags & 2048) != 0
  - id: legacy_pen_info
    type: pen_info_legacy
    if: (property_flags & 4096) != 0
  - id: voice_data
    type: voice_data_block
    if: (property_flags & 8192) != 0
  - id: attached_files
    type: attached_files_block
    if: (property_flags & 16384) != 0
  - id: current_pen_info_block
    type: sized_current_pen_info
    if: (property_flags & 32768) != 0
  - id: last_recognized_data_modified_time_raw
    type: u8
    if: (property_flags & 65536) != 0
  - id: fixed_font
    type: utf16_string_u16
    if: (property_flags & 131072) != 0
  - id: fixed_text_direction
    type: s4
    if: (property_flags & 262144) != 0
  - id: fixed_background_theme
    type: s4
    if: (property_flags & 524288) != 0
  - id: text_summarization
    type: utf16_string_u16
    if: (property_flags & 1048576) != 0
  - id: stroke_group_size
    type: s4
    if: (property_flags & 2097152) != 0
  - id: app_custom_data
    type: utf16_string_u32
    if: (property_flags & 4194304) != 0
  - id: unknown_optional_bytes
    size: integrity_offset - _io.pos
    if: integrity_offset > _io.pos and integrity_offset <= _io.size
instances:
  integrity_hash:
    pos: integrity_offset
    size: 32
    if: integrity_offset + 32 <= _io.size
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
  utf16_string_u32:
    seq:
      - id: len
        type: u4
      - id: value
        type: str
        size: len * 2
        encoding: UTF-16LE
        if: len != 4294967295
  app_version_block:
    seq:
      - id: major
        type: s4
      - id: minor
        type: s4
      - id: patch_name
        type: utf16_string_u16
  author_block:
    seq:
      - id: a
        type: utf16_string_u16
      - id: b
        type: utf16_string_u16
      - id: c
        type: utf16_string_u16
      - id: d
        type: s4
  geo_block:
    seq:
      - id: latitude
        type: f8
      - id: longitude
        type: f8
  last_edited_page_image_block:
    seq:
      - id: image_id
        type: s4
      - id: time_raw
        type: u8
  string_id_block:
    seq:
      - id: num_entries
        type: u2
      - id: entries
        type: string_id_entry
        repeat: expr
        repeat-expr: num_entries
  string_id_entry:
    seq:
      - id: string_id
        type: s4
      - id: value
        type: utf16_string_u16
  pen_info_legacy:
    seq:
      - id: name
        type: utf16_string_u16
      - id: size
        type: f4
      - id: color_int
        type: u4
      - id: is_curvable
        type: s4
      - id: advanced_setting
        type: utf16_string_u16
      - id: is_eraser_enabled
        type: s4
      - id: size_level
        type: s4
      - id: particle_density
        type: s4
      - id: hsv
        type: f4
        repeat: expr
        repeat-expr: 3
      - id: color_ui_info
        type: s4
        if: _io.pos + 4 <= _io.size
  pen_info_current:
    seq:
      - id: name
        type: utf16_string_u16
      - id: size
        type: f4
      - id: color_int
        type: u4
      - id: is_curvable
        type: s4
      - id: advanced_setting
        type: utf16_string_u16
      - id: is_eraser_enabled
        type: s4
      - id: size_level
        type: s4
      - id: particle_density
        type: s4
      - id: particle_size
        type: f4
      - id: is_fixed_width
        type: s4
      - id: hsv
        type: f4
        repeat: expr
        repeat-expr: 3
      - id: color_ui_info
        type: s4
        if: _io.pos + 4 <= _io.size
  sized_current_pen_info:
    seq:
      - id: block_size
        type: u4
      - id: body
        type: pen_info_current
        size: block_size - 4
  voice_data_block:
    seq:
      - id: num_entries
        type: u4
      - id: entries
        type: voice_data_entry
        repeat: expr
        repeat-expr: num_entries
  voice_data_entry:
    seq:
      - id: entry_size
        type: u4
      - id: data
        size: entry_size
  attached_files_block:
    seq:
      - id: num_entries
        type: u2
      - id: entries
        type: attached_file_entry
        repeat: expr
        repeat-expr: num_entries
  attached_file_entry:
    seq:
      - id: filename
        type: utf16_string_u16
      - id: bind_id
        type: s4
