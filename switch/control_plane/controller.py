# -*- coding: UTF-8 -*-
import sys,pickle                                                             
import signal
import numpy as np
import os,time
sys.path.append(os.path.expandvars('$SDE/install/lib/python2.7/site-packages/tofino/'))

from bfrt_grpc import client

GRPC_CLIENT=client.ClientInterface(grpc_addr="localhost:50052", client_id=0,device_id=0, is_master=True)
bfrt_info=GRPC_CLIENT.bfrt_info_get(p4_name=None)
GRPC_CLIENT.bind_pipeline_config(p4_name=bfrt_info.p4_name)

def reset():
    GRPC_CLIENT.clear_all_tables()
    sys.stderr.write("#**  clear all the table! \n")

def quit(signum, frame):
    print ('stop receive digest')
    GRPC_CLIENT.__del__()
    sys.exit()

if bfrt_info.p4_name!='switch':
    sys.stderr.write("P4 program mismatch: driver reports currently running '%s' \n"% bfrt_info.p4_name)
    GRPC_CLIENT.__del__()
    sys.exit(-1)

target = client.Target()

learn_filter = bfrt_info.learn_get("digest_a")

Register_Table_Size = 3000
global now_index
now_index = 0
flow_index_keys = [None]*Register_Table_Size
flow_info = {}

def add_tb_entry_flow_result(data_dict):
    global now_index
    # add entry, set register, if needed, del entry
    table_name = 'SwitchIngress.Flow_result'
    flow_index_table = bfrt_info.table_get(table_name)
    flow_index_table.info.key_field_annotation_add("hdr.ipv4.src_addr", "ipv4")
    flow_index_table.info.key_field_annotation_add("hdr.ipv4.dst_addr", "ipv4")
    flow_index_key_list = []
    flow_index_data_list = []
    del_flow_index_key_list = []
    key1 = str(data_dict["src_addr"]) + '-' + str(data_dict["dst_addr"]) + '-' + str(data_dict["src_port"]) + '-' + str(data_dict["dst_port"]) + '-' + str(data_dict['protocol'])
    key2 = str(data_dict["dst_addr"]) + '-' + str(data_dict["src_addr"]) + '-' + str(data_dict["dst_port"]) + '-' + str(data_dict["src_port"]) + '-' + str(data_dict['protocol'])
    if key1 in flow_info.keys() or key2 in flow_info.keys():
        print("exist")
        return
    if len(flow_info)>=Register_Table_Size/2: #FIFO delete
        for i in range(10): #delete first 10 entries
            del_key = list(flow_info.keys())[i]
            
            del_data_dict = flow_info[del_key]
            #print(del_key,key1)
                
            del_flow_index_key_list.append(flow_index_table.make_key([
                                            client.KeyTuple('hdr.ipv4.src_addr',del_data_dict['src_addr']), 
                                            client.KeyTuple('hdr.ipv4.dst_addr',del_data_dict['dst_addr']),
                                            client.KeyTuple('ig_md.src_port',del_data_dict['src_port']),
                                            client.KeyTuple('ig_md.dst_port',del_data_dict['dst_port']),
                                            client.KeyTuple('hdr.ipv4.protocol',del_data_dict['protocol'])]))
            del_flow_index_key_list.append(flow_index_table.make_key([
                                            client.KeyTuple('hdr.ipv4.src_addr',del_data_dict['dst_addr']),
                                            client.KeyTuple('hdr.ipv4.dst_addr',del_data_dict['src_addr']),
                                            client.KeyTuple('ig_md.src_port',del_data_dict['dst_port']),
                                            client.KeyTuple('ig_md.dst_port',del_data_dict['src_port']),
                                            client.KeyTuple('hdr.ipv4.protocol',del_data_dict['protocol'])]))
            flow_info.pop(del_key)
        flow_index_table.entry_del(target, del_flow_index_key_list)
        print("Del flow_result entry finished",len(flow_info))

    
    flow_index_key_list.append(flow_index_table.make_key([
                                    client.KeyTuple('hdr.ipv4.src_addr',data_dict['src_addr']), 
                                    client.KeyTuple('hdr.ipv4.dst_addr',data_dict['dst_addr']),
                                    client.KeyTuple('ig_md.src_port',data_dict['src_port']),
                                    client.KeyTuple('ig_md.dst_port',data_dict['dst_port']),
                                    client.KeyTuple('hdr.ipv4.protocol',data_dict['protocol'])]))
    flow_index_data_list.append(flow_index_table.make_data([client.DataTuple('result', data_dict['result'])],
                                            "SwitchIngress.Set_flow_result"))
    #if (data_dict['src_port']!=data_dict['dst_port']):
    flow_index_key_list.append(flow_index_table.make_key([
                                    client.KeyTuple('hdr.ipv4.src_addr',data_dict['dst_addr']),
                                    client.KeyTuple('hdr.ipv4.dst_addr',data_dict['src_addr']),
                                    client.KeyTuple('ig_md.src_port',data_dict['dst_port']),
                                    client.KeyTuple('ig_md.dst_port',data_dict['src_port']),
                                    client.KeyTuple('hdr.ipv4.protocol',data_dict['protocol'])]))
    flow_index_data_list.append(flow_index_table.make_data([client.DataTuple('result', data_dict['result'])],
                                            "SwitchIngress.Set_flow_result"))
        
    flow_index_table.entry_add(target, flow_index_key_list, flow_index_data_list)
    flow_info[key1] = data_dict
    print("Add flow_result entry finished ".format(len(flow_info)))

