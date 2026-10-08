package tofu_release_kit

import rego.v1

decision := {"allowed": count(findings) == 0, "findings": sort(findings)}

managed contains resource if {
    some resource in input.plan.resource_changes
    resource.mode == "managed"
}

live contains resource if {
    some resource in managed
    resource.change.after != null
    not "forget" in resource.change.actions
}

findings contains {"rule": "protected-resource", "address": resource.address,
                   "reason": "Deletion, replacement, or loss of management of a protected resource requires a separate reviewed exception."} if {
    some resource in managed
    resource.address in input.config.protected_resources
    some action in resource.change.actions
    action in {"delete", "forget"}
}

tag_value(resource, key) := value if {
    tags_all := object.get(resource.change.after, "tags_all", {})
    tags := object.get(resource.change.after, "tags", {})
    value := object.get(tags_all, key, object.get(tags, key, ""))
}

tag_known(resource, key) if {
    unknown := object.get(resource.change, "after_unknown", {})
    is_object(unknown)
    unknown_all := object.get(unknown, "tags_all", {})
    unknown_tags := object.get(unknown, "tags", {})
    is_object(unknown_all)
    is_object(unknown_tags)
    object.get(unknown_all, key, false) != true
    object.get(unknown_tags, key, false) != true
}

valid_tag(resource, key) if {
    tag_known(resource, key)
    value := tag_value(resource, key)
    is_string(value)
    trim_space(value) != ""
}

findings contains {"rule": "required-tags", "address": resource.address,
                   "reason": sprintf("Required tag %s is missing, empty, or unknown at plan time.", [key])} if {
    some resource in live
    resource.type in input.config.taggable_types
    some key in input.config.required_tags
    not valid_tag(resource, key)
}

network_types := {"aws_security_group", "aws_security_group_rule", "aws_vpc_security_group_ingress_rule"}

network_resource(resource) if {
    resource.type in network_types
    resource.type != "aws_security_group_rule"
}

network_resource(resource) if {
    resource.type == "aws_security_group_rule"
    object.get(resource.change.after, "type", "ingress") != "egress"
}

network_unknown(resource) if {
    object.get(resource.change, "after_unknown", {}) == true
}

network_unknown(resource) if {
    unknown := object.get(resource.change, "after_unknown", {})
    some field in {"ingress", "type", "cidr_ipv4", "cidr_ipv6", "cidr_blocks", "ipv6_cidr_blocks", "from_port", "to_port", "protocol", "ip_protocol"}
    value := object.get(unknown, field, false)
    value == true
}

network_unknown(resource) if {
    unknown := object.get(resource.change, "after_unknown", {})
    some field in {"ingress", "cidr_blocks", "ipv6_cidr_blocks"}
    walk(object.get(unknown, field, {}), [_, true])
}

findings contains {"rule": "public-admin", "address": resource.address,
                   "reason": "Ingress properties are unknown; public administrative access cannot be evaluated."} if {
    some resource in live
    network_resource(resource)
    network_unknown(resource)
}

ingress_rules(resource) := rules if {
    resource.type == "aws_security_group"
    rules := object.get(resource.change.after, "ingress", [])
}

ingress_rules(resource) := [resource.change.after] if {
    resource.type != "aws_security_group"
}

public(rule) if { object.get(rule, "cidr_ipv4", "") == "0.0.0.0/0" }
public(rule) if { object.get(rule, "cidr_ipv6", "") == "::/0" }
public(rule) if { "0.0.0.0/0" in object.get(rule, "cidr_blocks", []) }
public(rule) if { "::/0" in object.get(rule, "ipv6_cidr_blocks", []) }

admin(rule) if {
    protocol := object.get(rule, "ip_protocol", object.get(rule, "protocol", ""))
    protocol in {"-1", -1}
}

admin(rule) if {
    protocol := object.get(rule, "ip_protocol", object.get(rule, "protocol", ""))
    protocol in {"tcp", "6", 6, "udp", "17", 17}
    some port in input.config.admin_ports
    rule.from_port <= port
    rule.to_port >= port
}

findings contains {"rule": "public-admin", "address": resource.address,
                   "reason": "Public IPv4 or IPv6 access includes an administrative port."} if {
    some resource in live
    network_resource(resource)
    some rule in ingress_rules(resource)
    public(rule)
    admin(rule)
}
