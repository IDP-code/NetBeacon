/* -*- P4_16 -*- */

/*******************************************************************************
 * BAREFOOT NETWORKS CONFIDENTIAL & PROPRIETARY
 *
 * Copyright (c) Intel Corporation
 * SPDX-License-Identifier: CC-BY-ND-4.0
 */

#ifndef _PARSERS_
#define _PARSERS_


#include "headers.p4"

// ---------------------------------------------------------------------------
// Ingress parser
// ---------------------------------------------------------------------------

parser SwitchIngressParser(
        packet_in pkt,
        out header_t hdr,
        out metadata_t ig_md,
        out ingress_intrinsic_metadata_t ig_intr_md) {

    TofinoIngressParser() tofino_parser;
    Checksum() ipv4_checksum;

    state start {
        tofino_parser.apply(pkt, ig_intr_md);
        transition parse_ethernet;
    }
    

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ETHERTYPE_IPV4: parse_ipv4;
            ETHERTYPE_VLAN: parse_vlan;
            ETHERTYPE_ARP: reject;
            default: reject;
        }
    }
    
    state parse_vlan{
        pkt.extract(hdr.vlan_tag);
        transition select(hdr.vlan_tag.ether_type) {
            ETHERTYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        ipv4_checksum.add(hdr.ipv4);

        // parse only non-fragmented (hdr.ipv4.frag_offset=0) IP packets with no options(hdr.ipv4.ihl=5)
        transition select(hdr.ipv4.ihl, hdr.ipv4.frag_offset, hdr.ipv4.protocol) {
            (5, 0, IP_PROTOCOLS_TCP) : parse_tcp;
            (5, 0, IP_PROTOCOLS_UDP)  : parse_udp;
            default: reject;
        }
    }

    state parse_tcp {
        pkt.extract(hdr.tcp);
        ig_md.src_port = hdr.tcp.src_port;
        ig_md.dst_port = hdr.tcp.dst_port;
        ig_md.udp_length=0;
        ig_md.tcp_window=hdr.tcp.window;
        ig_md.tcp_data_offset=hdr.tcp.data_offset;
        transition accept;
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        ig_md.src_port = hdr.udp.src_port;
        ig_md.dst_port = hdr.udp.dst_port;
        ig_md.tcp_window=0;
        ig_md.tcp_data_offset=0;
        ig_md.udp_length=hdr.udp.hdr_length;
        transition select(hdr.udp.src_port) {
            68: reject;
            default: accept;
        }
        //transition accept;
    }
}

// ---------------------------------------------------------------------------
// Ingress Deparser
// ---------------------------------------------------------------------------
control SwitchIngressDeparser(
        packet_out pkt,
        inout header_t hdr,
        in metadata_t ig_md,
        in ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md) {

    Digest<digest_a_t>() digest_a;
    //Digest<digest_b_t>() digest_b; //maxmum 48 bytes

    apply {

        if (ig_dprsr_md.digest_type == 2) {
            digest_a.pack({hdr.ipv4.src_addr, hdr.ipv4.dst_addr, ig_md.src_port, ig_md.dst_port, hdr.ipv4.protocol,ig_md.result});
        }

        pkt.emit(hdr);
    }
}

#endif /* _PARSERS_ */