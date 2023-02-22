/* -*- P4_16 -*- */

/*******************************************************************************
 * BAREFOOT NETWORKS CONFIDENTIAL & PROPRIETARY
 *
 * Copyright (c) Intel Corporation
 * SPDX-License-Identifier: CC-BY-ND-4.0
 */


#ifndef _HEADERS_
#define _HEADERS_

typedef bit<48> mac_addr_t;
typedef bit<32> ipv4_addr_t;
typedef bit<128> ipv6_addr_t;
typedef bit<12> vlan_id_t;

typedef bit<16> ether_type_t;
const ether_type_t ETHERTYPE_IPV4 = 16w0x0800;
const ether_type_t ETHERTYPE_ARP = 16w0x0806;
const ether_type_t ETHERTYPE_IPV6 = 16w0x86dd;
const ether_type_t ETHERTYPE_VLAN = 16w0x8100;

typedef bit<8> ip_protocol_t;
const ip_protocol_t IP_PROTOCOLS_ICMP = 1;
const ip_protocol_t IP_PROTOCOLS_TCP = 6;
const ip_protocol_t IP_PROTOCOLS_UDP = 17;

#define egress_port 65
#define recirculate_port 68

typedef bit<32> flow_index_t;

#define Register_Table_Size 65536 //register array size
#define Register_Index_Size 16    //register array index bits

#define timeout_thres 256 //timeout threshold


// The actual numeric value
//  * is not important, it just needs to be consistent between what it set in the
//  * ingress pipeline and what is checked in the ingress deparser. */
const bit<3> DPRSR_DIGEST_TYPE_A = 2;
const bit<8> RESUB_TYPE_A = 255;

/* Define a few different resubmit digests.  Note that each must be exactly 8
 * bytes on Tofino-1 and 16 bytes on Tofino-2.  In order to allow the ingress
 * parser to identify which resubmit digest type a packet has, one byte is used
 * to carry a type. */
header resubmit_type_a {
    bit<8>  result;
    bit<8>  confidence;
    bit<48> pad2;
}

header ethernet_h {
    mac_addr_t dst_addr;
    mac_addr_t src_addr;
    bit<16> ether_type;
}

header vlan_tag_h {
    bit<3> pcp;
    bit<1> cfi;
    vlan_id_t vid;
    bit<16> ether_type;
}

header mpls_h {
    bit<20> label;
    bit<3> exp;
    bit<1> bos;
    bit<8> ttl;
}

header ipv4_h {
    bit<4> version;
    bit<4> ihl;
    bit<8> diffserv;
    bit<16> total_len;
    bit<16> identification;
    bit<3> flags;
    bit<13> frag_offset;
    bit<8> ttl;
    bit<8> protocol;
    bit<16> hdr_checksum;
    ipv4_addr_t src_addr;
    ipv4_addr_t dst_addr;
}

header ipv6_h {
    bit<4> version;
    bit<8> traffic_class;
    bit<20> flow_label;
    bit<16> payload_len;
    bit<8> next_hdr;
    bit<8> hop_limit;
    ipv6_addr_t src_addr;
    ipv6_addr_t dst_addr;
}

header tcp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<32> seq_no;
    bit<32> ack_no;
    bit<4> data_offset;
    bit<4> res;
    bit<8> flags;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgent_ptr;
}

header udp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<16> hdr_length;
    bit<16> checksum;
}

header icmp_h {
    bit<8> type_;
    bit<8> code;
    bit<16> hdr_checksum;
}

// Address Resolution Protocol -- RFC 6747
header arp_h {
    bit<16> hw_type;
    bit<16> proto_type;
    bit<8> hw_addr_len;
    bit<8> proto_addr_len;
    bit<16> opcode;
    // ...
}

// Segment Routing Extension (SRH) -- IETFv7
header ipv6_srh_h {
    bit<8> next_hdr;
    bit<8> hdr_ext_len;
    bit<8> routing_type;
    bit<8> seg_left;
    bit<8> last_entry;
    bit<8> flags;
    bit<16> tag;
}

// VXLAN -- RFC 7348
header vxlan_h {
    bit<8> flags;
    bit<24> reserved;
    bit<24> vni;
    bit<8> reserved2;
}

// Generic Routing Encapsulation (GRE) -- RFC 1701
header gre_h {
    bit<1> C;
    bit<1> R;
    bit<1> K;
    bit<1> S;
    bit<1> s;
    bit<3> recurse;
    bit<5> flags;
    bit<3> version;
    bit<16> proto;
}

struct header_t {
    ethernet_h ethernet;
    vlan_tag_h vlan_tag;
    ipv4_h ipv4;
    ipv6_h ipv6;
    tcp_h tcp;
    udp_h udp;

    // Add more headers here.
}

struct empty_header_t {}

struct empty_metadata_t {}

struct metadata_t {
    bit<16> src_port;
    bit<16> dst_port;
    bit<32> flow_hash;
    bit<32> flow_hash1;
    bit<Register_Index_Size> flow_index;
    
    bit<16> total_pkts;
    bit<32> total_bytes;
    bit<16> zoom_pkt_length;

    bit<16> tcp_window;
    bit<4> tcp_data_offset;
    bit<16> udp_length;

    bit<16> bin1;
    bit<8> bin2;
    bit<16> max_pkt_length;
    bit<16> min_pkt_length;
    bit<32> pkt_size_avg;
    
    bit<32> pkt_length_power_sum;
    bit<32> total_bytes_power;
    bit<32> last_pkt_timestamp;
    bit<32> ipd;
    bit<32> min_ipd;

    bit<32> last_classified;
    bit<32> now_timestamp;
    bit<32> interval;
    
    // bit<16> feat1_encode;
    // bit<16> feat2_encode;
    bit<48> feat3_encode;
    bit<8> feat4_encode;
    bit<144> feat5_encode;
    bit<72> feat6_encode;
    bit<64> feat7_encode;
    bit<8> feat8_encode;
    bit<24> feat9_encode;

    bit<32> feat10_encode;
    bit<24> feat11_encode;
    bit<72> feat12_encode;
    bit<80> feat13_encode;
    bit<48> feat14_encode;
    bit<72> feat15_encode; 
    bit<80> feat16_encode;

    bit<8> tree1_confidence;
    bit<8> result;
    bit<8> flow_size;
}


struct digest_a_t {
   ipv4_addr_t src_addr;
   ipv4_addr_t dst_addr;
   bit<16> src_port;
   bit<16> dst_port;
   bit<8> protocol;
   bit<8> result;
}

#endif /* _HEADERS_ */