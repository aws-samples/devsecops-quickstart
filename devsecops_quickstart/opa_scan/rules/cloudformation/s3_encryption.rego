package rules.s3_encryption

import data.cf_utils
import data.utils

buckets[id] = resource{
    resources = cf_utils.resources_by_type["AWS::S3::Bucket"]
    resource = resources[id]
}
is_encrypted(resource) {
  resource.Properties.BucketEncryption[_] = _
}
has_not_encryption(resource, key) = msg {
  msg = sprintf("Bucket %s is not encrypted", [key])
  not is_encrypted(resource)
} 

rule[r] {
  resource = buckets[id]
  msg = has_not_encryption(resource, id)
  r = utils.deny_resource_with_message(resource, msg)
} {
   resource = buckets[id]
   is_encrypted(resource)
   r = utils.allow_resource(resource)
}
