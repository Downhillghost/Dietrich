meta:
  id: samsung_page_layers
  endian: le
seq:
  - id: layer_count
    type: u2
    valid:
      min: 1
      max: 64
  - id: current_layer_index
    type: u2
    valid:
      max: layer_count - 1
  - id: layers
    type: layer
    repeat: expr
    repeat-expr: layer_count
types:
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
  layer:
    seq:
      - id: header_size
        type: u4
        valid:
          min: 16
          max: 16384
      - id: metadata_offset_abs
        type: u4
      - id: unknown_08
        type: u1
      - id: flags_1
        type: u1
      - id: unknown_0a
        type: u1
      - id: flags_2
        type: u1
      - id: layer_number
        type: u4
      - id: header_extra
        size: header_size - 16
      - id: object_count
        type: u4
        valid:
          max: 4096
      - id: objects
        type: object_record
        repeat: expr
        repeat-expr: object_count
      - id: trailer
        size: 32
        if: _io.pos + 32 <= _io.size
  object_record:
    seq:
      - id: object_type
        type: u1
      - id: child_count
        type: u2
      - id: object_size
        type: u4
        valid:
          min: 32
      - id: payload_bytes
        size: object_size - 32
      - id: trailer
        size: 32
      - id: children
        type: object_record
        repeat: expr
        repeat-expr: child_count
  subrecord:
    seq:
      - id: size
        type: u4
      - id: record_type
        type: u2
      - id: body
        type:
          switch-on: record_type
          cases:
            1: stroke_subrecord
            3: image_own_subrecord
            6: image_layout_subrecord
            7: shape_image_subrecord
        size: size - 6
  stroke_subrecord:
    seq:
      - id: flexible_offset
        type: u4
      - id: property_mask1_length
        type: u1
      - id: property_mask1_bytes
        size: property_mask1_length
      - id: property_mask2_length
        type: u1
      - id: property_mask2_bytes
        size: property_mask2_length
      - id: point_count
        type: u2
      - id: geometry_and_flexible
        size-eos: true
  image_layout_subrecord:
    seq:
      - id: own_offset
        type: u4
      - id: raw_after_own_offset
        size-eos: true
    instances:
      own_block:
        pos: own_offset - 6
        type: image_layout_own_block
        if: own_offset >= 6 and own_offset - 6 < _io.size
  image_layout_own_block:
    seq:
      - id: block_size
        type: u4
      - id: unknown_04
        type: u2
      - id: layout_type
        type: u4
      - id: alpha
        type: u4
      - id: extra
        size-eos: true
  shape_image_subrecord:
    seq:
      - id: own_offset
        type: u4
      - id: unknown_04
        size: 3
      - id: shape_property_mask
        type: u4
      - id: shape_type
        type: u4
      - id: original_rect
        type: rect_f64
      - id: extra
        size-eos: true
  image_own_subrecord:
    seq:
      - id: flexible_payload_present
        type: u1
      - id: unknown_01
        size: 6
      - id: group1_flags
        type: u1
      - id: group2_flags
        type: u1
      - id: group3_flags
        type: u1
      - id: unknown_0a
        type: u1
      - id: flexible_payload
        size-eos: true