def receive_digest():
    print("receive_digest......")
    signal.signal(signal.SIGINT, quit)                                
    signal.signal(signal.SIGTERM, quit)
    count = 0
    start_time = time.time()
    while True:
        digest = None
        try:
            digest = GRPC_CLIENT.digest_get()
        except KeyboardInterrupt:
            break
        except Exception as e:
            if 'Digest list not received' not in str(e):
                print('Unexpected error receiving digest - [%s]', e)
        
        if digest:
            data_list = learn_filter.make_data_list(digest)
            if not data_list or len(data_list) == 0:
                data_list = learn_filter.make_data_list(digest)
            for data_item in data_list:
                data_dict = data_item.to_dict()
                #print(data_dict)
                add_tb_entry_flow_result(data_dict)

def load_tb_bin(table_data):
    print("load_bin_tb_Feat.......")
    for i in range(len(table_data)):
        table_name = "pkt_bin{}".format(i+1)
        update_action_name = "Update_bin{}".format(i+1)
        read_action_name = "Read_bin{}".format(i+1)
        tcam_table = bfrt_info.table_get(table_name)
        key_list = [tcam_table.make_key([client.KeyTuple('$MATCH_PRIORITY', 1),
                                        client.KeyTuple('hdr.ipv4.total_len',table_data[i][0],table_data[i][1])]),
                    tcam_table.make_key([client.KeyTuple('$MATCH_PRIORITY', 2),
                                        client.KeyTuple('hdr.ipv4.total_len',0,0)])]#match anything
        data_list = [tcam_table.make_data([],update_action_name),
                     tcam_table.make_data([],read_action_name)]
        tcam_table.entry_add(target, key_list, data_list)
        
        table_name = "Init_bin{}_table".format(i+1)
        update_action_name = "Init1_bin{}".format(i+1)
        read_action_name = "Init0_bin{}".format(i+1)
        tcam_table = bfrt_info.table_get(table_name)
        key_list = [tcam_table.make_key([client.KeyTuple('$MATCH_PRIORITY', 1),
                                        client.KeyTuple('hdr.ipv4.total_len',table_data[i][0],table_data[i][1])]),
                    tcam_table.make_key([client.KeyTuple('$MATCH_PRIORITY', 2),
                                        client.KeyTuple('hdr.ipv4.total_len',0,0)])]
        data_list = [tcam_table.make_data([],update_action_name),
                     tcam_table.make_data([],read_action_name)]
        tcam_table.entry_add(target, key_list, data_list)



