package cf_utils

resource_types = {rt |
  r = input.Resources[_]
  rt = r.type
}

resources_names = {r |
  input.Resources[r]
}

resources_by_type = {rt: rs |
  resource_types[rt]
  rs = {id: r | 
    r = input.Resources[id]
    r.type = rt
  }
}

is_tagged(resource) {
  count(resource.tags) > 0
}

has_tag(resource, key) {
  some k
  resource.tags[k]
  k == key
}