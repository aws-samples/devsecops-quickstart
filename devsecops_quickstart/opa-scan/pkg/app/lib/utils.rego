package utils

array_contains(arr, elem) {
  arr[_] = elem
}

allow_resource(resource) = ret {
  ret = {
    "valid": "true",
    "id": resource.address,
    "message": "",
    "type": resource.type
  }
}

deny_resource_with_message(resource, message) = ret {
  ret = {
    "valid": "false",
    "id": resource.address,
    "message": message,
    "type": resource.type
  }
}

approval_resource_with_message(resource, message) = ret {
  ret = {
    "valid": "approval",
    "id": resource.address,
    "message": message,
    "type": resource.type
  }
}