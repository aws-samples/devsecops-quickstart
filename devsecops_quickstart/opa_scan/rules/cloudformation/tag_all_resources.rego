# The following rule checks that "taggable" resource types have tag
# values with at least 6 characters.
package rules.tag_all_resources

import data.cf_utils
import data.utils

taggable_resource_types = {
  "AWS::EC2::Instance",
  "AWS::AutoScaling::AutoScalingGroup",
  "AWS::S3::Bucket",
  "AWS::EC2::SecurityGroup",
  "AWS::EC2::Subnet",
  "AWS::EC2::VPC",
  "AWS::EC2::DHCPOptions",
  "AWS::EC2::VPNConnection",
  "AWS::EC2::VPNGateway",
}


taggable_resources[id] = resource {
   some resource_type
   taggable_resource_types[resource_type]
   resources = cf_utils.resources_by_type[resource_type]
   resource = resources[id]
}

is_tagged(resource) {
  resource.Properties.Tags[_] = _
}

is_improperly_tagged(resource) = msg {
   not is_tagged(resource)
   msg = "Not Tags Found"
}

rule[r] {
   resource = taggable_resources[key]
   msg = is_improperly_tagged(resource)
   rs = utils.parse_cf_resource(resource, key)
   r = utils.deny_resource_with_message(rs, msg)
} {
   resource = taggable_resources[key]
   not is_improperly_tagged(resource)
   rs = utils.parse_cf_resource(resource, key)
   r = utils.allow_resource(rs)
}