def load_tb_Feat(table_data,table_name,feat_name,action_name,is_total_pkts = True):
    # is_total_pkts: Whether to include the number of packets parameter
    print("load_tb_Feat--{}.......".format(table_name))

    tcam_table = bfrt_info.table_get(table_name)

    KeyTuple_list=[]
    DataTuple_List=[] 

    for x in range(len(table_data)):
        if is_total_pkts: 
            KeyTuple_list.append(tcam_table.make_key([client.KeyTuple('$MATCH_PRIORITY', table_data[x][0]),
                                                        client.KeyTuple("ig_md.total_pkts", table_data[x][4]),
                                                        client.KeyTuple(feat_name,
                                                                    int(table_data[x][1]),
                                                                    int(table_data[x][2]))]))
        else:
            KeyTuple_list.append(tcam_table.make_key([client.KeyTuple('$MATCH_PRIORITY', table_data[x][0]),
                                                        client.KeyTuple(feat_name,
                                                                    int(table_data[x][1]),
                                                                    int(table_data[x][2]))]))
        DataTuple_List.append(tcam_table.make_data([client.DataTuple('ind', table_data[x][3])],action_name))

    tcam_table.entry_add(target, KeyTuple_list, DataTuple_List)
    print("load_tb_Feat--{} finished.".format(table_name))

def load_tb_flow_size_tree(table_data):
    print("load_tb_flow_size_tree.......")
    table_name = "SwitchIngress.Flow_Size_Tree"
    tcam_table = bfrt_info.table_get(table_name)
    
    for x in range(len(table_data)): 
        tcam_table.entry_add(
            target,
            [tcam_table.make_key([client.KeyTuple("ig_md.feat3_encode",table_data[x][10],table_data[x][11]),
                                client.KeyTuple("ig_md.feat4_encode",table_data[x][8],table_data[x][9]),
                                client.KeyTuple("ig_md.feat5_encode",table_data[x][2],table_data[x][3]),
                                client.KeyTuple("ig_md.feat6_encode",table_data[x][12],table_data[x][13]),
                                client.KeyTuple("ig_md.feat7_encode",table_data[x][6],table_data[x][7]),
                                client.KeyTuple("ig_md.feat8_encode",table_data[x][0],table_data[x][1]),
                                client.KeyTuple("ig_md.feat9_encode",table_data[x][4],table_data[x][5]),
                                ])],
            [tcam_table.make_data([client.DataTuple('result',table_data[x][14])],
                                    "SetFlowSize")])
    
    print("load_tb_flow_size_tree finished.")

def load_tb_pkt_tree(table_data):
    print("load_tb_pkt_tree.......")
    table_name = "SwitchIngress.Pkt_Tree"
    tcam_table = bfrt_info.table_get(table_name)
    
    for x in range(len(table_data)): 
        tcam_table.entry_add(
            target,
            [tcam_table.make_key([client.KeyTuple("ig_md.feat3_encode",table_data[x][10],table_data[x][11]),
                                client.KeyTuple("ig_md.feat4_encode",table_data[x][8],table_data[x][9]),
                                client.KeyTuple("ig_md.feat5_encode",table_data[x][2],table_data[x][3]),
                                client.KeyTuple("ig_md.feat6_encode",table_data[x][12],table_data[x][13]),
                                client.KeyTuple("ig_md.feat7_encode",table_data[x][6],table_data[x][7]),
                                client.KeyTuple("ig_md.feat8_encode",table_data[x][0],table_data[x][1]),
                                client.KeyTuple("ig_md.feat9_encode",table_data[x][4],table_data[x][5]),
                                ])],
            [tcam_table.make_data([client.DataTuple('confidence', int(round(max(table_data[x][14])*100))),
                                   client.DataTuple('result', int(np.argmax(table_data[x][14])+1))],
                                    "SetClass_Pkt_Tree")])
    
    print("load_tb_pkt_tree finished.")

def load_tb_flow_tree(table_data):
    print("load_tb_flow_tree.......")
    table_name = "SwitchIngress.Flow_Tree"
    tcam_table = bfrt_info.table_get(table_name)
    
    for x in range(len(table_data)): 
    #   
        result = int(np.argmax(table_data[x][15])+1)

        # if max(table_data[x][15])>0.45: #set determined threshold here
        #     result+=50
        
        if table_data[x][0]==2048:
            result+=50
        
        tcam_table.entry_add(
            target,
            [tcam_table.make_key([client.KeyTuple("ig_md.total_pkts", table_data[x][0]),
                                client.KeyTuple("ig_md.feat10_encode",table_data[x][7],table_data[x][8]),
                                client.KeyTuple("ig_md.feat11_encode",table_data[x][5],table_data[x][6]),
                                client.KeyTuple("ig_md.feat12_encode",table_data[x][11],table_data[x][12]),
                                client.KeyTuple("ig_md.feat13_encode",table_data[x][1],table_data[x][2]),
                                client.KeyTuple("ig_md.feat14_encode",table_data[x][13],table_data[x][14]),
                                client.KeyTuple("ig_md.feat15_encode",table_data[x][3],table_data[x][4]),
                                client.KeyTuple("ig_md.feat16_encode",table_data[x][9],table_data[x][10]),
                                ])],
            [tcam_table.make_data([client.DataTuple('confidence', int(round(max(table_data[x][15])*100))),
                                   client.DataTuple('result', result)],
                                    "SetClass_Flow_Tree")])
    
    print("load_tb_flow_tree finished.")

