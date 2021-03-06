#!/anaconda3/bin/python
import sys, os, glob
import numpy as np
# To ensure that non of the numpy outputs are truncated with '...'
np.set_printoptions(threshold=np.inf)
import pandas as pd
# To ensure that non of the pandas outputs are truncated with '...'
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
# to visualize in easy to read html table
# https://github.com/swcarpentry/python-novice-gapminder/issues/342
from IPython.display import display
import argparse 
# To add timer at the end
import time

start_time = time.time() # To keep track of speed

#Could also use path to query folder...
def predict_ss(H, E, C, marg_p_R, marg_p_SS, query_profile, win_size):
    '''
    Arguments H, E, C, marg_p_R & marg_p_SS are the log transformed model matrices used 
    to predict the secondary structure (ss). 
    The query_profile is passed for prediction of its ss.
    Returns predicted ss as a string.
    '''
    # Loading query profile
    profile_arr = np.loadtxt(query_profile, usecols=range(0,20), dtype=np.float64)
    # Creating overhang to be added before and after profile_arr
    overhang = win_size//2
    overhang_arr = np.zeros((overhang, 20))
    # Adding overhang to beginning and end:
    overhang_profile_arr = np.concatenate((overhang_arr, profile_arr, overhang_arr), axis=0)
    # print("*********** *********")
    # print(overhang_profile_arr)

    # Var holding predicted SS: Line 1 of fasta-like dssp file
    predicted_ss = ''
    #Counting lines of file to range on when sliding the window
    rows_count = profile_arr.shape[0]

    # Matrices holding the 'log term' of the information function --> log P(R,S)/(P(S)P(R)) = P(R,S) - (P(S) + P(R)). 
    # The inf fct = incomplete -- missing weight as factor!
    log_H = H - (marg_p_SS['H'].values[0] + marg_p_R)
    log_E = E - (marg_p_SS['E'].values[0] + marg_p_R)
    log_C = C - (marg_p_SS['C'].values[0] + marg_p_R)

    for i in range(rows_count):
        # Iterating over the overhang_profile_arr generating new window for each iteration
        # The window is a matrix containing all the weights. Its a slice from index i up to i+window_size
        weights = overhang_profile_arr[i:(i+win_size)]
        # Completing *information function* for each conformation by multiplying the weight obtained from PW
        I_H = weights * log_H
        I_E = weights * log_E
        I_C = weights * log_C
        
        # Summing up the result of the information function
        res_H = I_H.sum()
        res_E = I_E.sum()
        res_C = I_C.sum()
        
        # Creating dict to assign SS when given the maximum
        i_dict = {res_H:'H', res_E:'E', res_C:'C'}

        # Finding maximum of HEC information functions
        thewinner = max(res_H, res_E, res_C)

        # Assigning SS to predicted_ss string
        predicted_ss += i_dict[thewinner]

    return  predicted_ss

def write_dssp(ss, query_id, outpath):
    '''
    Takes predicted_ss from predict_from_set() as first argument and 
    id of the query as second argument. Generates a fasta like dssp
    file. No return.
    '''
    # Line 0 of fasta-like dssp file: --> slicing away '.profile'
    ID = os.path.basename(query_id)
    dssp_header = '>'+query_id 
    # Line 1 of fasta-like dssp file holding SS structure is the ss
    dssp_path = os.path.join(outpath, ID+'.dssp')
    with open(dssp_path, 'w') as wfile:
        wfile.write(dssp_header+'\n'+ss+'\n')
    return

def read_clean_all(infile1):
    ''' Reads ALL lines from a file. Returns string of second line. The '\n' is stripped.'''
    with open(infile1, 'r') as rfile:
        newline_list = rfile.readlines()
        clean =[]
        for l in newline_list:
            clean.append(l.rstrip())
        return clean

def listdir_nohidden(path):
    '''
    To ignore hidden files from os.listdir.
    Returns only list of paths of 'nonhidden files' from directory
    --> the glob pattern * matches all files that are NOT hidden
    '''
    return glob.glob(os.path.join(path, '*'))

#############################################################################################################################
# Adding parser
#############################################################################################################################
parser = argparse.ArgumentParser(description='Prediction using trained GOR model')
parser.add_argument('-m', '--model', type=str, metavar='', required=True, help='Path to directory containing model csv generated by training.') 
parser.add_argument('-q', '--queryprofiles', type=str, metavar='', required=True, help='Path to directory containing all query profile files to be predicted.')
parser.add_argument('-i', '--ids', type=str, metavar='', required=False, help='Path to file containing IDs of current training set.')
parser.add_argument('-o', '--output', type=str, metavar='', required=True, help='Path to output directory for all predicted structures.')
args = parser.parse_args()

if __name__ == "__main__":
    #---------------------------------------------------------------------------------------------------------------------------
    # Loading GOR model --> 4 np.array and 1 pd.df
    #---------------------------------------------------------------------------------------------------------------------------
    model_path = args.model
    #'/Users/ila/01-Unibo/02_Lab2/files_lab2_project/all_data/outputs/gor_train_out/' # path to each of the "gor_training_output_XXX.csv" or add to argparse???

    H = np.loadtxt(os.path.join(model_path,'gor_training_out_H'), dtype=np.float64)     # index_col indicates that first column is the index
    E = np.loadtxt(os.path.join(model_path,'gor_training_out_E'), dtype=np.float64)
    C = np.loadtxt(os.path.join(model_path,'gor_training_out_C'), dtype=np.float64)
    df_marg_p_R = np.loadtxt(os.path.join(model_path,'gor_training_out_marg_prob_R'), dtype=np.float64)
    SS_df = pd.read_csv(os.path.join(model_path,'gor_training_output_SS.csv'), index_col=[0])
    # loading win_size from training output
    win_size = np.loadtxt(os.path.join(model_path,'win_size'), dtype=np.int32)
    #---------------------------------------------------------------------------------------------------------------------------
    # Logtransforming --> to enable substraction and addition instead of division and mulitplication
    #---------------------------------------------------------------------------------------------------------------------------
    log_H = np.log(H)
    log_E = np.log(E)
    log_C = np.log(C)
    log_marg_p_R = np.log(df_marg_p_R)
    log_marg_p_SS = np.log(SS_df)

    # List of queries to loop on -- ids need to be added from test_set_i
    short_path = args.queryprofiles # Path to profiles of the query
    query_ids = read_clean_all(args.ids) # List containing all ids -NO extension

    # Directory obtaining ss predictions in fasta like .dssp
    pred_dir = args.output
    #---------------------------------------------------------------------------------------------------------------------------
    # Initiate loop
    #---------------------------------------------------------------------------------------------------------------------------
    for profile_id in query_ids:
        query_path = os.path.join(short_path, profile_id)+'.profile'   # Name of each query
        pred_ss = predict_ss(log_H, log_E, log_C, log_marg_p_R, log_marg_p_SS, query_path, win_size)
        write_dssp(pred_ss, profile_id, pred_dir)

    # Print elapsed time
    elapsed_seconds = float(time.time() - start_time)
    if elapsed_seconds > 60:
        minutes = elapsed_seconds/60
        print("--- %s minutes ---" % minutes)
    else:
        print("--- %s seconds ---" % (time.time() - start_time))