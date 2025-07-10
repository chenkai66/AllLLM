import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def calculate_cosine_similarity(vec1, vec2):
    """
    计算两个向量的余弦相似度
    
    参数:
        vec1 (np.array): 向量1
        vec2 (np.array): 向量2
        
    返回:
        float: 余弦相似度
    """
    vec1 = vec1.reshape(1, -1)
    vec2 = vec2.reshape(1, -1)
    return cosine_similarity(vec1, vec2)[0][0]

def find_most_similar(vector, vector_list, threshold=0.7):
    """
    在向量列表中查找最相似的向量
    
    参数:
        vector (np.array): 查询向量
        vector_list (list): 向量列表
        threshold (float): 相似度阈值
        
    返回:
        int: 最相似向量的索引，若无则返回-1
    """
    max_similarity = -1
    max_index = -1
    
    for i, vec in enumerate(vector_list):
        similarity = calculate_cosine_similarity(vector, vec)
        if similarity > max_similarity and similarity >= threshold:
            max_similarity = similarity
            max_index = i
    
    return max_index