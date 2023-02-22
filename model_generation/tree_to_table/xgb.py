from .utils import *


# Get all the thresholds that appear in the tree
def get_xgb_feature_thres(model_file,keys):
    # model_file: tree model file, keys: the list of features
    with open(model_file, 'r') as f:
        lines = f.readlines()
    feat_dict = {}
    for key in keys:
        feat_dict[key] = []
    for line in lines:
        if ":[" in line:
            m = re.search(r".*\[(.*?)<(.*?)\].*",line.strip(), re.M|re.I)
            feat_dict[m.group(1)].append(float(m.group(2)))
    for key in feat_dict.keys():
        for i in range(len(feat_dict[key])):
           feat_dict[key][i] = math.ceil(feat_dict[key][i]) #rounding up, the xgboost node is f<a
        feat_dict[key] = list(np.unique(np.array(feat_dict[key])))

    return feat_dict


# Get the model table table entries
def get_xgb_trees_table_entries(model_file,keys,feat_dict,key_encode_bits,pkts=None):
    # model_file: model file，feat_dict: the thresholds of each feature, key_encode_bits: range mark, pkts: the first few packets, optional
    # The return value is a list, each element represents a table item, the content is the range mark of each feature and the classification result
    with open(model_file, 'r') as f:
        lines = f.readlines()
    tree_data = []
    tree_leaves= []#Each row is a leaf node, recording that smallest threshold index in left subtree and smallest threshold index (negative) in right subtree on the path of that leaf node
    trees = []
    leafs= []
    for line in lines:
        if "booster" in line:# new tree
            trees.append(len(tree_leaves))
            nodes={}
            nodes[str(0)] = [1000,0]*len(keys) # assumption that there are no more than 1000 different feature thresholds.
        if "yes" in line:
            m = re.search(r"(.*?):\[(.*?)<(.*?)\] yes=(.*?),no=(.*?),.*",line.strip(), re.M|re.I)
            feat = m.group(2)
            thre = math.ceil(float(m.group(3)))
            nodes[m.group(4)] = nodes[m.group(1)].copy()
            nodes[m.group(4)][keys.index(feat)*2] = min(nodes[m.group(4)][keys.index(feat)*2],
                                                    feat_dict[feat].index(thre)+1)
            nodes[m.group(5)] = nodes[m.group(1)].copy()
            nodes[m.group(5)][keys.index(feat)*2+1] = min(nodes[m.group(5)][keys.index(feat)*2+1],
                                                    -feat_dict[feat].index(thre)-1)
        if "leaf" in line:
            m = re.search(r"(.*?):leaf=(.*?)\n",line.strip('\t'), re.M|re.I)
            tree_leaves.append(nodes[m.group(1)])
            leafs.append(float(m.group(2)))
            
    trees.append(len(tree_leaves))
    print("tree_leaves: ",trees)
            
    print("judge leaf conflict ...")
    loop_val = []
    for i in range(len(trees))[:-1]:
        loop_val.append(range(trees[i],trees[i+1]))
    print(loop_val)
    for tup in product(*loop_val):
        flag = 0
        for f in range(len(keys)): #Check for conflicting feature values
            a = 1000; b=1000; 
            for i in tup:
                a = min(tree_leaves[i][f*2],a)
                b = min(tree_leaves[i][f*2+1],b)
            if a+b <= 0:
                flag=1
                break
        # Semantic conflict check can be added here
        if flag==0:
            if pkts is None:
                tree_data.append([]) #
            else:
                tree_data.append([pkts])
            for f in range(len(keys)):
                a = 1000; b=1000; 
                for i in tup:
                    a = min(tree_leaves[i][f*2],a)
                    b = min(tree_leaves[i][f*2+1],b)
                key = keys[f]
                te = get_model_table_range_mark(key_encode_bits[key],a,b,len(feat_dict[key]))
                tree_data[-1].extend([int(get_value_mask(te,key_encode_bits[key])[0],2),int(get_value_mask(te,key_encode_bits[key])[1],2)])  #The value and mask of each feature
            leaf_sum = 0.0
            for i in tup:
                leaf_sum+=leafs[i]
            tree_data[-1].append(round(sigmoid(leaf_sum)*100)) #classification probabilities list
    return tree_data