pkt_feat = ['proto','total_len','diffserv', 'ttl', 'tcp_dataOffset', 'tcp_window', 'udp_length']
pkt_flow_feat = ['pkt_size_max','flow_iat_min','bin_5','bin_3','pkt_size_var_approx','pkt_size_avg','pkt_size_min']

with open("./bin_table_and_class_flow.pkl","rb") as f:
    [bin_table,feat_table_datas_flow,tree_data_p2p_flow] = pickle.load(f)

with open("./flow_size_and_class_pkt.pkl","rb") as f:
    [feat_table_datas_pkt,tree_data_flow_size, tree_data_p2p_pkt] = pickle.load(f)

load_tb_bin(bin_table[::-1])

load_tb_Feat(feat_table_datas_pkt['tcp_window'],"SwitchIngress.Feat3","ig_md.tcp_window",'SwitchIngress.feat3_hit',is_total_pkts=False)
load_tb_Feat(feat_table_datas_pkt["tcp_dataOffset"],"SwitchIngress.Feat4","ig_md.tcp_data_offset",'SwitchIngress.feat4_hit',is_total_pkts=False)
load_tb_Feat(feat_table_datas_pkt['total_len'],"SwitchIngress.Feat5","hdr.ipv4.total_len",'SwitchIngress.feat5_hit',is_total_pkts=False)
load_tb_Feat(feat_table_datas_pkt['udp_length'],"SwitchIngress.Feat6","ig_md.udp_length",'SwitchIngress.feat6_hit',is_total_pkts=False)
load_tb_Feat(feat_table_datas_pkt['ttl'],"SwitchIngress.Feat7","hdr.ipv4.ttl",'SwitchIngress.feat7_hit',is_total_pkts=False)
load_tb_Feat(feat_table_datas_pkt['proto'],"SwitchIngress.Feat8","hdr.ipv4.protocol",'SwitchIngress.feat8_hit',is_total_pkts=False)
load_tb_Feat(feat_table_datas_pkt['diffserv'],"SwitchIngress.Feat9","hdr.ipv4.diffserv",'SwitchIngress.feat9_hit',is_total_pkts=False)

load_tb_Feat(feat_table_datas_flow['bin_3'],"SwitchIngress.Feat10","ig_md.bin1",'SwitchIngress.feat10_hit')
load_tb_Feat(feat_table_datas_flow['bin_5'],"SwitchIngress.Feat11","ig_md.bin2",'SwitchIngress.feat11_hit')
load_tb_Feat(feat_table_datas_flow['pkt_size_avg'],"SwitchIngress.Feat12","ig_md.pkt_size_avg",'SwitchIngress.feat12_hit')
load_tb_Feat(feat_table_datas_flow['pkt_size_max'],"SwitchIngress.Feat13","ig_md.max_pkt_length",'SwitchIngress.feat13_hit')
load_tb_Feat(feat_table_datas_flow['pkt_size_min'],"SwitchIngress.Feat14","ig_md.min_pkt_length",'SwitchIngress.feat14_hit')
load_tb_Feat(feat_table_datas_flow['flow_iat_min'],"SwitchIngress.Feat15","ig_md.min_ipd",'SwitchIngress.feat15_hit')
load_tb_Feat(feat_table_datas_flow['pkt_size_var_approx'],"SwitchIngress.Feat16","ig_md.pkt_length_power_sum",'SwitchIngress.feat16_hit')


load_tb_flow_size_tree(tree_data_flow_size)
load_tb_pkt_tree(tree_data_p2p_pkt)
load_tb_flow_tree(tree_data_p2p_flow)

receive_digest()