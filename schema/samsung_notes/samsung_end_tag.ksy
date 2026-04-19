meta:
  id: samsung_end_tag
  endian: le
seq:
  - id: payload_size
    type: u2
  - id: payload
    type: payload
    size: payload_size
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
  payload:
    seq:
      - id: format_version
        type: s4
      - id: note_id
        type: utf16_string_u16
      - id: modified_time_raw
        type: u8
      - id: property_flags
        type: s4
      - id: cover_image
        type: utf16_string_u16
      - id: note_width
        type: s4
      - id: note_height
        type: f4
      - id: title
        type: utf16_string_u16
      - id: thumbnail_width
        type: s4
      - id: thumbnail_height
        type: s4
      - id: app_patch_name
        type: utf16_string_u16
      - id: min_format_version
        type: s4
      - id: created_time_raw
        type: u8
      - id: last_viewed_page_index
        type: s4
      - id: page_mode
        type: u2
      - id: document_type
        type: u2
      - id: owner_id
        type: utf16_string_u16
      - id: reserved_zero_1
        type: s4
      - id: reserved_zero_2
        type: s4
      - id: display_created_time_raw
        type: u8
      - id: display_modified_time_raw
        type: u8
      - id: last_recognized_data_modified_time_raw
        type: u8
      - id: fixed_font
        type: utf16_string_u16
      - id: fixed_text_direction
        type: s4
      - id: fixed_background_theme
        type: s4
      - id: server_checkpoint
        type: s8
      - id: new_orientation
        type: s4
      - id: min_unknown_version
        type: s4
      - id: app_custom_data
        type: utf16_string_u32
      - id: footer_marker
        size-eos: true
