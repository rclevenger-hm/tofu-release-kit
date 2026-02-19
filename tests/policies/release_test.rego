package tofu_release_kit_test

import rego.v1
import data.tofu_release_kit.decision

config := {"protected_resources": ["aws_dynamodb_table.orders"], "required_tags": ["owner", "environment"],
           "taggable_types": ["aws_dynamodb_table"], "admin_ports": [22, 3389]}

resource(kind, actions, after, unknown) := {"address": sprintf("%s.orders", [kind]), "type": kind, "mode": "managed",
    "change": {"actions": actions, "after": after, "after_unknown": unknown}}

evaluate(r) := result if {
    result := decision with input as {"config": config, "plan": {"resource_changes": [r]}}
}

test_tagged_resource_passes if {
    evaluate(resource("aws_dynamodb_table", ["create"], {"tags": {"owner": "platform", "environment": "test"}}, {})).allowed
}

test_provider_default_tags_pass if {
    evaluate(resource("aws_dynamodb_table", ["create"], {"tags_all": {"owner": "platform", "environment": "test"}}, {})).allowed
}

test_missing_tags_denied if {
    result := evaluate(resource("aws_dynamodb_table", ["create"], {}, {}))
    not result.allowed
    count(result.findings) == 2
}

test_unknown_tags_denied if {
    not evaluate(resource("aws_dynamodb_table", ["create"], {"tags": {"owner": "p", "environment": "t"}}, {"tags_all": true})).allowed
}

test_null_tags_denied if {
    not evaluate(resource("aws_dynamodb_table", ["create"], {"tags": null}, {})).allowed
}

test_protected_deletion_denied if {
    not evaluate(resource("aws_dynamodb_table", ["delete"], null, {})).allowed
}

test_create_before_destroy_denied if {
    not evaluate(resource("aws_dynamodb_table", ["create", "delete"], {"tags": {"owner": "p", "environment": "t"}}, {})).allowed
}

test_forget_denied if {
    not evaluate(resource("aws_dynamodb_table", ["forget"], null, {})).allowed
}

test_public_ipv4_ssh_denied if {
    not evaluate(resource("aws_vpc_security_group_ingress_rule", ["create"], {"cidr_ipv4": "0.0.0.0/0", "ip_protocol": "tcp", "from_port": 22, "to_port": 22}, {})).allowed
}

test_public_ipv6_range_denied if {
    not evaluate(resource("aws_security_group_rule", ["create"], {"type": "ingress", "ipv6_cidr_blocks": ["::/0"], "protocol": "tcp", "from_port": 1, "to_port": 65535}, {})).allowed
}

test_public_all_protocols_denied if {
    not evaluate(resource("aws_vpc_security_group_ingress_rule", ["create"], {"cidr_ipv4": "0.0.0.0/0", "ip_protocol": "-1"}, {})).allowed
}

test_inline_ingress_denied if {
    not evaluate(resource("aws_security_group", ["create"], {"ingress": [{"cidr_blocks": ["0.0.0.0/0"], "protocol": "tcp", "from_port": 3389, "to_port": 3389}]}, {})).allowed
}

test_public_https_passes if {
    evaluate(resource("aws_vpc_security_group_ingress_rule", ["create"], {"cidr_ipv4": "0.0.0.0/0", "ip_protocol": "tcp", "from_port": 443, "to_port": 443}, {})).allowed
}

test_private_ssh_passes if {
    evaluate(resource("aws_vpc_security_group_ingress_rule", ["create"], {"cidr_ipv4": "10.0.0.0/8", "ip_protocol": "tcp", "from_port": 22, "to_port": 22}, {})).allowed
}

test_egress_passes if {
    evaluate(resource("aws_security_group_rule", ["create"], {"type": "egress", "cidr_blocks": ["0.0.0.0/0"], "protocol": "-1"}, {})).allowed
}

test_unknown_network_denied if {
    not evaluate(resource("aws_security_group", ["create"], {"ingress": []}, {"ingress": [{"cidr_blocks": [true]}]})).allowed
}
